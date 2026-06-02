"""Initiative — rolling, ordering (with DEX tie-break), and turn advancement."""

import dataclasses

import pytest

from dndwright.combat.initiative import (
    InitiativeEntry,
    InitiativeRoll,
    TurnAdvance,
    advance_turn,
    order_initiative,
    previous_turn,
    roll_initiative,
)
from dndwright.dice import DiceEngine


def _entry(name, total, dex=0, active=True):
    return InitiativeEntry(name=name, total=total, dexterity_modifier=dex, is_active=active)


class TestRollInitiative:
    def test_total_is_roll_plus_modifier(self):
        r = roll_initiative(DiceEngine(seed=1), modifier=3)
        assert isinstance(r, InitiativeRoll)
        assert r.total == r.roll + 3 and r.modifier == 3

    def test_manual_roll(self):
        r = roll_initiative(DiceEngine(seed=1), modifier=2, manual_roll=20)
        assert r.roll == 20 and r.total == 22 and r.is_natural_20 is True

    def test_seeded_is_deterministic(self):
        a = roll_initiative(DiceEngine(seed=9), modifier=1)
        b = roll_initiative(DiceEngine(seed=9), modifier=1)
        assert a == b


class TestOrdering:
    def test_sorts_by_total_desc(self):
        order = order_initiative([_entry("a", 9), _entry("b", 17), _entry("c", 12)])
        assert [e.name for e in order] == ["b", "c", "a"]

    def test_dex_modifier_breaks_ties(self):
        order = order_initiative([
            _entry("Goblin", 17, dex=2),
            _entry("Rogue", 17, dex=4),  # higher DEX wins the tie
        ])
        assert [e.name for e in order] == ["Rogue", "Goblin"]

    def test_full_tie_keeps_input_order(self):
        # equal total AND dex → stable sort preserves the given order
        order = order_initiative([_entry("first", 10, dex=1), _entry("second", 10, dex=1)])
        assert [e.name for e in order] == ["first", "second"]

    def test_returns_tuple(self):
        assert isinstance(order_initiative([_entry("a", 5)]), tuple)


class TestAdvanceTurn:
    def test_advances_to_next(self):
        order = order_initiative([_entry("a", 20), _entry("b", 15), _entry("c", 10)])
        t = advance_turn(order, round_number=1, turn_index=0)
        assert (t.turn_index, t.round_number, t.new_round) == (1, 1, False)

    def test_wrap_starts_new_round(self):
        order = order_initiative([_entry("a", 20), _entry("b", 15)])
        t = advance_turn(order, round_number=1, turn_index=1)  # last → wrap
        assert t.turn_index == 0 and t.new_round is True and t.round_number == 2

    def test_skips_inactive(self):
        order = (_entry("a", 20), _entry("b", 15, active=False), _entry("c", 10))
        t = advance_turn(order, round_number=1, turn_index=0)
        assert t.turn_index == 2  # 'b' is inactive, skipped

    def test_all_inactive_ends_combat(self):
        order = (_entry("a", 20, active=False),)
        t = advance_turn(order, round_number=2, turn_index=0)
        assert t.combat_ended is True

    def test_empty_order_ends_combat(self):
        assert advance_turn((), 1, 0).combat_ended is True


class TestPreviousTurn:
    def test_steps_back(self):
        order = order_initiative([_entry("a", 20), _entry("b", 15), _entry("c", 10)])
        t = previous_turn(order, round_number=1, turn_index=2)
        assert t.turn_index == 1

    def test_wrap_back_decrements_round(self):
        order = order_initiative([_entry("a", 20), _entry("b", 15)])
        t = previous_turn(order, round_number=3, turn_index=0)  # back past start
        assert t.turn_index == 1 and t.round_number == 2

    def test_round_floored_at_one(self):
        order = order_initiative([_entry("a", 20), _entry("b", 15)])
        t = previous_turn(order, round_number=1, turn_index=0)
        assert t.round_number == 1  # never below 1

    def test_skips_inactive(self):
        order = (_entry("a", 20), _entry("b", 15, active=False), _entry("c", 10))
        t = previous_turn(order, round_number=2, turn_index=2)
        assert t.turn_index == 0  # 'b' skipped


class TestImmutability:
    def test_entries_frozen_and_hashable(self):
        e = _entry("a", 17, dex=2)
        with pytest.raises(dataclasses.FrozenInstanceError):
            e.total = 0  # type: ignore[misc]
        assert isinstance(hash(e), int)
        assert len({e, _entry("a", 17, dex=2)}) == 1

    def test_turn_advance_is_frozen(self):
        t = TurnAdvance(round_number=1, turn_index=0)
        with pytest.raises(dataclasses.FrozenInstanceError):
            t.turn_index = 5  # type: ignore[misc]
