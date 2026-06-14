"""Tests for adapters bug fixes (hit-die display + natural armor AC)."""
from dndwright import character_data_to_inputs, computed_values_to_sheet


class TestHitDieDisplayFix:
    """Bug 1: hit-die display must match computation after archetype overrides."""

    def test_hit_die_uses_archetype_override_in_display(self):
        """Sheet hit_die_type must show d12 when archetype=primal_martial overrides d10."""
        class_data = {
            "class_name": "barbarian",
            "hit_die": "d10",
            "archetype": "primal_martial",
        }
        species_data = {"speed": 30}
        ability_scores = {
            "strength": 10, "dexterity": 10, "constitution": 10,
            "intelligence": 10, "wisdom": 10, "charisma": 10,
        }
        inputs = character_data_to_inputs(
            ability_scores, class_data, None, species_data, None, 3,
        )
        # Computation uses d12
        assert inputs["class_hit_dice"].get("barbarian") == 12

        # Display must also reflect d12
        sheet = computed_values_to_sheet(
            {}, ability_scores, class_data, None, species_data, None, 3,
        )
        assert sheet["hit_die_type"] == "d12"

    def test_hit_die_uses_class_lookup_in_display(self):
        """Sheet hit_die_type must match class lookup for known SRD class."""
        class_data = {
            "class_name": "wizard",
            # No hit_die field at all — should fall back to d6 from lookup
        }
        species_data = {"speed": 30}
        ability_scores = {
            "strength": 10, "dexterity": 10, "constitution": 10,
            "intelligence": 10, "wisdom": 10, "charisma": 10,
        }
        inputs = character_data_to_inputs(
            ability_scores, class_data, None, species_data, None, 1,
        )
        assert inputs["class_hit_dice"].get("wizard") == 6

        sheet = computed_values_to_sheet(
            {}, ability_scores, class_data, None, species_data, None, 1,
        )
        assert sheet["hit_die_type"] == "d6"

    def test_hit_die_no_override_uses_llm_value(self):
        """When no lookup matches, display the LLM's raw hit_die value."""
        class_data = {
            "class_name": "custom_homebrew_class",
            "hit_die": "d10",
        }
        species_data = {"speed": 30}
        ability_scores = {
            "strength": 10, "dexterity": 10, "constitution": 10,
            "intelligence": 10, "wisdom": 10, "charisma": 10,
        }
        sheet = computed_values_to_sheet(
            {}, ability_scores, class_data, None, species_data, None, 1,
        )
        assert sheet["hit_die_type"] == "d10"

    def test_hit_die_compute_and_display_match(self):
        """Primary regression test: computation and display must agree."""
        class_data = {
            "class_name": "fighter",
            "hit_die": "d6",  # LLM claims d6, but fighter lookup says d10
        }
        species_data = {"speed": 30}
        ability_scores = {
            "strength": 10, "dexterity": 10, "constitution": 10,
            "intelligence": 10, "wisdom": 10, "charisma": 10,
        }
        inputs = character_data_to_inputs(
            ability_scores, class_data, None, species_data, None, 1,
        )
        # Computation uses d10 (fighter lookup overrides d6)
        assert inputs["class_hit_dice"].get("fighter") == 10

        sheet = computed_values_to_sheet(
            {}, ability_scores, class_data, None, species_data, None, 1,
        )
        # Display must also show d10, not d6
        assert sheet["hit_die_type"] == "d10"


