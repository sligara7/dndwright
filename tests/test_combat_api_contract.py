"""API contract for the dndwright.combat subpackage — pins its public surface."""

import dndwright.combat as combat

EXPECTED_COMBAT_PUBLIC = {
    "ActiveCondition",
    "CONCENTRATION",
    "CombatantState",
    "ConditionChange",
    "ConditionEffect",
    "DAMAGE_TYPES",
    "DEATH_SAVES_TO_DIE",
    "DEATH_SAVES_TO_STABILIZE",
    "DEATH_SAVE_DC",
    "DamageApplication",
    "DeathSaveResult",
    "HPChange",
    "INDEFINITE",
    "InitiativeEntry",
    "InitiativeRoll",
    "ROUNDS",
    "ROUND_END",
    "SAVE_ENDS",
    "SaveResult",
    "TIMED",
    "TURN_END",
    "TURN_START",
    "TurnAdvance",
    "UNTIL_END_OF_TURN",
    "UNTIL_START_OF_TURN",
    "WeaponAttack",
    "advance_turn",
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
}

EXPECTED_INITIATIVE_PUBLIC = {
    "InitiativeEntry",
    "InitiativeRoll",
    "TurnAdvance",
    "roll_initiative",
    "order_initiative",
    "advance_turn",
    "previous_turn",
}


def test_combat_all_matches_contract():
    assert set(combat.__all__) == EXPECTED_COMBAT_PUBLIC


def test_everything_in_combat_all_is_importable():
    for name in combat.__all__:
        assert hasattr(combat, name), f"{name} missing from dndwright.combat"


def test_initiative_all_matches_contract():
    assert set(combat.initiative.__all__) == EXPECTED_INITIATIVE_PUBLIC


def test_everything_in_initiative_all_is_importable():
    for name in combat.initiative.__all__:
        assert hasattr(combat.initiative, name), f"{name} missing from combat.initiative"


EXPECTED_CONDITIONS_PUBLIC = {
    "ConditionEffect", "ActiveCondition", "ConditionChange", "SaveResult",
    "condition_effects", "condition_names", "implied_conditions", "is_immune",
    "tick_conditions", "attempt_save",
    "ROUNDS", "UNTIL_END_OF_TURN", "UNTIL_START_OF_TURN", "CONCENTRATION",
    "INDEFINITE", "SAVE_ENDS", "TIMED", "ROUND_END", "TURN_END", "TURN_START",
}


def test_conditions_all_matches_contract():
    assert set(combat.conditions.__all__) == EXPECTED_CONDITIONS_PUBLIC


def test_everything_in_conditions_all_is_importable():
    for name in combat.conditions.__all__:
        assert hasattr(combat.conditions, name), f"{name} missing from combat.conditions"
