"""Combat rules — damage/temp HP/healing/death saves over the pure CombatantState.

Pure-calculator numbers mirror the original storyflow combat-service suite; the state
transitions verify the rules extracted from its (formerly SQL-bound) async methods.
"""

import dataclasses

import pytest

from dndwright.combat import (
    CombatantState,
    DamageApplication,
    HPChange,
    apply_damage,
    apply_healing,
    calculate_damage_application,
    reset_death_saves,
    roll_death_save,
    set_temp_hp,
    stabilize,
)
from dndwright.dice import DiceEngine


class FixedRoll(DiceEngine):
    """A DiceEngine whose d20 always lands on a chosen face (for death-save tests)."""

    def __init__(self, face: int):
        super().__init__(seed=0)
        self._face = face

    def _roll_die(self, sides):
        return self._face if sides == 20 else super()._roll_die(sides)


class TestCalculateDamageApplication:
    def test_no_temp_hp(self):
        r = calculate_damage_application(current_hp=30, max_hp=30, temp_hp=0, damage=10)
        assert (r.total_damage, r.absorbed_by_temp_hp, r.damage_to_hp) == (10, 0, 10)
        assert r.overkill == 0 and r.is_massive_damage is False

    def test_temp_hp_partial_absorb(self):
        r = calculate_damage_application(current_hp=30, max_hp=30, temp_hp=5, damage=10)
        assert r.absorbed_by_temp_hp == 5 and r.damage_to_hp == 5

    def test_temp_hp_absorbs_all(self):
        r = calculate_damage_application(current_hp=30, max_hp=30, temp_hp=15, damage=10)
        assert r.absorbed_by_temp_hp == 10 and r.damage_to_hp == 0

    def test_overkill(self):
        r = calculate_damage_application(current_hp=10, max_hp=30, temp_hp=0, damage=25)
        assert r.damage_to_hp == 10 and r.overkill == 15

    def test_massive_damage(self):
        r = calculate_damage_application(current_hp=30, max_hp=30, temp_hp=0, damage=60)
        assert r.overkill == 30 and r.is_massive_damage is True


class TestApplyDamage:
    def test_basic_damage(self):
        state, app = apply_damage(CombatantState(current_hp=30, max_hp=30), 10)
        assert state.current_hp == 20
        assert isinstance(app, DamageApplication) and app.damage_to_hp == 10

    def test_temp_hp_absorbs_first(self):
        state, app = apply_damage(CombatantState(current_hp=30, max_hp=30, temp_hp=8), 10)
        assert app.absorbed_by_temp_hp == 8
        assert state.temp_hp == 0 and state.current_hp == 28

    def test_hp_floors_at_zero(self):
        # 20 damage → 0 HP with overkill 15 (< max 30, so not massive): dying, not dead.
        state, _ = apply_damage(CombatantState(current_hp=5, max_hp=30), 20)
        assert state.current_hp == 0 and state.is_dying

    def test_massive_damage_is_instant_death(self):
        state, app = apply_damage(CombatantState(current_hp=30, max_hp=30), 60)
        assert app.is_massive_damage is True
        assert state.is_dead and state.death_save_failures == 3

    def test_massive_damage_no_instant_death_when_disabled(self):
        # Monsters that don't make death saves: just drop to 0, not "dead by saves".
        state, app = apply_damage(
            CombatantState(current_hp=30, max_hp=30), 60, instant_death_on_massive=False
        )
        assert app.is_massive_damage is True
        assert state.current_hp == 0 and not state.is_dead


class TestApplyHealing:
    def test_heals(self):
        state, change = apply_healing(CombatantState(current_hp=5, max_hp=30), 10)
        assert state.current_hp == 15
        assert isinstance(change, HPChange) and change.hp_change == 10

    def test_capped_at_max(self):
        state, change = apply_healing(CombatantState(current_hp=25, max_hp=30), 100)
        assert state.current_hp == 30 and change.hp_change == 5

    def test_healing_from_zero_resets_saves_and_stabilizes(self):
        downed = CombatantState(current_hp=0, max_hp=30, death_save_failures=2,
                                death_save_successes=1)
        state, change = apply_healing(downed, 7)
        assert state.current_hp == 7
        assert state.death_save_failures == 0 and state.death_save_successes == 0
        assert change.was_healed_from_zero and change.stabilized