class TestNaturalArmorACFix:
    """Bug 2: species natural armor must contribute to AC computation."""

    @staticmethod
    def _sheet_for_species(species_data):
        ability_scores = {
            "strength": 10, "dexterity": 14, "constitution": 10,
            "intelligence": 10, "wisdom": 10, "charisma": 10,
        }
        class_data = {"class_name": "wizard", "hit_die": "d6"}
        inputs = character_data_to_inputs(
            ability_scores, class_data, None, species_data, None, 1,
        )
        return inputs

    def test_carapace_trait_adds_natural_armor_input(self):
        """Species with 'Carapace' trait → natural_armor_ac set in inputs."""
        species = {
            "speed": 30,
            "traits": [
                {
                    "name": "Carapace",
                    "description": "Your chitinous shell gives you natural armor. Your base AC is 12.",
                }
            ],
        }
        inputs = self._sheet_for_species(species)
        assert inputs["natural_armor_ac"] == 12

    def test_no_natural_armor_trait_sets_zero(self):
        """Species without natural armor → natural_armor_ac = 0."""
        species = {
            "speed": 30,
            "traits": [
                {"name": "Darkvision", "description": "You can see in the dark 60 ft."},
            ],
        }
        inputs = self._sheet_for_species(species)
        assert inputs["natural_armor_ac"] == 0

    def test_explicit_natural_armor_ac_field(self):
        """Explicit natural_armor_ac field on species data is used."""
        species = {
            "speed": 30,
            "natural_armor_ac": 15,
        }
        inputs = self._sheet_for_species(species)
        assert inputs["natural_armor_ac"] == 15

    def test_natural_armor_contributes_to_computed_ac(self):
        """Compute full sheet — AC reflects natural armor + DEX when no equipment.

        Unarmored AC = 10 + DEX(2) = 12.  Natural armor AC = 13.
        max(10 + 2, 13) = 13.
        """
        from dndwright import DND_5E_2024_RULESET, evaluate

        species = {
            "speed": 30,
            "traits": [
                {
                    "name": "Tough Hide",
                    "description": "Your thick, armored hide gives you natural armor. Your AC is 13.",
                }
            ],
        }
        ability_scores = {
            "strength": 10, "dexterity": 14, "constitution": 10,
            "intelligence": 10, "wisdom": 10, "charisma": 10,
        }
        class_data = {"class_name": "wizard", "hit_die": "d6"}

        inputs = character_data_to_inputs(
            ability_scores, class_data, None, species, None, 1,
        )
        computed = evaluate(DND_5E_2024_RULESET, inputs)
        assert computed["armor_class"] == 13
        assert inputs["natural_armor_ac"] == 13

    def test_natural_armor_lower_than_equipped_armor(self):
        """When equipped armor gives better AC, natural armor is ignored."""
        from dndwright import DND_5E_2024_RULESET, evaluate

        species = {
            "speed": 30,
            "traits": [
                {
                    "name": "Carapace",
                    "description": "Your shell gives natural armor AC 12.",
                }
            ],
        }
        ability_scores = {
            "strength": 10, "dexterity": 10, "constitution": 10,
            "intelligence": 10, "wisdom": 10, "charisma": 10,
        }
        class_data = {"class_name": "fighter", "hit_die": "d10"}
        equipment = {
            "armor": {
                "type": "chain_mail",
                "magic_bonus": 0,
            },
        }
        inputs = character_data_to_inputs(
            ability_scores, class_data, None, species, None, 1, equipment,
        )
        computed = evaluate(DND_5E_2024_RULESET, inputs)
        # Chain mail base AC = 16, no DEX.  max(12, 16) = 16.
        assert computed["armor_class"] == 16

    def test_exoskeleton_trait_recognized(self):
        """'Exoskeleton' keyword also triggers natural armor parsing."""
        species = {
            "speed": 30,
            "traits": [
                {
                    "name": "Chitin Exoskeleton",
                    "description": "Your exoskeleton provides natural protection. AC 14.",
                }
            ],
        }
        inputs = self._sheet_for_species(species)
        assert inputs["natural_armor_ac"] == 14

    def test_no_traits_handled_gracefully(self):
        """Missing traits, non-list traits, empty traits → natural_armor_ac = 0."""
        for species in [{}, {"traits": None}, {"traits": []}, {"traits": "not_a_list"}]:
            inputs = self._sheet_for_species(species)
            assert inputs["natural_armor_ac"] == 0
