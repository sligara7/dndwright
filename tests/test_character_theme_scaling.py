"""evaluate_character / compute_* honour an optional ThemeScalingLayer.

A scaling layer re-themes the ruleset the sheet is computed against (re-baselined
input defaults + merged lookup tables) so mechanical values fit the campaign's
setting. ``scaling=None`` (the default) reproduces the stock 5e behaviour exactly.
"""

from dndwright import (
    ThemeScalingLayer,
    compute_key_stats,
    compute_stat_diff,
    evaluate_character,
    get_theme_scaling,
)


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


FIGHTER_L5 = _char("fighter", [16, 14, 15, 10, 12, 8], 5)


def _find(obj, key):
    """First value for `key` anywhere in a nested mapping (sheet shape-agnostic)."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            found = _find(v, key)
            if found is not None:
                return found
    return None


# A layer that lifts the *unarmored* base AC (armor_base_ac["none"], default 10) by 5.
# Overrides "unarmored" too so the test holds whichever key the armor op resolves.
_UNARMORED_PLUS_5 = ThemeScalingLayer(
    theme="test", lookup_overrides={"armor_base_ac": {"none": 15, "unarmored": 15}}
)


class TestEvaluateCharacterScaling:
    def test_none_reproduces_default(self):
        assert evaluate_character(FIGHTER_L5, scaling=None) == evaluate_character(FIGHTER_L5)

    def test_lookup_override_changes_the_sheet(self):
        base_ac = _find(evaluate_character(FIGHTER_L5), "armor_class")
        themed_ac = _find(evaluate_character(FIGHTER_L5, scaling=_UNARMORED_PLUS_5), "armor_class")
        assert themed_ac == base_ac + 5

    def test_predefined_theme_composes_and_evaluates(self):
        sheet = evaluate_character(FIGHTER_L5, scaling=get_theme_scaling("sci_fi"))
        assert _find(sheet, "armor_class") is not None

    def test_themed_call_does_not_leak_into_base_ruleset(self):
        # A themed evaluation must not mutate the shared base ruleset (purity).
        big = ThemeScalingLayer(theme="t", lookup_overrides={"armor_base_ac": {"none": 99}})
        before = _find(evaluate_character(FIGHTER_L5), "armor_class")
        evaluate_character(FIGHTER_L5, scaling=big)
        assert _find(evaluate_character(FIGHTER_L5), "armor_class") == before


class TestComputeHelpersScaling:
    def test_compute_key_stats_accepts_scaling(self):
        base = compute_key_stats(FIGHTER_L5)["armor_class"]["value"]
        themed = compute_key_stats(FIGHTER_L5, scaling=_UNARMORED_PLUS_5)["armor_class"]["value"]
        assert themed == base + 5

    def test_compute_stat_diff_accepts_scaling(self):
        # L4→L5 raises proficiency 2→3; the diff still works under a theme layer.
        before = _char("fighter", [16, 14, 15, 10, 12, 8], 4)
        diff = compute_stat_diff(before, FIGHTER_L5, scaling=get_theme_scaling("modern_warfare"))
        assert diff["proficiency_bonus"]["before"] == 2
        assert diff["proficiency_bonus"]["after"] == 3
