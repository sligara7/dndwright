"""Pure D&D 5e initiative — rolling, ordering, and turn advancement.

Identity-free and persistence-free, like the rest of :mod:`dndwright.combat`. An
initiative order is a tuple of frozen :class:`InitiativeEntry` value objects; turn
advancement is a pure function of ``(order, round, turn_index)``.

    from dndwright.combat.initiative import (
        InitiativeEntry, order_initiative, advance_turn,
    )

    order = order_initiative([
        InitiativeEntry(name="Goblin", total=17, dexterity_modifier=2),
        InitiativeEntry(name="Rogue",  total=17, dexterity_modifier=4),  # wins the tie
        InitiativeEntry(name="Ogre",   total=9,  dexterity_modifier=-1),
    ])
    turn = advance_turn(order, round_number=1, turn_index=0)  # -> TurnAdvance

5e tie-break: higher initiative total first; on a tie, higher DEX modifier; still tied,
input order is preserved (a stable sort — the caller decides the final roll-off).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from ..dice import DiceEngine

__all__ = [
    "InitiativeEntry",
    "InitiativeRoll",
    "TurnAdvance",
    "roll_initiative",
    "order_initiative",
    "advance_turn",
    "previous_turn",
]


@dataclass(frozen=True)
class InitiativeEntry:
    """One combatant in the initiative order — no IDs, just what ordering needs."""

    name: str
    total: int  # initiative total (roll + modifier)
    dexterity_modifier: int = 0  # tie-breaker
    is_active: bool = True  # inactive entries are skipped when advancing turns


@dataclass(frozen=True)
class InitiativeRoll:
    """The outcome of rolling initiative for one combatant."""

    roll: int
    modifier: int
    total: int
    is_natural_20: bool


@dataclass(frozen=True)
class TurnAdvance:
    """The result of moving the turn marker."""

    round_number: int
    turn_index: int
    new_round: bool = False  # advancing wrapped past the end → a new round began
    combat_ended: bool = False  # no active combatants remain


def roll_initiative(
    engine: DiceEngine, modifier: int = 0, *, manual_roll: int | None = None
) -> InitiativeRoll:
    """Roll 1d20 + ``modifier`` for initiative (or apply ``manual_roll``)."""
    roll = manual_roll if manual_roll is not None else (engine.roll("1d20").natural_roll or 0)
    return InitiativeRoll(
        roll=roll, modifier=modifier, total=roll + modifier, is_natural_20=roll == 20
    )


def order_initiative(entries: Iterable[InitiativeEntry]) -> tuple[InitiativeEntry, ...]:
    """Sort ``entries`` into initiative order: total desc, then DEX modifier desc.

    The sort is stable, so entries tied on both keep their input order (the 5e "roll off"
    is the caller's to resolve before calling, e.g. by ordering the input).
    """
    return tuple(sorted(entries, key=lambda e: (-e.total, -e.dexterity_modifier)))


def advance_turn(
    order: Sequence[InitiativeEntry], round_number: int, turn_index: int
) -> TurnAdvance:
    """Advance to the next active combatant, incrementing the round on wrap-around."""
    n = len(order)
    if n == 0 or not any(e.is_active for e in order):
        return TurnAdvance(round_number, turn_index, combat_ended=True)

    next_index = turn_index
    for _ in range(n):
        next_index = (next_index + 1) % n
        if order[next_index].is_active:
            new_round = next_index <= turn_index  # wrapped past the end
            return TurnAdvance(
                round_number=round_number + (1 if new_round else 0),
                turn_index=next_index,
                new_round=new_round,
            )
    return TurnAdvance(round_number, turn_index, combat_ended=True)


def previous_turn(
    order: Sequence[InitiativeEntry], round_number: int, turn_index: int
) -> TurnAdvance:
    """Step the turn marker back to the previous active combatant (for corrections).

    Does not undo any actions — only moves the marker. Wrapping backward past the start
    decrements the round (floored at 1).
    """
    n = len(order)
    if n == 0 or not any(e.is_active for e in order):
        return TurnAdvance(round_number, turn_index, combat_ended=True)

    prev_index = turn_index
    went_back_a_round = False
    for _ in range(n):
        prev_index = (prev_index - 1) % n
        if prev_index >= turn_index and round_number > 1:
            went_back_a_round = True
        if order[prev_index].is_active:
            break

    new_round_number = max(1, round_number - 1) if went_back_a_round else round_number
    return TurnAdvance(round_number=new_round_number, turn_index=prev_index)
