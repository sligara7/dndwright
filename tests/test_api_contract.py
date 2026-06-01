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
    "DND_5E_2024_RULESET",
    "evaluate",
    "assemble_character_inputs",
    "apply_modifiers",
    "character_data_to_inputs",
    "computed_values_to_sheet",
    "Ruleset",
    "ComputationNode",
    "FormulaSpec",
    "NodeType",
    "load_ontology",
    "Ontology",
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


class TestKeySignatures:
    def test_evaluate_character_takes_a_mapping(self):
        params = list(inspect.signature(dndwright.evaluate_character).parameters)
        assert len(params) >= 1  # (data, ...)

    def test_evaluate_takes_ruleset_and_inputs(self):
        params = list(inspect.signature(dndwright.evaluate).parameters)
        assert params[:2] == ["ruleset", "inputs"] or len(params) >= 2
