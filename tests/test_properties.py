"""Property-based tests — published-rule invariants over wide input ranges.

These complement the fixed-fixture tests in ``test_engine.py`` by checking the math
holds for *any* valid ability score / level, not just hand-picked characters.
"""

from hypothesis import given
from hypothesis import strategies as st

from dndwright import evaluate_character

ABILITIES = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
SCORES = st.integers(min_value=1, max_value=30)
LEVELS = st.integers(min_value=1, max_value=20)


def _char(scores: dict, level: int) -> dict:
    return {
        "ability_scores": scores,
        "class_data": {"class_name": "fighter"},
        "species_data": {"name": "Human", "speed": 30},
        "level": level,
    }


@given(scores=st.fixed_dictionaries({a: SCORES for a in ABILITIES}), level=LEVELS)
def test_ability_modifier_formula_holds_everywhere(scores, level):
    sheet = evaluate_character(_char(scores, level))
    for ability, score in scores.items():
        assert sheet["ability_modifiers"][ability] == (score - 10) // 2


@given(level=LEVELS)
def test_proficiency_bonus_formula(level):
    sheet = evaluate_character(_char({a: 10 for a in ABILITIES}, level))
    assert sheet["proficiency_bonus"] == 2 + (level - 1) // 4


@given(level=st.integers(min_value=1, max_value=19),
       con=SCORES)
def test_hp_is_monotonic_in_level(level, con):
    scores = {a: 10 for a in ABILITIES} | {"constitution": con}
    lower = evaluate_character(_char(scores, level))["hit_points"]
    higher = evaluate_character(_char(scores, level + 1))["hit_points"]
    assert higher >= lower  # gaining a level never reduces max HP


@given(scores=st.fixed_dictionaries({a: SCORES for a in ABILITIES}), level=LEVELS)
def test_proficiency_bonus_in_published_range(scores, level):
    pb = evaluate_character(_char(scores, level))["proficiency_bonus"]
    assert 2 <= pb <= 6  # PB spans +2 (lvl 1) to +6 (lvl 17-20)