class TestTempHP:
    def test_grant(self):
        assert set_temp_hp(CombatantState(current_hp=10, max_hp=10), 5).temp_hp == 5

    def test_does_not_stack_takes_higher(self):
        base = CombatantState(current_hp=10, max_hp=10, temp_hp=8)
        assert set_temp_hp(base, 5).temp_hp == 8   # keep existing higher value
        assert set_temp_hp(base, 12).temp_hp == 12  # replace with higher


class TestDeathSaves:
    def test_success_increments(self):
        state, r = roll_death_save(CombatantState(0, 30), FixedRoll(15))
        assert r.is_success and not r.is_failure
        assert state.death_save_successes == 1

    def test_failure_increments(self):
        state, r = roll_death_save(CombatantState(0, 30), FixedRoll(7))
        assert r.is_failure and not r.is_success
        assert state.death_save_failures == 1

    def test_nat_20_regains_1_hp_and_clears_saves(self):
        downed = CombatantState(0, 30, death_save_successes=1, death_save_failures=2)
        state, r = roll_death_save(downed, FixedRoll(20))
        assert r.is_critical_success
        assert state.current_hp == 1
        assert state.death_save_successes == 0 and state.death_save_failures == 0

    def test_nat_1_counts_as_two_failures(self):
        state, r = roll_death_save(CombatantState(0, 30), FixedRoll(1))
        assert r.is_critical_failure and r.is_failure
        assert state.death_save_failures == 2

    def test_three_successes_stabilizes(self):
        state = CombatantState(0, 30, death_save_successes=2)
        state, r = roll_death_save(state, FixedRoll(12))
        assert state.death_save_successes == 3
        assert state.is_stable and r.is_stable

    def test_three_failures_dies(self):
        state = CombatantState(0, 30, death_save_failures=2)
        state, r = roll_death_save(state, FixedRoll(5))
        assert state.death_save_failures == 3
        assert state.is_dead and r.is_dead

    def test_manual_roll(self):
        state, r = roll_death_save(CombatantState(0, 30), DiceEngine(seed=1), manual_roll=18)
        assert r.roll == 18 and r.is_success

    def test_no_op_when_already_stable(self):
        stable = CombatantState(0, 30, death_save_successes=3)
        state, r = roll_death_save(stable, FixedRoll(1))
        assert r.no_op and state == stable  # the nat-1 did not register

    def test_no_op_when_already_dead(self):
        dead = CombatantState(0, 30, death_save_failures=3)
        state, r = roll_death_save(dead, FixedRoll(20))
        assert r.no_op and state == dead

    def test_seeded_engine_is_deterministic(self):
        a, _ = roll_death_save(CombatantState(0, 30), DiceEngine(seed=42))
        b, _ = roll_death_save(CombatantState(0, 30), DiceEngine(seed=42))
        assert a == b


class TestStabilizeAndReset:
    def test_stabilize_sets_three_successes(self):
        state = stabilize(CombatantState(0, 30, death_save_failures=2))
        assert state.is_stable and state.death_save_failures == 0

    def test_cannot_stabilize_dead(self):
        dead = CombatantState(0, 30, death_save_failures=3)
        assert stabilize(dead) == dead  # unchanged

    def test_reset_clears_tallies(self):
        state = reset_death_saves(CombatantState(0, 30, death_save_successes=2,
                                                 death_save_failures=1))
        assert state.death_save_successes == 0 and state.death_save_failures == 0


class TestCombatantStateProperties:
    def test_derived_flags(self):
        assert CombatantState(0, 30, death_save_failures=3).is_dead
        assert CombatantState(0, 30, death_save_successes=3).is_stable
        assert CombatantState(0, 30).is_dying
        assert not CombatantState(5, 30).is_dying

    def test_hp_percentage(self):
        assert CombatantState(15, 30).hp_percentage == 50.0
        assert CombatantState(1, 0).hp_percentage == 0.0  # no divide-by-zero

    def test_state_is_frozen_and_hashable(self):
        s = CombatantState(10, 30, temp_hp=5)
        with pytest.raises(dataclasses.FrozenInstanceError):
            s.current_hp = 0  # type: ignore[misc]
        assert isinstance(hash(s), int)
        assert len({s, CombatantState(10, 30, temp_hp=5)}) == 1  # value-equal


class TestPurity:
    def test_input_state_is_not_mutated(self):
        original = CombatantState(current_hp=30, max_hp=30, temp_hp=5)
        apply_damage(original, 10)
        apply_healing(original, 5)
        set_temp_hp(original, 99)
        assert original == CombatantState(current_hp=30, max_hp=30, temp_hp=5)
