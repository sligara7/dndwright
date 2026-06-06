"""API contract — the public surface other code may rely on.

Pins `dndwright.__all__` and key signatures so a breaking change fails CI. If a
change here is intentional, update the expected set *and* the version / CHANGELOG
per semver.
"""

import inspect

import dndwright

EXPECTED_PUBLIC = {
    "evaluate_character",
    "compute_key_stats",
    "compute_stat_diff",
    "validate_character_data",
    "CharacterInputError",
    "DND_5E_2024_RULESET",
    "evaluate",
    "assemble_character_inputs",
    "apply_modifiers",
    "get_evaluation_order",
    "get_node_dependencies",
    "get_downstream_nodes",
    "get_graph_edges",
    "get_all_lookup_tables",
    "compose",
    "modifier",
    "component_from_content",
    "component_to_dict",
    "component_from_dict",
    "COMPONENT_SCHEMA_VERSION",
    "RESISTANCES_NODE",
    "IMMUNITIES_NODE",
    "VULNERABILITIES_NODE",
    "DAMAGE_CHANNELS",
    "Component",
    "Contribution",
    "character_data_to_inputs",
    "computed_values_to_sheet",
    "Ruleset",
    "ComputationNode",
    "FormulaSpec",
    "NodeType",
    "validate_ruleset",
    "assert_valid_ruleset",
    "ValidationIssue",
    "RulesetValidationError",
    "known_operations",
    "register_operation",
    "Operation",
    "describe_operations",
    "apply_theme_scaling",
    "get_theme_scaling",
    "list_predefined_themes",
    "PREDEFINED_THEME_SCALING",
    "ThemeScalingLayer",
    "to_mermaid",
    "to_dot",
    "load_ontology",
    "Ontology",
    "load_content",
    "categories",
    "generate_library",
    "CONTENT_MODELS",
    "Creature",
    "CharClass",
    "Species",
    "Spell",
    "MagicItem",
    "Background",
    "Feat",
    "Weapon",
    "Armor",
    "Condition",
    "Modifier",
    "DiceEngine",
}


class TestPublicSurface:
    def test_all_matches_contract(self):
        assert set(dndwright.__all__) == EXPECTED_PUBLIC

    def test_everything_in_all_is_importable(self):
        for name in dndwright.__all__:
            assert hasattr(dndwright, name), f"{name} missing from package"

    def test_version_present(self):
        assert isinstance(dndwright.__version__, str)
        assert dndwright.__version__.count(".") >= 2

    def test_version_matches_package_metadata(self):
        # __version__ must match the installed (pyproject) version, so a missed
        # bump can't ship a mislabelled wheel. Skips when run from source.
        import importlib.metadata as md

        try:
            installed = md.version("dndwright")
        except md.PackageNotFoundError:
            import pytest

            pytest.skip("dndwright not installed; running from source tree")
        assert installed == dndwright.__version__


class TestKeySignatures:
    def test_evaluate_character_takes_a_mapping(self):
        params = list(inspect.signature(dndwright.evaluate_character).parameters)
        assert len(params) >= 1  # (data, ...)

    def test_evaluate_takes_ruleset_and_inputs(self):
        params = list(inspect.signature(dndwright.evaluate).parameters)
        assert params[:2] == ["ruleset", "inputs"] or len(params) >= 2


# ---------------------------------------------------------------------------
# #1 — Full signature pins for every public callable.
#
# These pin parameter names, order, defaults, and (string) annotations, so a
# silent signature change (reordered/renamed param, changed default, new
# required arg, changed return type) fails CI — not just a dropped name.
# `str(inspect.signature(...))` renders annotations as written (the package uses
# `from __future__ import annotations`, so they're already strings).
#
# To intentionally change a signature: update the expected string here, bump the
# version, and note it in the CHANGELOG per the versioning policy.
# ---------------------------------------------------------------------------

