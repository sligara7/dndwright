"""Character-input validation — strict mode catches malformed data; lenient stays lenient."""

import pytest

from dndwright import (
    CharacterInputError,
    evaluate_character,
    validate_character_data,
)

GOOD = {
    "ability_scores": {"strength": 8, "dexterity": 14, "constitution": 14,
                       "intelligence": 18, "wisdom": 12, "charisma": 10},
    "class_data": {"class_name": "wizard"},
    "species_data": {"name": "Human", "speed": 30},
    "level": 5,
}


class TestValidateCharacterData:
    def test_good_data_has_no_problems(self):
        assert validate_character_data(GOOD) == []

    def test_missing_ability_scores(self):
        data = {**GOOD, "ability_scores": {}}
        assert any("missing or empty" in p for p in validate_character_data(data))

    def test_missing_one_ability(self):
        scores = dict(GOOD["ability_scores"])
        del scores["charisma"]
        problems = validate_character_data({**GOOD, "ability_scores": scores})
        assert any("charisma" in p for p in problems)

    def test_non_numeric_score(self):
        scores = {**GOOD["ability_scores"], "strength": "strong"}
        assert any("strength" in p and "number" in p
                   for p in validate_character_data({**GOOD, "ability_scores": scores}))

    def test_out_of_range_score(self):
        scores = {**GOOD["ability_scores"], "strength": 99}
        assert any("range" in p for p in validate_character_data({**GOOD, "ability_scores": scores}))

    def test_bad_level(self):
        assert any("level" in p for p in validate_character_data({**GOOD, "level": 0}))
        assert any("level" in p for p in validate_character_data({**GOOD, "level": "five"}))

    def test_missing_class(self):
        assert any("class_name" in p for p in validate_character_data({**GOOD, "class_data": {}}))

    def test_bool_is_not_a_valid_score(self):
        # bool is an int subclass — must be rejected as a score.
        scores = {**GOOD["ability_scores"], "wisdom": True}
        assert any("wisdom" in p for p in validate_character_data({**GOOD, "ability_scores": scores}))

    def test_fractional_float_score_rejected(self):
        scores = {**GOOD["ability_scores"], "strength": 15.7}
        problems = validate_character_data({**GOOD, "ability_scores": scores})
        assert any("strength" in p and "whole number" in p for p in problems)

    def test_integral_float_score_accepted(self):
        # 15.0 is integer-valued and fine for the engine.
        scores = {**GOOD["ability_scores"], "strength": 15.0}
        assert validate_character_data({**GOOD, "ability_scores": scores}) == []

    def test_missing_level_is_reported(self):
        # _extract_session_fields defaults level to 1, so an omitted level must be
        # detected from the raw input, not silently treated as level 1.
        data = {k: v for k, v in GOOD.items() if k != "level"}
        assert any(p == "level is missing" for p in validate_character_data(data))

    def test_missing_level_inside_data_wrapper(self):
        wrapped = {"data": {k: v for k, v in GOOD.items() if k != "level"}}
        assert any(p == "level is missing" for p in validate_character_data(wrapped))

    def test_non_dict_input(self):
        assert validate_character_data([1, 2, 3]) == [
            "character data must be a JSON object, got list"
        ]


class TestStrictMode:
    def test_strict_raises_on_bad_input(self):
        with pytest.raises(CharacterInputError) as exc:
            evaluate_character({"level": 0}, strict=True)
        assert exc.value.problems  # carries the structured list

    def test_strict_passes_good_input(self):
        sheet = evaluate_character(GOOD, strict=True)
        assert sheet["proficiency_bonus"] == 3

    def test_default_is_strict_since_0_29_0(self):
        # THE DEFAULT FLIPPED in 0.29.0. Malformed input now raises rather than
        # being coerced into a plausible-but-wrong sheet, because a coerced sheet
        # has every expected key and plausible numbers and is therefore
        # indistinguishable from a correct one at every downstream surface.
        # This test replaces test_lenient_default_still_coerces, which asserted
        # the opposite and was correct until the default changed.
        with pytest.raises(CharacterInputError):
            evaluate_character({"ability_scores": {}, "level": 1})

    def test_lenient_is_still_available_on_request(self):
        # The old behaviour is not gone, only opt-in: strict=False restores it
        # exactly, so a caller who genuinely wants coercion says so.
        sheet = evaluate_character({"ability_scores": {}, "level": 1}, strict=False)
        assert sheet["ability_modifiers"]["strength"] == 0  # defaulted to 10 → mod 0

    def test_the_coerced_sheet_is_indistinguishable_from_a_good_one(self):
        # The reason the default changed, made executable: a lenient sheet from
        # empty input carries the SAME KEYS as a sheet from complete input, so no
        # downstream consumer can tell them apart by shape — only by having been
        # told. That is why there was no error to swallow.
        coerced = evaluate_character({"ability_scores": {}, "level": 1}, strict=False)
        good = evaluate_character(GOOD, strict=False)
        assert set(coerced) == set(good)
        assert all(isinstance(coerced[k], type(good[k])) for k in ("proficiency_bonus",))
