"""Tests for homebrew validators."""
import pytest
from dndwright.rules.homebrew_validator import (
    validate_class_homebrew,
    validate_species_homebrew,
    validate_subclass_homebrew,
    validate_background_homebrew,
    validate_homebrew,
)


class TestValidateClassHomebrew:
    def test_legal_class_returns_empty(self):
        assert validate_class_homebrew({
            "hit_die": 8,
            "saving_throw_proficiencies": ["constitution", "charisma"],
            "archetype": "support_caster",
            "spellcasting_type": "full_caster",
            "spellcasting_ability": "charisma",
        }) == []

    def test_legal_non_spellcaster_class(self):
        assert validate_class_homebrew({
            "hit_die": 12,
            "saving_throw_proficiencies": ["dexterity", "intelligence"],
            "archetype": "full_martial",
            "spellcasting_type": "none",
        }) == []

    def test_legal_with_saving_throws_alias(self):
        assert validate_class_homebrew({
            "hit_die": 10,
            "saving_throws": ["strength", "constitution"],
            "archetype": "full_martial",
        }) == []

    def test_invalid_hit_die(self):
        problems = validate_class_homebrew({"hit_die": 4,
            "saving_throw_proficiencies": ["dexterity", "intelligence"]})
        assert any("hit_die" in p.lower() for p in problems)

    def test_missing_hit_die(self):
        problems = validate_class_homebrew({
            "saving_throw_proficiencies": ["dexterity", "intelligence"]})
        assert any("hit_die" in p.lower() for p in problems)

    def test_wrong_save_count(self):
        problems = validate_class_homebrew({
            "hit_die": 8,
            "saving_throw_proficiencies": ["dexterity"]})
        assert any("exactly 2" in p for p in problems)

    def test_both_saves_same_category(self):
        problems = validate_class_homebrew({
            "hit_die": 8,
            "saving_throw_proficiencies": ["dexterity", "constitution"]})
        assert any("strong" in p or "weak" in p for p in problems)

    def test_invalid_archetype(self):
        problems = validate_class_homebrew({
            "hit_die": 8,
            "saving_throw_proficiencies": ["dexterity", "intelligence"],
            "archetype": "not_a_real_archetype"})
        assert any("archetype" in p.lower() for p in problems)

    def test_spellcaster_missing_ability(self):
        problems = validate_class_homebrew({
            "hit_die": 8,
            "saving_throw_proficiencies": ["dexterity", "intelligence"],
            "spellcasting_type": "full_caster"})
        assert any("spellcasting_ability" in p.lower() for p in problems)

    def test_non_spellcaster_with_ability(self):
        problems = validate_class_homebrew({
            "hit_die": 8,
            "saving_throw_proficiencies": ["dexterity", "intelligence"],
            "spellcasting_type": "none",
            "spellcasting_ability": "intelligence"})
        assert any("non-spellcaster" in p.lower() for p in problems)

    def test_feature_invalid_level(self):
        problems = validate_class_homebrew({
            "hit_die": 8,
            "saving_throw_proficiencies": ["dexterity", "intelligence"],
            "progression": [
                {"name": "Feature A", "level": 25}]})
        assert any("1-20" in p for p in problems)

    def test_feature_duplicate_level(self):
        problems = validate_class_homebrew({
            "hit_die": 8,
            "saving_throw_proficiencies": ["dexterity", "intelligence"],
            "progression": [
                {"name": "Feature A", "level": 3},
                {"name": "Feature B", "level": 3}]})
        assert any("Multiple" in p or "multiple" in p for p in problems)

    def test_bad_spellcasting_type(self):
        problems = validate_class_homebrew({
            "hit_die": 8,
            "saving_throw_proficiencies": ["dexterity", "intelligence"],
            "spellcasting_type": "super_caster"})
        assert any("spellcasting_type" in p.lower() for p in problems)

    def test_invalid_spellcasting_ability(self):
        problems = validate_class_homebrew({
            "hit_die": 8,
            "saving_throw_proficiencies": ["dexterity", "intelligence"],
            "spellcasting_type": "full_caster",
            "spellcasting_ability": "coolness"})
        assert any("spellcasting_ability" in p.lower() for p in problems)

    def test_unknown_ability_in_saves(self):
        problems = validate_class_homebrew({
            "hit_die": 8,
            "saving_throw_proficiencies": ["dexterity", "speed"]})
        assert any("Unknown ability" in p for p in problems)

    def test_valid_archetypes_accepted(self):
        for arch in ["full_martial", "half_caster", "full_caster",
                      "pact_caster", "expert", "priest", "arcane",
                      "warlock", "support_caster", "skill_martial"]:
            assert validate_class_homebrew({
                "hit_die": 8,
                "saving_throw_proficiencies": ["dexterity", "intelligence"],
                "archetype": arch,
            }) == []

    def test_feature_non_dict(self):
        problems = validate_class_homebrew({
            "hit_die": 8,
            "saving_throw_proficiencies": ["dexterity", "intelligence"],
            "progression": ["not_a_dict"]})
        assert any("not a dict" in p.lower() for p in problems)

    def test_feature_non_integer_level(self):
        problems = validate_class_homebrew({
            "hit_die": 8,
            "saving_throw_proficiencies": ["dexterity", "intelligence"],
            "progression": [{"name": "Bad", "level": "three"}]})
        assert any("non-integer" in p.lower() for p in problems)


