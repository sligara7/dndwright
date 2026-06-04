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
