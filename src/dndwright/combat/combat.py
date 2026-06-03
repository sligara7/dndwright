"""Pure D&D 5e combat rules — HP, temporary HP, death saves, stabilization.

Identity-free and persistence-free: combat state is a frozen :class:`CombatantState`
value object (no IDs, no database). Every operation is a pure function of the form
``(state, input) -> (new_state, explanation)`` — immutable and deterministic — so it
composes with any storage / broadcast layer (your adapter loads a row, calls these,
writes the result back).

    from dndwright.combat import CombatantState, apply_damage, apply_healing
    from dndwright.dice import DiceEngine

    state = CombatantState(current_hp=12, max_hp=12)
    state, applied = apply_damage(state, 15)     # -> (new state, DamageApplication)
    state, save = roll_death_save(state, DiceEngine(seed=1))

Death-save model (5e): a d20 vs DC 10. 10+ is a success, 9- a failure; a natural 20
regains 1 HP and clears all saves; a natural 1 counts as two failures; three successes
stabilises, three failures kills. ``is_stable`` / ``is_dead`` are derived from the
running success/failure tallies, so there is a single source of truth.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from typing import Any

from ..dice import DiceEngine

DEATH_SAVE_DC = 10
DEATH_SAVES_TO_STABILIZE = 3
DEATH_SAVES_TO_DIE = 3

# The 13 SRD 5.2 damage types. A combatant's resistances/immunities/vulnerabilities are
# subsets of these, stored as plain data — composable (union contributions from species,
# items, conditions, …) so they can be built up "lego" style.
DAMAGE_TYPES = frozenset({
    "acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic",
    "piercing", "poison", "psychic", "radiant", "slashing", "thunder",
})


def damage_multiplier(
    damage_type: str | None,
    *,
    resistances: Iterable[str] = (),
    immunities: Iterable[str] = (),
    vulnerabilities: Iterable[str] = (),
) -> float:
    """The 5e damage multiplier for a typed hit, from the target's defense sets.

    ``0.0`` if immune, ``0.5`` if resistant, ``2.0`` if vulnerable, ``1.0`` otherwise.
    Resistance and vulnerability to the *same* type cancel (``0.5 × 2 = 1.0``), per 5e;
    immunity wins outright. An untyped hit (``damage_type=None``) is always ``1.0``.

    Driven entirely by data (set membership) — no hard-coded damage-type lists — so the
    defense sets can be composed from any number of sources. Matching is case-insensitive.
    """
    if damage_type is None:
        return 1.0
    dt = damage_type.lower()
    if dt in {t.lower() for t in immunities}:
        return 0.0
    mult = 1.0
    if dt in {t.lower() for t in resistances}:
        mult *= 0.5
    if dt in {t.lower() for t in vulnerabilities}:
        mult *= 2.0
    return mult


def clean_damage_types(values: Any) -> tuple[str, ...]:
    """Normalise a collection of damage-type strings: lower-cased, de-duplicated, sorted, and
    intersected with :data:`DAMAGE_TYPES` so narrative junk (``"Fire Resistance"``, prose like
    ``"nonmagical piercing"``) is dropped. The single source of truth for damage-type cleaning —
    used by :func:`combatant_defenses` and by callers that build resistance contributions.
    """
    if not values:
        return ()
    return tuple(sorted({str(v).lower() for v in values} & DAMAGE_TYPES))


def combatant_defenses(computed: Mapping[str, Any]) -> dict[str, frozenset[str]]:
    """Pull the damage-defence channels out of an evaluated character graph (or a plain
    ``{"resistances": [...], "immunities": [...], "vulnerabilities": [...]}`` snapshot).

    ``computed`` is typically the raw dict from :func:`dndwright.evaluate` (whose ``resistances``
    / ``immunities`` / ``vulnerabilities`` nodes — see ``DAMAGE_CHANNELS`` — are unions of the
    composed components' contributions), but any mapping with those keys works. Returns exactly
    the kwargs :class:`CombatantState` wants::

        computed = evaluate(compose(DND_5E_2024_RULESET, *components), inputs)
        state = CombatantState(current_hp=hp, max_hp=hp, **combatant_defenses(computed))

    Members are cleaned via :func:`clean_damage_types` (lower-cased, intersected with
    :data:`DAMAGE_TYPES`), so junk can't slip in and silently break multiplier matching.
    """
    return {
        "resistances": frozenset(clean_damage_types(computed.get("resistances"))),
        "immunities": frozenset(clean_damage_types(computed.get("immunities"))),
        "vulnerabilities": frozenset(clean_damage_types(computed.get("vulnerabilities"))),
    }


@dataclass(frozen=True)
class CombatantState:
    """A creature's combat state — just the numbers, no identity or persistence.

    ``is_stable`` / ``is_dead`` / ``is_dying`` are derived from the death-save tallies
    (and HP), so they cannot drift out of sync with the counts.
    """

    current_hp: int
    max_hp: int
    temp_hp: int = 0
    death_save_successes: int = 0
    death_save_failures: int = 0
    # Defenses as plain, composable data (subsets of DAMAGE_TYPES). frozensets keep the
    # state immutable + hashable; build them up by unioning contributions from species,
    # items, conditions, etc. Drive apply_damage's damage-type multiplier.
    resistances: frozenset[str] = frozenset()
    immunities: frozenset[str] = frozenset()
    vulnerabilities: frozenset[str] = frozenset()

    @property
    def is_dead(self) -> bool:
        return self.death_save_failures >= DEATH_SAVES_TO_DIE

    @property
    def is_stable(self) -> bool:
        return self.death_save_successes >= DEATH_SAVES_TO_STABILIZE

    @property
    def is_dying(self) -> bool:
        """At 0 HP, still making death saves (not yet stable or dead)."""
        return self.current_hp == 0 and not self.is_dead and not self.is_stable

    @property
    def hp_percentage(self) -> float:
        return (self.current_hp / self.max_hp * 100.0) if self.max_hp else 0.0


@dataclass(frozen=True)
class DamageApplication:
    """How a hit was absorbed: resistance multiplier, then temp HP, then HP, then overkill."""

    total_damage: int  # effective damage after the resistance/vulnerability/immunity multiplier
    absorbed_by_temp_hp: int
    damage_to_hp: int
    overkill: int  # damage beyond 0 HP
    is_massive_damage: bool  # overkill >= max HP → instant death (5e)
    raw_damage: int = 0  # the pre-multiplier damage rolled
    multiplier: float = 1.0  # 0 immune / 0.5 resist / 1 normal / 2 vulnerable


@dataclass(frozen=True)
class HPChange:
    """The before/after of an HP change (used for healing)."""

    old_hp: int
    new_hp: int
    max_hp: int
    temp_hp: int
    hp_change: int  # signed: positive = healed, negative = lost
    hp_percentage: float
    went_down: bool = False  # dropped to 0 this change
    was_healed_from_zero: bool = False
    stabilized: bool = False  # regained consciousness from 0 HP


@dataclass(frozen=True)
class DeathSaveResult:
    """The outcome of one death saving throw applied to the running tally."""

    roll: int  # the d20 face (0 when no save was rolled — see no_op)
    is_success: bool
    is_failure: bool
    is_critical_success: bool  # natural 20 → regain 1 HP
    is_critical_failure: bool  # natural 1 → two failures
    total_successes: int
    total_failures: int
    is_stable: bool
    is_dead: bool
    no_op: bool = False  # the combatant was already stable/dead; nothing changed


def calculate_damage_application(
    current_hp: int, max_hp: int, temp_hp: int, damage: int
) -> DamageApplication:
    """Work out how ``damage`` lands: temp HP absorbs first, then HP, then overkill."""
    absorbed = min(temp_hp, damage)
    remaining = damage - absorbed
    damage_to_hp = min(current_hp, remaining)
    overkill = remaining - damage_to_hp
    return DamageApplication(
        total_damage=damage,
        absorbed_by_temp_hp=absorbed,
        damage_to_hp=damage_to_hp,
        overkill=overkill,
        is_massive_damage=overkill >= max_hp,
        raw_damage=damage,
        multiplier=1.0,
    )


def apply_damage(
    state: CombatantState,
    amount: int,
    *,
    damage_type: str | None = None,
    instant_death_on_massive: bool = True,
) -> tuple[CombatantState, DamageApplication]:
    """Apply ``amount`` damage. Resistance/vulnerability/immunity first (by ``damage_type``
    against the state's defense sets), then temp HP absorbs, then HP floors at 0.

    A typed hit is scaled by :func:`damage_multiplier` (immune → 0, resistant → halved
    rounded down, vulnerable → doubled) using ``state.resistances`` / ``immunities`` /
    ``vulnerabilities`` before anything else, per 5e. Pass ``damage_type=None`` for an
    untyped hit (no scaling).

    If the leftover damage past 0 HP is at least the creature's max HP it is *massive
    damage* — instant death (5e). ``instant_death_on_massive`` gates that rule: pass
    ``False`` for creatures that don't make death saves (most monsters just drop to 0).
    """
    mult = damage_multiplier(
        damage_type,
        resistances=state.resistances,
        immunities=state.immunities,
        vulnerabilities=state.vulnerabilities,
    )
    effective = int(amount * mult)  # int() floors the 0.5 case, per 5e round-down
    app = calculate_damage_application(state.current_hp, state.max_hp, state.temp_hp, effective)
    app = replace(app, raw_damage=amount, multiplier=mult)
    new_temp = max(0, state.temp_hp - app.absorbed_by_temp_hp)
    new_hp = max(0, state.current_hp - app.damage_to_hp)
    failures = state.death_save_failures
    if app.is_massive_damage and instant_death_on_massive:
        failures = DEATH_SAVES_TO_DIE
    new_state = replace(
        state, current_hp=new_hp, temp_hp=new_temp, death_save_failures=failures
    )
    return new_state, app


def apply_healing(state: CombatantState, amount: int) -> tuple[CombatantState, HPChange]:
    """Heal ``amount`` (capped at max HP). Healing from 0 HP clears death saves."""
    was_at_zero = state.current_hp == 0
    new_hp = min(state.max_hp, state.current_hp + amount)
    healed = new_hp - state.current_hp
    successes, failures = state.death_save_successes, state.death_save_failures
    healed_from_zero = was_at_zero and new_hp > 0
    if healed_from_zero:
        successes = failures = 0
    new_state = replace(
        state, current_hp=new_hp, death_save_successes=successes, death_save_failures=failures
    )
    change = HPChange(
        old_hp=state.current_hp,
        new_hp=new_hp,
        max_hp=state.max_hp,
        temp_hp=state.temp_hp,
        hp_change=healed,
        hp_percentage=new_state.hp_percentage,
        was_healed_from_zero=healed_from_zero,
        stabilized=healed_from_zero,
    )
    return new_state, change


def set_temp_hp(state: CombatantState, amount: int) -> CombatantState:
    """Grant temporary HP. 5e: temp HP doesn't stack — keep the higher value."""
    return replace(state, temp_hp=max(state.temp_hp, amount))


def roll_death_save(
    state: CombatantState, engine: DiceEngine, *, manual_roll: int | None = None
) -> tuple[CombatantState, DeathSaveResult]:
    """Roll (or apply ``manual_roll`` as) one death saving throw and update the tally.

    No-ops (returns ``no_op=True``) when the combatant is already stable or dead.
    """
    if state.is_stable or state.is_dead:
        return state, DeathSaveResult(
            roll=0,
            is_success=False,
            is_failure=False,
            is_critical_success=False,
            is_critical_failure=False,
            total_successes=state.death_save_successes,
            total_failures=state.death_save_failures,
            is_stable=state.is_stable,
            is_dead=state.is_dead,
            no_op=True,
        )

    roll = manual_roll if manual_roll is not None else (engine.roll("1d20").natural_roll or 0)
    is_nat20 = roll == 20
    is_nat1 = roll == 1
    succeeded = roll >= DEATH_SAVE_DC

    current_hp = state.current_hp
    successes = state.death_save_successes
    failures = state.death_save_failures
    if is_nat20:
        current_hp, successes, failures = 1, 0, 0  # regain consciousness, clear saves
    elif is_nat1:
        failures += 2
    elif succeeded:
        successes += 1
    else:
        failures += 1

    new_state = replace(
        state, current_hp=current_hp, death_save_successes=successes, death_save_failures=failures
    )
    result = DeathSaveResult(
        roll=roll,
        is_success=succeeded and not is_nat1,
        is_failure=(not succeeded) or is_nat1,
        is_critical_success=is_nat20,
        is_critical_failure=is_nat1,
        total_successes=successes,
        total_failures=failures,
        is_stable=new_state.is_stable,
        is_dead=new_state.is_dead,
    )
    return new_state, result


def stabilize(state: CombatantState) -> CombatantState:
    """Stabilise a dying creature (Spare the Dying, a medicine check). A dead creature
    cannot be stabilised. Sets the save tally to stable without restoring HP."""
    if state.is_dead:
        return state
    return replace(
        state, death_save_successes=DEATH_SAVES_TO_STABILIZE, death_save_failures=0
    )


def reset_death_saves(state: CombatantState) -> CombatantState:
    """Clear both death-save tallies (e.g. on a long rest or revival)."""
    return replace(state, death_save_successes=0, death_save_failures=0)
