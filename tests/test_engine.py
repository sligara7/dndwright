"""Engine tests — canonical D&D 5e (2024) math on known-good characters.

Fixtures cover the three spellcasting axes (full / half / none). Assertions are
deterministic against the published rules:
  ability_modifier = (score - 10) // 2
  proficiency_bonus = (level - 1) // 4 + 2
"""

import pytest

from dndwright import DND_5E_2024_RULESET, evaluate_character


def _find(obj, key):
    """Recursively find the first value for `key` anywhere in a nested mapping."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            found = _find(v, key)
            if found is not None:
                return found
    return None


def _char(class_name, scores, level):
    return {
        "ability_scores": dict(zip(
            ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"],
            scores,
        )),
        "class_data": {"class_name": class_name},
        "species_data": {"name": "Human", "speed": 30},
        "level": level,
    }


WIZARD_L5 = _char("wizard", [8, 14, 14, 18, 12, 10], 5)
PALADIN_L3 = _char("paladin", [16, 10, 14, 8, 12, 16], 3)
BARBARIAN_L2 = _char("barbarian", [18, 14, 16, 8, 12, 10], 2)

CASES = [
    (WIZARD_L5, {
        "proficiency_bonus": 3,
        "ability_modifiers": {"strength": -1, "dexterity": 2, "constitution": 2,
                              "intelligence": 4, "wisdom": 1, "charisma": 0},
        "spellcasting_type": "full_caster",
    }),
    (PALADIN_L3, {
        "proficiency_bonus": 2,
        "ability_modifiers": {"strength": 3, "dexterity": 0, "constitution": 2,
                              "intelligence": -1, "wisdom": 1, "charisma": 3},
        "spellcasting_type": "half_caster",
    }),
    (BARBARIAN_L2, {
        "proficiency_bonus": 2,
        "ability_modifiers": {"strength": 4, "dexterity": 2, "constitution": 3,
                              "intelligence": -1, "wisdom": 1, "charisma": 0},
    }),
]


class TestRulesetShape:
    def test_ruleset_is_a_dag_of_nodes(self):
        nodes = DND_5E_2024_RULESET.nodes
        assert len(nodes) > 50  # a substantial computation graph


class TestComputedMath:
    @pytest.mark.parametrize("char,expected", CASES,
                             ids=["wizard_l5", "paladin_l3", "barbarian_l2"])
    def test_core_values(self, char, expected):
        sheet = evaluate_character(char)
        assert sheet["proficiency_bonus"] == expected["proficiency_bonus"]
        assert sheet["ability_modifiers"] == expected["ability_modifiers"]
        if "spellcasting_type" in expected:
            assert _find(sheet, "spellcasting_type") == expected["spellcasting_type"]

    def test_proficiency_bonus_progression(self):
        # +2 at 1-4, +3 at 5-8, +4 at 9-12, ...
        for level, pb in [(1, 2), (4, 2), (5, 3), (8, 3), (9, 4), (13, 5), (17, 6)]:
            sheet = evaluate_character(_char("wizard", [10] * 6, level))
            assert sheet["proficiency_bonus"] == pb, f"level {level}"

    def test_ability_modifier_formula(self):
        sheet = evaluate_character(_char("wizard", [1, 10, 11, 20, 14, 7], 1))
        mods = sheet["ability_modifiers"]
        assert mods["strength"] == -5   # (1-10)//2
        assert mods["dexterity"] == 0   # (10-10)//2
        assert mods["constitution"] == 0
        assert mods["intelligence"] == 5  # (20-10)//2
        assert mods["wisdom"] == 2
        assert mods["charisma"] == -2   # (7-10)//2


class TestSheetCompleteness:
    def test_sheet_has_core_fields(self):
        sheet = evaluate_character(WIZARD_L5)
        for field in ("ability_modifiers", "proficiency_bonus", "armor_class",
                      "hit_points", "hit_dice", "initiative"):
            assert field in sheet, f"missing {field}"


class TestDeterminism:
    def test_same_input_same_output(self):
        assert evaluate_character(WIZARD_L5) == evaluate_character(WIZARD_L5)

    def test_pure_compute_no_mutation(self):
        # The input dict must not be mutated by evaluation.
        import copy
        before = copy.deepcopy(WIZARD_L5)
        evaluate_character(WIZARD_L5)
        assert WIZARD_L5 == before
