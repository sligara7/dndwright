"""Pure D&D 5e conditions — effects lookup, implications/immunity, duration ticking, saves.

Identity-free and persistence-free, like the rest of :mod:`dndwright.combat`. The
condition *catalog* (the 14 SRD conditions + exhaustion, with their effect text and
mechanical flags) is bundled data — ``dndwright.content.load_content("conditions")`` —
not hand-coded enums; this module is the rules layer over it.

    from dndwright.combat.conditions import (
        condition_effects, tick_conditions, attempt_save, ActiveCondition, ROUND_END,
    )

    condition_effects("paralyzed").grants_advantage_to_attackers   # True
    tick_conditions([ActiveCondition("hexed", "rounds", rounds_remaining=1)], ROUND_END)
    attempt_save(ActiveCondition("poisoned", "save_ends", save_dc=13), roll_total=15)

Operations are pure: ``tick_conditions`` / ``attempt_save`` report what *would* change;
your adapter applies the change to its store.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import lru_cache

# Duration types (mirror the values an active condition stores).
ROUNDS = "rounds"
UNTIL_END_OF_TURN = "until_end_of_turn"
UNTIL_START_OF_TURN = "until_start_of_turn"
CONCENTRATION = "concentration"
INDEFINITE = "indefinite"
SAVE_ENDS = "save_ends"
TIMED = "timed"

# Tick events.
ROUND_END = "round_end"
TURN_END = "turn_end"
TURN_START = "turn_start"

__all__ = [
    "ConditionEffect",
    "ActiveCondition",
    "ConditionChange",
    "SaveResult",
    "condition_effects",
    "condition_names",
    "implied_conditions",
    "is_immune",
    "tick_conditions",
    "attempt_save",
    "ROUNDS",
    "UNTIL_END_OF_TURN",
    "UNTIL_START_OF_TURN",
    "CONCENTRATION",
    "INDEFINITE",
    "SAVE_ENDS",
    "TIMED",
    "ROUND_END",
    "TURN_END",
    "TURN_START",
]


@dataclass(frozen=True)
class ConditionEffect:
    """A condition's effect text plus the mechanical flags that drive rules."""

    name: str
    display_name: str
    effects: tuple[str, ...]
    is_incapacitating: bool = False
    prevents_movement: bool = False
    prevents_actions: bool = False
    grants_advantage_to_attackers: bool = False
    imposes_disadvantage_on_attacks: bool = False
    level: int | None = None  # for exhaustion


@dataclass(frozen=True)
class ActiveCondition:
    """A condition currently on a creature — no IDs, just what the rules need."""

    name: str
    duration_type: str = INDEFINITE
    rounds_remaining: int | None = None
    save_dc: int | None = None
    level: int | None = None  # for exhaustion


@dataclass(frozen=True)
class ConditionChange:
    """A change a tick would make to one active condition."""

    name: str
    change: str  # "ticked" | "expired" | "removed"
    rounds_remaining: int | None = None  # the new value for a "ticked" change


@dataclass(frozen=True)
class SaveResult:
    """The outcome of a saving throw against a save-ends condition."""

    name: str
    roll_total: int
    dc: int | None
    is_success: bool
    condition_removed: bool
    reason: str  # "saved" | "failed" | "not_save_ends" | "no_dc"


@lru_cache(maxsize=1)
def _catalog() -> dict[str, dict]:
    """Name → catalog entry, loaded once from the bundled content."""
    from ..content import load_content

    return {entry["name"].lower(): entry for entry in load_content("conditions")}


def condition_names() -> tuple[str, ...]:
    """All known condition names (sorted)."""
    return tuple(sorted(_catalog()))


def condition_effects(name: str, level: int | None = None) -> ConditionEffect:
    """Look up a condition's effects + mechanical flags. Unknown names yield an empty
    effect (so callers can tolerate homebrew names without a crash)."""
    info = _catalog().get(name.lower())
    if info is None:
        return ConditionEffect(name=name.lower(), display_name=name.title(), effects=())

    if name.lower() == "exhaustion" and level:
        levels = info.get("levels", {})
        effects = tuple(levels[str(i)] for i in range(1, min(level, 6) + 1) if str(i) in levels)
    else:
        effects = tuple(info.get("effects", []))

    m = info.get("mechanics", {})
    return ConditionEffect(
        name=name.lower(),
        display_name=info.get("display_name", name.title()),
        effects=effects,
        is_incapacitating=m.get("incapacitating", False),
        prevents_movement=m.get("prevents_movement", False),
        prevents_actions=m.get("prevents_actions", False),
        grants_advantage_to_attackers=m.get("grants_advantage_to_attackers", False),
        imposes_disadvantage_on_attacks=m.get("imposes_disadvantage_on_attacks", False),
        level=level,
    )


def implied_conditions(name: str) -> tuple[str, ...]:
    """Conditions automatically implied by ``name`` (e.g. paralyzed → incapacitated)."""
    return tuple(_catalog().get(name.lower(), {}).get("implies", []))


def is_immune(existing_conditions: Iterable[str], condition_to_apply: str) -> bool:
    """Whether any current condition grants immunity to ``condition_to_apply``
    (e.g. petrified → immune to poisoned)."""
    target = condition_to_apply.lower()
    catalog = _catalog()
    return any(
        target in catalog.get(existing.lower(), {}).get("grants_immunity_to", [])
        for existing in existing_conditions
    )


def tick_conditions(
    active: Sequence[ActiveCondition], event: str
) -> list[ConditionChange]:
    """Report the changes ``event`` makes to ``active`` (the caller applies them).

    - ``ROUND_END``: round-based conditions decrement; ``"ticked"`` while time remains,
      ``"expired"`` when it runs out.
    - ``TURN_END`` / ``TURN_START``: until-end/until-start-of-turn conditions are
      ``"removed"``.
    Conditions not affected by the event are omitted.
    """
    changes: list[ConditionChange] = []
    for c in active:
        if event == ROUND_END and c.duration_type == ROUNDS and c.rounds_remaining is not None:
            remaining = c.rounds_remaining - 1
            if remaining <= 0:
                changes.append(ConditionChange(c.name, "expired"))
            else:
                changes.append(ConditionChange(c.name, "ticked", rounds_remaining=remaining))
        elif event == TURN_END and c.duration_type == UNTIL_END_OF_TURN:
            changes.append(ConditionChange(c.name, "removed"))
        elif event == TURN_START and c.duration_type == UNTIL_START_OF_TURN:
            changes.append(ConditionChange(c.name, "removed"))
    return changes


def attempt_save(condition: ActiveCondition, roll_total: int) -> SaveResult:
    """Resolve a saving throw against a save-ends ``condition``.

    Only save-ends conditions with a DC can be saved against; the condition is removed
    on a roll of at least its DC.
    """
    if condition.duration_type != SAVE_ENDS:
        return SaveResult(condition.name, roll_total, None, False, False, "not_save_ends")
    if not condition.save_dc:
        return SaveResult(condition.name, roll_total, None, False, False, "no_dc")
    success = roll_total >= condition.save_dc
    return SaveResult(
        name=condition.name,
        roll_total=roll_total,
        dc=condition.save_dc,
        is_success=success,
        condition_removed=success,
        reason="saved" if success else "failed",
    )
