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
from .conditions import (
    CONCENTRATION,
    INDEFINITE,
    ROUND_END,
    ROUNDS,
    SAVE_ENDS,
    TIMED,
    TURN_END,
    TURN_START,
    UNTIL_END_OF_TURN,
    UNTIL_START_OF_TURN,
    ActiveCondition,
    ConditionChange,
    ConditionEffect,
    SaveResult,
    attempt_save,
    condition_effects,
    condition_names,
    implied_conditions,
    is_immune,
    tick_conditions,
)
from .initiative import (
    InitiativeEntry,
    InitiativeRoll,
    TurnAdvance,
    advance_turn,
    order_initiative,
    previous_turn,
    roll_initiative,
)
from .weapons import WeaponAttack, weapon_attack

__all__ = [
    "CONCENTRATION",
    "DAMAGE_TYPES",
    "DEATH_SAVES_TO_DIE",
    "DEATH_SAVES_TO_STABILIZE",
    # rule constants
    "DEATH_SAVE_DC",
    "INDEFINITE",
    "ROUNDS",
    "ROUND_END",
    "SAVE_ENDS",
    "TIMED",
    "TURN_END",
    "TURN_START",
    "UNTIL_END_OF_TURN",
    "UNTIL_START_OF_TURN",
    "ActiveCondition",
    # state + result value types
    "CombatantState",
    "ConditionChange",
    "ConditionEffect",
    "DamageApplication",
    "DeathSaveResult",
    "HPChange",
    "InitiativeEntry",
    "InitiativeRoll",
    "SaveResult",
    "TurnAdvance",
    "WeaponAttack",
    "advance_turn",
    # operations (state, input) -> (new_state, explanation)
    "apply_damage",
    "apply_healing",
    "attempt_save",
    "calculate_damage_application",
    "clean_damage_types",
    "combatant_defenses",
    "condition_effects",
    "condition_names",
    "conditions",
    "damage_multiplier",
    "implied_conditions",
    # submodules: initiative ordering + turn advancement; conditions tick/save
    "initiative",
    "is_immune",
    "order_initiative",
    "previous_turn",
    "reset_death_saves",
    "roll_death_save",
    "roll_initiative",
    "set_temp_hp",
    "stabilize",
    "tick_conditions",
    "weapon_attack",
]