EXPECTED_SIGNATURES = {
    "apply_modifiers": "(computed: 'dict[str, Any]', inputs: 'dict[str, Any]') -> 'dict[str, Any]'",
    "apply_theme_scaling": "(ruleset: 'Ruleset', layer: 'ThemeScalingLayer') -> 'Ruleset'",
    "assemble_character_inputs": (
        "(class_mechanics: 'ClassMechanics', species_mechanics: 'SpeciesMechanics | None' = None, "
        "subclass_mechanics: 'SubclassMechanics | None' = None, "
        "background_mechanics: 'BackgroundMechanics | None' = None, "
        "ability_scores: 'dict[str, int] | None' = None, level: 'int' = 1, class_name: 'str' = '', "
        "additional_classes: 'dict[str, ClassMechanics] | None' = None, "
        "additional_class_levels: 'dict[str, int] | None' = None, "
        "equipped_armor: 'ArmorMechanics | None' = None, has_shield: 'bool' = False, "
        "feats: 'list[FeatMechanics] | None' = None) -> 'dict[str, Any]'"
    ),
    "assert_valid_ruleset": "(ruleset: 'Ruleset') -> 'None'",
    "categories": "() -> 'list[str]'",
    "character_data_to_inputs": (
        "(ability_scores: 'dict[str, int]', class_data: 'dict', subclass_data: 'dict | None', "
        "species_data: 'dict', background_data: 'dict | None', level: 'int', "
        "equipment: 'dict | None' = None) -> 'dict[str, Any]'"
    ),
    "component_from_content": (
        "(item: 'dict[str, Any]', *, choices: 'dict[str, str] | None' = None) -> 'Component | None'"
    ),
    "component_from_dict": "(data: 'dict[str, Any]') -> 'Component'",
    "component_to_dict": "(component: 'Component') -> 'dict[str, Any]'",
    "compose": "(base: 'Ruleset', *components: 'Component') -> 'Ruleset'",
    "compute_key_stats": (
        "(session_data: 'dict', *, scaling: 'ThemeScalingLayer | None' = None) -> 'dict[str, Any]'"
    ),
    "compute_stat_diff": (
        "(before_data: 'dict', after_data: 'dict', *, scaling: 'ThemeScalingLayer | None' = None) "
        "-> 'dict[str, dict[str, Any]]'"
    ),
    "computed_values_to_sheet": (
        "(computed: 'dict[str, Any]', ability_scores: 'dict[str, int]', class_data: 'dict', "
        "subclass_data: 'dict | None', species_data: 'dict', background_data: 'dict | None', "
        "level: 'int', equipment: 'dict | None' = None, spells: 'dict | None' = None, "
        "narrative: 'dict | None' = None, character_name: 'str' = 'Unnamed', "
        "alignment: 'str | None' = None, selected_feats: 'list[dict] | None' = None) -> 'dict'"
    ),
    "describe_operations": "() -> 'dict[str, str]'",
    "evaluate": "(ruleset: 'Ruleset', input_values: 'dict[str, Any]') -> 'dict[str, Any]'",
    "evaluate_character": (
        "(session_data: 'dict', *, strict: 'bool' = False, "
        "scaling: 'ThemeScalingLayer | None' = None) -> 'dict'"
    ),
    "generate_library": (
        "(llm: 'JsonLLM', classes: 'int' = 6, species: 'int' = 6, creatures: 'int' = 12) "
        "-> 'dict[str, list[dict]]'"
    ),
    "get_all_lookup_tables": "() -> 'dict'",
    "get_downstream_nodes": "(ruleset: 'Ruleset', node_id: 'str') -> 'list[str]'",
    "get_evaluation_order": "(ruleset: 'Ruleset') -> 'list[str]'",
    "get_graph_edges": "(ruleset: 'Ruleset') -> 'list[tuple[str, str]]'",
    "get_node_dependencies": "(ruleset: 'Ruleset', node_id: 'str') -> 'list[str]'",
    "get_theme_scaling": "(theme: 'str') -> 'ThemeScalingLayer | None'",
    "known_operations": "() -> 'list[str]'",
    "list_predefined_themes": "() -> 'list[dict]'",
    "load_content": "(category: 'str') -> 'list[dict]'",
    "load_ontology": "(path: 'str | Path | None' = None) -> 'Ontology'",
    "modifier": (
        "(id: 'str', *, target: 'str', amount: 'Any', mode: 'str' = 'add', name: 'str' = '', "
        "description: 'str' = '') -> 'Component'"
    ),
    "register_operation": "(name: 'str', fn: 'Operation', *, overwrite: 'bool' = False) -> 'None'",
    "to_dot": "(ruleset: 'Ruleset', *, cluster: 'bool' = True) -> 'str'",
    "to_mermaid": "(ruleset: 'Ruleset', *, direction: 'str' = 'TD', cluster: 'bool' = True) -> 'str'",
    "validate_character_data": "(session_data: 'dict') -> 'list[str]'",
    "validate_ruleset": "(ruleset: 'Ruleset') -> 'list[ValidationIssue]'",
    # Public classes whose constructor is a documented call site.
    "DiceEngine": "(seed: 'int | None' = None, *, rng: 'random.Random | None' = None)",
}


