"""Pure D&D 5e combat rules — HP, temp HP, death saves, stabilization, weapon attacks.

Identity-free, persistence-free value functions: state is a frozen
:class:`CombatantState`, and each op is ``(state, input) -> (new_state, explanation)``.

    from dndwright.combat import CombatantState, apply_damage, roll_death_save
    from dndwright.dice import DiceEngine

    s = CombatantState(current_hp=8, max_hp=20, temp_hp=3)
    s, applied = apply_damage(s, 10)          # temp HP absorbs first
    s, save = roll_death_save(s, DiceEngine(seed=1))

Depends on :mod:`dndwright.dice` (``roll_death_save`` takes a ``DiceEngine``).
"""

from . import conditions, initiative
from .combat import (
    DAMAGE_TYPES,
    DEATH_SAVE_DC,
    DEATH_SAVES_TO_DIE,
    DEATH_SAVES_TO_STABILIZE,
    CombatantState,
    DamageApplication,
    DeathSaveResult,
    HPChange,
    apply_damage,
    apply_healing,
    calculate_damage_application,
    clean_damage_types,
    combatant_defenses,
    damage_multiplier,
    reset_death_saves,
    roll_death_save,
    set_temp_hp,
    stabilize,
)
from .weapons import WeaponAttack, weapon_attack

__all__ = [
    # state + result value types
    "CombatantState",
    "DamageApplication",
    "HPChange",
    "DeathSaveResult",
    "WeaponAttack",
    # operations (state, input) -> (new_state, explanation)
    "apply_damage",
    "apply_healing",
    "set_temp_hp",
    "roll_death_save",
    "stabilize",
    "reset_death_saves",
    "calculate_damage_application",
    "damage_multiplier",
    "combatant_defenses",
    "clean_damage_types",
    "weapon_attack",
    # rule constants
    "DEATH_SAVE_DC",
    "DEATH_SAVES_TO_STABILIZE",
    "DEATH_SAVES_TO_DIE",
    "DAMAGE_TYPES",
    # submodules: initiative ordering + turn advancement; conditions tick/save
    "initiative",
    "conditions",
]
