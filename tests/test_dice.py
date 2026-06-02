"""Dice engine — parsing, rolling, advantage, special rolls, RNG injection, determinism.

Ported from the source engine's suite and adapted to the typed (dataclass) result surface.
"""

import dataclasses
import secrets

import pytest

from dndwright import DiceEngine as TopLevelDiceEngine
from dndwright.dice import (
    AttackRoll,
    DiceEngine,
    DiceGroup,
    ExpressionResult,
    ParsedExpression,
    SaveRoll,
    StatArray,
)
from dndwright.dice.engine import _MAX_DIE_ITERATIONS


class TestParsing:
    def test_simple_expression(self):
        result = DiceEngine().parse_expression("1d20")
        assert isinstance(result, ParsedExpression)
        assert len(result.dice_groups) == 1
        assert result.dice_groups[0].count == 1
        assert result.dice_groups[0].sides == 20
        assert result.modifier == 0

    def test_modifier(self):
        assert DiceEngine().parse_expression("1d20+5").modifier == 5

    def test_negative_modifier(self):
        assert DiceEngine().parse_expression("1d20-2").modifier == -2

    def test_multiple_dice(self):
        groups = DiceEngine().parse_expression("2d6+1d8").dice_groups
        assert len(groups) == 2
        assert (groups[0].count, groups[0].sides) == (2, 6)
        assert (groups[1].count, groups[1].sides) == (1, 8)

    def test_keep_highest(self):
        g = DiceEngine().parse_expression("4d6kh3").dice_groups[0]
        assert (g.count, g.sides, g.keep_highest) == (4, 6, 3)

    def test_drop_lowest(self):
        assert DiceEngine().parse_expression("4d6dl1").dice_groups[0].drop_lowest == 1


class TestRolling:
    def test_d20_in_range(self):
        eng = DiceEngine()
        for _ in range(100):
            assert 1 <= eng.roll("1d20").total <= 20

    def test_2d6_in_range(self):
        eng = DiceEngine()
        for _ in range(100):
            assert 2 <= eng.roll("2d6").total <= 12

    def test_modifier_applied(self):
        result = DiceEngine(seed=42).roll("1d20+5")
        assert result.total == result.individual_rolls[0] + 5
        assert result.modifier == 5

    def test_keep_highest_drops_lowest(self):
        result = DiceEngine(seed=42).roll("4d6kh3")
        dice = result.dice_results[0]
        assert len(dice.all_rolls) == 4
        assert len(dice.kept_rolls) == 3
        assert len(dice.dropped_rolls) == 1
        assert dice.dropped_rolls[0] <= min(dice.kept_rolls)

    def test_critical_detection(self):
        class Always20(DiceEngine):
            def _roll_die(self, sides):
                return 20 if sides == 20 else super()._roll_die(sides)

        result = Always20().roll("1d20")
        assert result.is_critical and not result.is_fumble
        assert result.natural_roll == 20

    def test_fumble_detection(self):
        class Always1(DiceEngine):
            def _roll_die(self, sides):
                return 1 if sides == 20 else super()._roll_die(sides)

        result = Always1().roll("1d20")
        assert result.is_fumble and not result.is_critical
        assert result.natural_roll == 1


class TestAdvantage:
    def test_advantage_takes_higher(self):
        eng = DiceEngine(seed=7)
        for _ in range(20):
            r = eng.roll("1d20", advantage=True)
            if r.advantage_data:
                assert r.natural_roll == max(r.advantage_data.roll1, r.advantage_data.roll2)

    def test_disadvantage_takes_lower(self):
        eng = DiceEngine(seed=7)
        for _ in range(20):
            r = eng.roll("1d20", disadvantage=True)
            if r.advantage_data:
                assert r.natural_roll == min(r.advantage_data.roll1, r.advantage_data.roll2)

    def test_advantage_data_present(self):
        r = DiceEngine().roll("1d20", advantage=True)
        assert r.advantage_data is not None
        assert r.had_advantage is True

    def test_advantage_only_on_single_d20(self):
        # 2d20 is not a single-d20 roll → no advantage data.
        assert DiceEngine().roll("2d20", advantage=True).advantage_data is None


class TestSpecialRolls:
    def test_attack_resolves_hit(self):
        r = DiceEngine().roll_attack(modifier=5, target_ac=15)
        assert isinstance(r, AttackRoll)
        assert r.target_ac == 15
        assert isinstance(r.is_hit, bool)

    def test_attack_without_ac_leaves_hit_none(self):
        assert DiceEngine().roll_attack(modifier=5).is_hit is None

    def test_save_resolves_success(self):
        r = DiceEngine().roll_save(modifier=3, dc=13)
        assert isinstance(r, SaveRoll)
        assert r.dc == 13 and isinstance(r.is_success, bool)

    def test_damage_critical_doubles_dice(self):
        eng = DiceEngine(seed=42)
        crit = eng.roll_damage("2d6+3", is_critical=True)
        assert crit.is_critical_damage is True
        assert "4d6" in str(crit.roll.dice_results[0].dice_group)
        assert crit.original_expression == "2d6+3"

    def test_initiative(self):
        r = DiceEngine().roll_initiative(modifier=3)
        assert isinstance(r, ExpressionResult)
        assert 4 <= r.total <= 23

    def test_stat_array(self):
        r = DiceEngine().roll_stat_array("4d6kh3")
        assert isinstance(r, StatArray)
        assert len(r.scores) == 6
        assert all(3 <= s <= 18 for s in r.scores)
        assert list(r.scores) == sorted(r.scores, reverse=True)
        assert len(r.roll_details) == 6

    def test_death_save(self):
        r = DiceEngine().roll_death_save()
        assert r.outcome in ("success", "failure", "critical_success", "critical_failure")
        assert r.successes in (0, 1)
        assert r.failures in (0, 1, 2)