class TestPublicSignatures:
    def test_pinned_set_matches_public_callables(self):
        # Every public free function must be pinned (DiceEngine is the one class
        # constructor we also pin). Catches a new public function that ships
        # without a signature contract.
        public_functions = {
            name for name in dndwright.__all__ if inspect.isfunction(getattr(dndwright, name))
        }
        pinned_functions = set(EXPECTED_SIGNATURES) - {"DiceEngine"}
        assert pinned_functions == public_functions

    def test_signatures_match(self):
        for name, expected in EXPECTED_SIGNATURES.items():
            actual = str(inspect.signature(getattr(dndwright, name)))
            assert actual == expected, f"signature of {name} changed:\n  was: {expected}\n  now: {actual}"


# ---------------------------------------------------------------------------
# #2 — Output-shape pin for evaluate_character.
#
# The returned sheet's key set is the documented data contract for the primary
# entry point. It is stable across class types and input completeness (a caster
# vs non-caster, full vs minimal input all return the same keys), so an exact
# match is the right pin — adding/removing a key requires a deliberate edit here.
# ---------------------------------------------------------------------------

EXPECTED_SHEET_KEYS = {
    "ability_modifiers", "ability_modifiers_display", "ability_scores", "alignment",
    "armor_class", "background_name", "character_name", "class_name", "equipment",
    "features_and_traits", "hit_dice", "hit_die_type", "hit_points", "initiative",
    "initiative_display", "level", "movement_types", "passive_scores", "personality",
    "proficiencies", "proficiency_bonus", "proficiency_display", "saving_throws", "skills",
    "species_name", "species_traits_consolidated", "speed", "spellcasting", "subclass_name",
}


class TestOutputShape:
    _BASE = {
        "ability_scores": {"strength": 15, "dexterity": 14, "constitution": 14,
                           "intelligence": 10, "wisdom": 12, "charisma": 8},
        "species_data": {"name": "Human", "speed": 30},
        "level": 5,
    }

    def test_sheet_keys_match_contract(self):
        sheet = dndwright.evaluate_character({**self._BASE, "class_data": {"class_name": "wizard"}})
        assert set(sheet) == EXPECTED_SHEET_KEYS

    def test_sheet_keys_stable_across_class_and_input(self):
        # Same key set whether or not the class casts spells, and for minimal input.
        ftr = dndwright.evaluate_character({**self._BASE, "class_data": {"class_name": "fighter"}})
        mini = dndwright.evaluate_character(
            {"ability_scores": self._BASE["ability_scores"],
             "class_data": {"class_name": "rogue"}, "level": 1}
        )
        assert set(ftr) == EXPECTED_SHEET_KEYS
        assert set(mini) == EXPECTED_SHEET_KEYS


