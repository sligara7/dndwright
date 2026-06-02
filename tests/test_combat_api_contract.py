"""API contract for the dndwright.combat subpackage — pins its public surface."""

import dndwright.combat as combat

EXPECTED_COMBAT_PUBLIC = {
    "CombatantState",
    "DamageApplication",
    "HPChange",
    "DeathSaveResult",
    "apply_damage",
    "apply_healing",
    "set_temp_hp",
    "roll_death_save",
    "stabilize",
    "reset_death_saves",
    "calculate_damage_application",
    "DEATH_SAVE_DC",
    "DEATH_SAVES_TO_STABILIZE",
    "DEATH_SAVES_TO_DIE",
}


def test_combat_all_matches_contract():
    assert set(combat.__all__) == EXPECTED_COMBAT_PUBLIC


def test_everything_in_combat_all_is_importable():
    for name in combat.__all__:
        assert hasattr(combat, name), f"{name} missing from dndwright.combat"