class TestHitDice:
    def test_single_level(self):
        r = DiceEngine().roll_hit_dice("d8", con_modifier=2, level=1)
        assert r.hit_die == "d8"
        assert len(r.rolls) == 1
        assert r.total_hp >= 1

    def test_multiple_levels(self):
        r = DiceEngine().roll_hit_dice("d10", con_modifier=3, level=5)
        assert len(r.rolls) == 5 and r.level == 5

    def test_minimum_1_hp_per_level(self):
        class AlwaysOne(DiceEngine):
            def _roll_die(self, sides):
                return 1

        r = AlwaysOne().roll_hit_dice("d6", con_modifier=-3, level=1)
        assert r.rolls[0].hp_gained >= 1


class TestRngAndDeterminism:
    def test_seeded_engines_match(self):
        a = DiceEngine(seed=123)
        b = DiceEngine(seed=123)
        seq_a = [a.roll("1d20").total for _ in range(20)]
        seq_b = [b.roll("1d20").total for _ in range(20)]
        assert seq_a == seq_b  # reproducible stream

    def test_injected_rng_is_used(self):
        import random
        # Injecting a seeded Random is equivalent to seeding the engine.
        injected = DiceEngine(rng=random.Random(999))
        seeded = DiceEngine(seed=999)
        assert [injected.roll("3d6").total for _ in range(10)] == \
               [seeded.roll("3d6").total for _ in range(10)]

    def test_system_random_injection_runs(self):
        # secrets.SystemRandom is a random.Random subclass → drop-in for production.
        eng = DiceEngine(rng=secrets.SystemRandom())
        for _ in range(50):
            assert 1 <= eng.roll("1d20").total <= 20

    def test_results_are_frozen(self):
        result = DiceEngine(seed=1).roll("1d20")
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.total = 999  # type: ignore[misc]


class TestTermination:
    """Pathological reroll/explode groups must terminate, not hang (review #1)."""

    def test_explode_on_one_sided_die_terminates(self):
        # 1d1! would explode forever (every face is the max); guard skips exploding.
        result = DiceEngine(seed=1).roll("1d1!")
        assert result.total == 1
        assert result.dice_results[0].exploded_rolls == ()

    def test_reroll_covering_all_faces_terminates(self):
        # 1d2r1,2 — every face is in the reroll set, so rerolling can never escape.
        result = DiceEngine(seed=1).roll("1d2r1,2")
        assert result.total in (1, 2)  # kept the original roll, did not loop

    def test_runaway_explode_is_capped(self):
        # A die that always rolls its max would explode forever without the cap.
        class AlwaysMax(DiceEngine):
            def _roll_die(self, sides):
                return sides

        result = AlwaysMax().roll("1d6!")
        exploded = result.dice_results[0].exploded_rolls
        assert len(exploded) == _MAX_DIE_ITERATIONS  # capped, terminated

    def test_runaway_reroll_is_capped(self):
        # Always rolling a 1 with reroll-on-1 (partial set) would loop forever uncapped.
        class AlwaysOne(DiceEngine):
            def _roll_die(self, sides):
                return 1

        result = AlwaysOne().roll("1d6r1")  # 1 in {1}, but {1} != all faces
        assert result.total == 1  # terminated at the cap


class TestRerollParsing:
    """reroll-once must be detected per-group, not from the whole expression (review #2)."""

    def test_r_is_keep_rerolling(self):
        assert DiceEngine().parse_expression("2d6r1").dice_groups[0].reroll_once is False

    def test_ro_is_reroll_once(self):
        assert DiceEngine().parse_expression("2d6ro1").dice_groups[0].reroll_once is True

    def test_ro_group_does_not_contaminate_an_r_group(self):
        groups = DiceEngine().parse_expression("2d6r1+1d8ro2").dice_groups
        assert groups[0].reroll_once is False  # the 'r1' group — was wrongly True before
        assert groups[1].reroll_once is True  # the 'ro2' group


class TestHashableImmutable:
    """The result value types are genuinely immutable: tuples, hashable (review #3)."""

    def test_sequence_fields_are_tuples(self):
        result = DiceEngine(seed=1).roll("4d6kh3")
        assert isinstance(result.dice_results, tuple)
        assert isinstance(result.individual_rolls, tuple)
        rr = result.dice_results[0]
        assert isinstance(rr.all_rolls, tuple)
        assert isinstance(rr.kept_rolls, tuple)
        assert isinstance(rr.dice_group.reroll_on, tuple)

    def test_dice_group_is_hashable_and_set_usable(self):
        a = DiceGroup(count=1, sides=6)
        b = DiceGroup(count=1, sides=6)
        assert hash(a) == hash(b)
        assert len({a, b}) == 1  # value-equal, dedups in a set

    def test_results_are_hashable_and_dict_keyable(self):
        result = DiceEngine(seed=1).roll("2d6")
        assert isinstance(hash(result), int)
        assert isinstance(hash(result.dice_results[0]), int)
        {result: "ok"}  # usable as a dict key without raising

    def test_reroll_on_with_values_is_hashable(self):
        g = DiceEngine().parse_expression("2d6r1,2").dice_groups[0]
        assert g.reroll_on == (1, 2)
        assert isinstance(hash(g), int)


def test_top_level_export_is_same_class():
    assert TopLevelDiceEngine is DiceEngine