class TestValidateSpeciesHomebrew:
    def test_legal_species(self):
        assert validate_species_homebrew({
            "size": "Medium",
            "creature_type": "Humanoid",
            "speed": {"walk": 30},
        }) == []

    def test_invalid_size(self):
        problems = validate_species_homebrew({"size": "Colossal"})
        assert any("size" in p.lower() for p in problems)

    def test_invalid_creature_type(self):
        problems = validate_species_homebrew({"creature_type": "Cat"})
        assert any("creature_type" in p.lower() for p in problems)

    def test_fast_fly_speed(self):
        problems = validate_species_homebrew({"speed": {"fly": 80}})
        assert any("fly" in p.lower() for p in problems)

    def test_fast_burrow_speed(self):
        problems = validate_species_homebrew({"speed": {"burrow": 50}})
        assert any("burrow" in p.lower() for p in problems)

    def test_high_innate_spell_level(self):
        problems = validate_species_homebrew({
            "innate_spellcasting": {
                "spells": [{"name": "Fireball", "level": 6}]}})
        assert any("innate" in p.lower() or "6" in p for p in problems)

    def test_bad_trait_type(self):
        problems = validate_species_homebrew({"traits": ["not_a_dict"]})
        assert any("not a dict" in p.lower() or "Species trait" in p for p in problems)

    def test_empty_species_returns_empty(self):
        assert validate_species_homebrew({}) == []


class TestValidateSubclassHomebrew:
    def test_legal_subclass(self):
        assert validate_subclass_homebrew({
            "subclass_archetype": "damage_dealer",
            "features": [
                {"name": "F3", "level": 3},
                {"name": "F6", "level": 6},
                {"name": "F10", "level": 10},
                {"name": "F14", "level": 14},
            ]}) == []

    def test_few_features_warns(self):
        problems = validate_subclass_homebrew({
            "features": [{"name": "Only One", "level": 3}]})
        assert any("only 1" in p.lower() for p in problems)

    def test_feature_invalid_level(self):
        problems = validate_subclass_homebrew({
            "features": [
                {"name": "A", "level": 3},
                {"name": "B", "level": 25},
                {"name": "C", "level": 6}]})
        assert any("1-20" in p for p in problems)

    def test_duplicate_feature_level(self):
        problems = validate_subclass_homebrew({
            "features": [
                {"name": "A", "level": 3},
                {"name": "B", "level": 3}]})
        assert any("Multiple" in p or "multiple" in p for p in problems)

    def test_invalid_domain_spell_level(self):
        problems = validate_subclass_homebrew({
            "features": [
                {"name": "A", "level": 3},
                {"name": "B", "level": 6}],
            "domain_spells": [{"spell_level": 10}]})
        assert any("invalid level" in p.lower() or "10" in p for p in problems)

    def test_bad_feature_type(self):
        problems = validate_subclass_homebrew({
            "features": ["not_a_dict"]})
        assert any("not a dict" in p.lower() or "Subclass feature" in p for p in problems)

    def test_empty_subclass_warns(self):
        problems = validate_subclass_homebrew({})
        assert any("only 0" in p.lower() or "feature" in p.lower() for p in problems)


class TestValidateBackgroundHomebrew:
    def test_legal_background(self):
        assert validate_background_homebrew({
            "skill_proficiencies": ["Perception", "Survival"],
            "origin_feat": "Alert",
            "ability_score_increases": {"dexterity": 2, "wisdom": 1},
        }) == []

    def test_wrong_skill_count(self):
        problems = validate_background_homebrew({
            "skill_proficiencies": ["Athletics"],
            "origin_feat": "Alert"})
        assert any("exactly 2" in p for p in problems)

    def test_missing_origin_feat(self):
        problems = validate_background_homebrew({
            "skill_proficiencies": ["Athletics", "Acrobatics"]})
        assert any("origin_feat" in p.lower() for p in problems)

    def test_ability_score_total_too_high(self):
        problems = validate_background_homebrew({
            "skill_proficiencies": ["Athletics", "Acrobatics"],
            "origin_feat": "Alert",
            "ability_score_increases": {
                "strength": 2, "dexterity": 1, "constitution": 1}})
        assert any("total" in p.lower() for p in problems)

    def test_unknown_ability_in_increases(self):
        problems = validate_background_homebrew({
            "skill_proficiencies": ["Athletics", "Acrobatics"],
            "origin_feat": "Alert",
            "ability_score_increases": {"charisma": 2, "luck": 1}})
        assert any("luck" in p or "Unknown" in p for p in problems)

    def test_legal_background_no_increases(self):
        assert validate_background_homebrew({
            "skill_proficiencies": ["Athletics", "Acrobatics"],
            "origin_feat": "Alert"}) == []

    def test_empty_background_returns_problems(self):
        problems = validate_background_homebrew({})
        # Missing origin_feat and skills should both be flagged
        assert len(problems) >= 1


class TestValidateHomebrewRouter:
    def test_valid_class_routes_correctly(self):
        assert validate_homebrew("class", {
            "hit_die": 8,
            "saving_throw_proficiencies": ["constitution", "intelligence"]}) == []

    def test_unknown_type_returns_problem(self):
        problems = validate_homebrew("unknown_type", {})
        assert len(problems) == 1
        assert "Unknown" in problems[0]

    def test_router_passes_bad_data_to_validator(self):
        problems = validate_homebrew("background", {})
        assert len(problems) >= 1
