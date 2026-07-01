"""Tests for homebrew validators."""
from dndwright.rules.homebrew_validator import (
    validate_class_homebrew,
    validate_species_homebrew,
    validate_subclass_homebrew,
    validate_background_homebrew,
    validate_homebrew,
    validate_power_budget,
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

    # --- Canonical / generated shape (regression pins) ---------------------
    # The validator must accept the shape that ``CharClass`` actually uses and
    # that the LLM-normalized homebrew output produces: a dice-STRING hit_die
    # ("d10", since ``CharClass.hit_die`` is typed ``str``) and CAPITALIZED
    # ability names ("Strength"). It previously demanded an int + lowercase and
    # so false-positive-rejected every valid generated class.

    def test_legal_dice_string_hit_die(self):
        assert validate_class_homebrew({
            "hit_die": "d10",
            "saving_throws": ["strength", "constitution"],
            "archetype": "full_martial",
        }) == []

    def test_legal_capitalized_saving_throws(self):
        assert validate_class_homebrew({
            "hit_die": 8,
            "saving_throws": ["Strength", "Constitution"],
            "archetype": "full_martial",
        }) == []

    def test_legal_full_generated_class_shape(self):
        """The exact gen_plus normalize_class output must validate clean."""
        assert validate_class_homebrew({
            "name": "Ironguard",
            "hit_die": "d10",
            "saving_throws": ["Strength", "Constitution"],
            "archetype": "full_martial",
            "spellcasting_type": "none",
            "progression_table": [{"level": i, "features": ["x"]} for i in range(1, 21)],
        }) == []

    def test_dice_string_invalid_die_still_caught(self):
        problems = validate_class_homebrew({
            "hit_die": "d7",
            "saving_throws": ["Strength", "Constitution"]})
        assert any("hit_die" in p.lower() for p in problems)

    def test_capitalized_two_strong_saves_still_caught(self):
        problems = validate_class_homebrew({
            "hit_die": "d8",
            "saving_throws": ["Dexterity", "Constitution"]})
        assert any("strong" in p or "weak" in p for p in problems)

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

    def test_router_handles_power_budget_kwargs(self):
        problems = validate_homebrew("power_budget", {
            "species_data": {"traits": []},
            "class_data": {"features": []},
            "level": 1,
        })
        assert problems == []


# ---------------------------------------------------------------------------
# Power-budget validator tests
# ---------------------------------------------------------------------------


class TestValidatePowerBudget:
    """validate_power_budget(species_data, class_data, subclass_data, level)."""

    # --- OK cases ------------------------------------------------------------

    def test_balanced_low_level_character_passes(self):
        species = {
            "traits": [
                {"name": "Darkvision", "description": "You have Darkvision 60 ft."},
                {"name": "Lucky", "description": "You can reroll 1s."},
                {"name": "Brave", "description": "Advantage against Frightened."},
            ]
        }
        class_ = {
            "features": [
                {"name": "Fighting Style", "level": 1},
                {"name": "Second Wind", "level": 1},
            ]
        }
        subclass = {
            "features": [
                {"name": "Sub Feature A", "level": 3},
                {"name": "Sub Feature B", "level": 6},
            ]
        }
        assert validate_power_budget(species, class_, subclass, level=1) == []

    def test_balanced_level_5_character_passes(self):
        species = {
            "traits": [
                {"name": "Giant Ancestry", "description": "Supernatural boon."},
                {"name": "Large Form", "description": "Become Large at level 5."},
                {"name": "Powerful Build", "description": "Carry more weight."},
            ]
        }
        class_ = {
            "features": [
                {"name": "Rage", "level": 1},
                {"name": "Unarmored Defense", "level": 1},
                {"name": "Reckless Attack", "level": 2},
                {"name": "Subclass", "level": 3},
                {"name": "ASI", "level": 4},
                {"name": "Extra Attack", "level": 5},
                {"name": "Fast Movement", "level": 5},
            ]
        }
        subclass = {
            "features": [
                {"name": "Frenzy", "level": 3},
                {"name": "Mindless Rage", "level": 6},
                {"name": "Retaliation", "level": 10},
                {"name": "Intimidating Presence", "level": 14},
            ]
        }
        assert validate_power_budget(species, class_, subclass, level=5) == []

    def test_no_subclass_passes(self):
        species = {"traits": [{"name": "Resourceful"}, {"name": "Skillful"}, {"name": "Versatile"}]}
        class_ = {"features": [{"name": "Fighting Style", "level": 1}, {"name": "Action Surge", "level": 2}]}
        assert validate_power_budget(species, class_, level=1) == []

    def test_level_20_balanced_character_passes(self):
        species = {"traits": [{"name": "Darkvision"}, {"name": "Fey Ancestry"}]}
        # ~15 features is within the level-20 budget of 26
        class_ = {
            "features": [{"name": f"F{i}", "level": i} for i in range(1, 17)]
        }
        subclass = {
            "features": [{"name": f"SF{i}", "level": i} for i in [3, 6, 10, 14, 17]]
        }
        assert validate_power_budget(species, class_, subclass, level=20) == []

    # --- Species trait budget failures ---------------------------------------

    def test_too_many_species_traits_fails(self):
        species = {
            "traits": [
                {"name": f"Trait {i}"} for i in range(7)  # 7 > 5 max
            ]
        }
        class_ = {"features": [{"name": "Attack", "level": 1}]}
        problems = validate_power_budget(species, class_, level=1)
        assert any("Species has 7 traits" in p for p in problems)
        assert any("over budget" in p for p in problems)

    def test_too_many_high_impact_traits_fails(self):
        species = {
            "traits": [
                {"name": "Flight", "description": "You have a fly speed of 30 ft."},
                {"name": "Damage Resistance", "description": "Resistance to fire damage."},
                {"name": "Breath Weapon", "description": "15 ft cone of fire damage."},
                {"name": "Magic Resistance", "description": "Advantage on saves vs spells."},
            ]  # 4 high-impact > 3 max
        }
        class_ = {"features": [{"name": "Fighting Style", "level": 1}]}
        problems = validate_power_budget(species, class_, level=1)
        assert any("high-impact" in p.lower() for p in problems)

    def test_innate_spellcasting_high_level_fails(self):
        species = {
            "traits": [
                {"name": "Arcane Heritage", "description": "Innate spellcasting."},
            ],
            "innate_spellcasting": {
                "spells": [
                    {"name": "Fireball", "level": 3},
                    {"name": "Disintegrate", "level": 6},
                ]
            },
        }
        class_ = {"features": [{"name": "Attack", "level": 1}]}
        problems = validate_power_budget(species, class_, level=1)
        assert any("level-6" in p or "4" in p for p in problems)

    # --- Class feature budget failures ---------------------------------------

    def test_too_many_features_at_level_1_fails(self):
        species = {"traits": []}
        class_ = {
            "features": [
                {"name": f"Feature {i}", "level": 1} for i in range(6)  # 6 > 4 max at L1
            ]
        }
        problems = validate_power_budget(species, class_, level=1)
        assert any("Class+subclass has 6 features" in p for p in problems)
        assert any("over budget" in p for p in problems)

    def test_too_many_features_at_level_3_fails(self):
        species = {"traits": []}
        class_ = {
            "features": [{"name": f"F{i}", "level": 1} for i in range(3)] + [
                {"name": f"F3_{i}", "level": 3} for i in range(5)
            ]
        }
        subclass = {
            "features": [{"name": f"SF{i}", "level": 3} for i in range(4)]
        }
        # At L3: 3 base (L1) + 5 base (L3) + 4 subclass (L3) = 12 > 9 max
        problems = validate_power_budget(species, class_, subclass, level=3)
        assert any("Class+subclass has 12 features" in p for p in problems)

    # --- Combined budget (Superman + Batman) ---------------------------------

    def test_superman_batman_stack_fails(self):
        """At level 1: 5 species + 5 class = 10, exceeds class budget (4) + combined."""
        species = {
            "traits": [
                {"name": "Flight", "description": "Fly speed 60 ft."},
                {"name": "Heat Vision", "description": "Ranged damage."},
                {"name": "Super Strength", "description": "Advantage on Strength."},
                {"name": "Invulnerability", "description": "Damage resistance to all."},
                {"name": "Super Speed", "description": "Dash as bonus action."},
            ]
        }
        class_ = {
            "features": [
                {"name": "Martial Arts", "level": 1},
                {"name": "Detective Training", "level": 1},
                {"name": "Gadget Belt", "level": 1},
                {"name": "Combat Expertise", "level": 1},
                {"name": "Shadow Strike", "level": 1},
            ]
        }
        subclass = {
            "features": [
                {"name": "Stealth Mastery", "level": 1},
            ]
        }
        problems = validate_power_budget(species, class_, subclass, level=1)
        # Should fail class-feature budget: 6 > 4 at L1
        assert any("Class+subclass has 6 features" in p for p in problems)
        # Should also fail combined: 5 species + 6 class = 11 > 9 at L1
        assert any("Combined power budget exceeded" in p for p in problems)

    def test_just_under_combined_budget_passes(self):
        # At level 1: budget = 5 + 4 = 9 (no extra margin for combined).
        # 4 species + 4 class = 8 < 9 passes.
        species = {"traits": [{"name": f"T{i}"} for i in range(4)]}
        class_ = {"features": [{"name": f"F{i}", "level": 1} for i in range(4)]}
        assert validate_power_budget(species, class_, level=1) == []

    def test_just_over_combined_budget_fails(self):
        # At level 1: budget = 5 + 4 = 9.  6 species + 4 class = 10 > 9 fails.
        species = {"traits": [{"name": f"T{i}"} for i in range(6)]}
        class_ = {"features": [{"name": f"F{i}", "level": 1} for i in range(4)]}
        problems = validate_power_budget(species, class_, level=1)
        assert any("Combined power budget exceeded" in p for p in problems)

    # --- Edge cases ---------------------------------------------------------

    def test_empty_data_passes(self):
        assert validate_power_budget({}, {}, level=1) == []

    def test_missing_traits_passes(self):
        species = {}
        class_ = {"features": [{"name": "Attack", "level": 1}]}
        assert validate_power_budget(species, class_, level=1) == []

    def test_string_traits_list_handled(self):
        """Malformed traits list (strings) should not crash."""
        species = {"traits": ["not_a_dict"]}
        class_ = {"features": [{"name": "Attack", "level": 1}]}
        problems = validate_power_budget(species, class_, level=1)
        assert problems == []

    def test_features_below_level_ignored(self):
        species = {"traits": []}
        class_ = {
            "features": [
                {"name": "F1", "level": 1},
                {"name": "F5", "level": 5},
                {"name": "F10", "level": 10},
            ]
        }
        assert validate_power_budget(species, class_, level=2) == []
