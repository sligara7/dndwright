"""Conditions — effects/flags from the catalog, implications/immunity, ticking, saves."""

import dataclasses

import pytest

from dndwright.combat.conditions import (
    ROUND_END,
    SAVE_ENDS,
    TURN_END,
    TURN_START,
    ActiveCondition,
    ConditionEffect,
    attempt_save,
    condition_effects,
    condition_names,
    implied_conditions,
    is_immune,
    tick_conditions,
)


class TestEffectsLookup:
    def test_known_condition_flags(self):
        e = condition_effects("paralyzed")
        assert isinstance(e, ConditionEffect)
        assert e.display_name == "Paralyzed"
        assert e.is_incapacitating and e.prevents_movement and e.prevents_actions
        assert e.grants_advantage_to_attackers

    def test_blinded_imposes_disadvantage(self):
        e = condition_effects("blinded")
        assert e.imposes_disadvantage_on_attacks and e.grants_advantage_to_attackers
        assert not e.is_incapacitating

    def test_name_is_case_insensitive(self):
        assert condition_effects("PRONE").name == "prone"

    def test_unknown_condition_is_empty_not_error(self):
        e = condition_effects("hexbound")  # homebrew, not in the SRD catalog
        assert e.effects == () and e.display_name == "Hexbound"

    def test_exhaustion_levels_are_cumulative(self):
        assert condition_effects("exhaustion", level=1).effects == (
            "Disadvantage on ability checks",
        )
        e3 = condition_effects("exhaustion", level=3)
        assert len(e3.effects) == 3 and e3.level == 3

    def test_effects_field_is_tuple_and_hashable(self):
        e = condition_effects("poisoned")
        assert isinstance(e.effects, tuple)
        assert isinstance(hash(e), int)

    def test_catalog_has_fifteen(self):
        assert len(condition_names()) == 15
        assert "unconscious" in condition_names()


class TestImplicationsAndImmunity:
    def test_implied_conditions(self):
        assert implied_conditions("unconscious") == ("incapacitated", "prone")
        assert implied_conditions("paralyzed") == ("incapacitated",)
        assert implied_conditions("blinded") == ()

    def test_immunity(self):
        assert is_immune(["petrified"], "poisoned") is True
        assert is_immune(["blinded"], "poisoned") is False
        assert is_immune([], "poisoned") is False


class TestTicking:
    def test_round_based_ticks_down(self):
        active = [ActiveCondition("hexed", "rounds", rounds_remaining=3)]
        [change] = tick_conditions(active, ROUND_END)
        assert change.change == "ticked" and change.rounds_remaining == 2

    def test_round_based_expires_at_zero(self):
        active = [ActiveCondition("hexed", "rounds", rounds_remaining=1)]
        [change] = tick_conditions(active, ROUND_END)
        assert change.change == "expired"

    def test_until_end_of_turn_removed_on_turn_end(self):
        active = [ActiveCondition("dazed", "until_end_of_turn")]
        assert tick_conditions(active, TURN_END)[0].change == "removed"
        assert tick_conditions(active, ROUND_END) == []  # wrong event → no change

    def test_until_start_of_turn_removed_on_turn_start(self):
        active = [ActiveCondition("warded", "until_start_of_turn")]
        assert tick_conditions(active, TURN_START)[0].change == "removed"

    def test_indefinite_conditions_never_tick(self):
        active = [ActiveCondition("prone", "indefinite")]
        assert tick_conditions(active, ROUND_END) == []
        assert tick_conditions(active, TURN_END) == []


class TestSaves:
    def test_successful_save_removes_condition(self):
        cond = ActiveCondition("poisoned", SAVE_ENDS, save_dc=13)
        r = attempt_save(cond, roll_total=15)
        assert r.is_success and r.condition_removed and r.reason == "saved"

    def test_failed_save_keeps_condition(self):
        cond = ActiveCondition("poisoned", SAVE_ENDS, save_dc=13)
        r = attempt_save(cond, roll_total=9)
        assert not r.is_success and not r.condition_removed and r.reason == "failed"

    def test_exactly_dc_succeeds(self):
        assert attempt_save(ActiveCondition("x", SAVE_ENDS, save_dc=13), 13).is_success

    def test_non_save_ends_condition_cannot_be_saved(self):
        r = attempt_save(ActiveCondition("prone", "indefinite"), 20)
        assert r.reason == "not_save_ends" and not r.condition_removed

    def test_save_ends_without_dc(self):
        r = attempt_save(ActiveCondition("x", SAVE_ENDS, save_dc=None), 20)
        assert r.reason == "no_dc"


class TestImmutability:
    def test_active_condition_frozen_and_hashable(self):
        c = ActiveCondition("poisoned", SAVE_ENDS, save_dc=13)
        with pytest.raises(dataclasses.FrozenInstanceError):
            c.save_dc = 0  # type: ignore[misc]
        assert isinstance(hash(c), int)