# ---------------------------------------------------------------------------
# #3 — Field pins for every exported pydantic model (+ the NodeType enum).
#
# Pins the field set of each public model so a rename/removal/added-required
# field fails CI. Pydantic lets you *add* an optional field safely; this pin
# still flags it, forcing a conscious "I'm extending this model" edit + version
# bump. Field types are not pinned here (the signature/field *names* are the load-
# bearing contract for serialised data and attribute access).
# ---------------------------------------------------------------------------

EXPECTED_MODEL_FIELDS = {
    "Armor": ["ac_bonus", "adds_dex", "base_ac", "category", "cost", "dex_cap", "name",
              "stealth_disadvantage", "strength_requirement", "weight"],
    "Background": ["ability_score_rule", "ability_scores", "choices", "component", "equipment",
                   "feat", "name", "skill_proficiencies", "tool_proficiency"],
    "CharClass": ["armor_training", "description", "features", "hit_die", "name", "primary_ability",
                  "saving_throws", "skill_proficiencies", "spellcasting", "starting_equipment",
                  "subclass", "subclass_features", "subclass_level", "tool_proficiencies",
                  "weapon_proficiencies"],
    "Component": ["contributions", "id", "metadata", "name", "nodes"],
    "ComputationNode": ["default_value", "description", "formula", "group", "id", "input_key",
                        "inputs", "label", "layer", "max_value", "min_value", "node_type"],
    "Condition": ["description", "display_name", "effects", "grants_immunity_to", "implies",
                  "levels", "mechanics", "name"],
    "Contribution": ["mode", "source", "target"],
    "Creature": ["abilities", "ac", "actions", "alignment", "bonus_actions", "condition_immunities",
                 "cr", "cr_numeric", "creature_subtype", "creature_type", "damage_immunities",
                 "damage_resistances", "damage_vulnerabilities", "gear", "hp", "hp_formula",
                 "initiative", "languages", "legendary_actions", "legendary_actions_intro", "name",
                 "proficiency_bonus", "reactions", "saving_throws", "senses", "size", "skills",
                 "speed", "swarm", "traits", "xp", "xp_lair"],
    "Feat": ["category", "choices", "component", "description", "name", "prerequisite", "repeatable"],
    "FormulaSpec": ["args", "op"],
    "MagicItem": ["attunement_required", "category", "component", "description", "name", "rarity",
                  "type_line"],
    "Modifier": ["amount", "condition", "formula", "mode", "target"],
    "Ontology": ["edge_types", "name", "node_types", "version"],
    "Ruleset": ["id", "lookup_tables", "metadata", "name", "nodes", "version"],
    "Species": ["choices", "component", "creature_type", "description", "name", "senses", "size",
                "speed", "traits"],
    "Spell": ["casting_time", "classes", "component", "components", "description", "duration",
              "level", "name", "range", "school"],
    "ThemeScalingLayer": ["description", "flavor_renames", "input_overrides", "lookup_overrides",
                          "notes", "theme"],
    "Weapon": ["category", "cost", "damage", "damage_dice", "damage_type", "kind", "mastery", "name",
               "properties", "weight"],
}

EXPECTED_NODE_TYPE_MEMBERS = {"AGGREGATE", "FORMULA", "INPUT", "LOOKUP", "OUTPUT"}


class TestModelFields:
    def test_pinned_set_matches_public_models(self):
        # Every exported pydantic model must be pinned — a new public model can't
        # ship without a field contract.
        public_models = {
            name for name in dndwright.__all__
            if inspect.isclass(getattr(dndwright, name))
            and hasattr(getattr(dndwright, name), "model_fields")
        }
        assert set(EXPECTED_MODEL_FIELDS) == public_models

    def test_model_fields_match(self):
        for name, expected in EXPECTED_MODEL_FIELDS.items():
            actual = sorted(getattr(dndwright, name).model_fields.keys())
            assert actual == expected, f"fields of {name} changed:\n  was: {expected}\n  now: {actual}"

    def test_node_type_members(self):
        assert set(dndwright.NodeType.__members__) == EXPECTED_NODE_TYPE_MEMBERS
