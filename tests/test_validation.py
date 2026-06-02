"""Ruleset validation — the built-in graph is clean, and each defect is caught."""

import pytest

from dndwright import (
    DND_5E_2024_RULESET,
    ComputationNode,
    FormulaSpec,
    NodeType,
    Ruleset,
    RulesetValidationError,
    assert_valid_ruleset,
    known_operations,
    validate_ruleset,
)


def _ruleset(nodes: dict, tables: dict | None = None) -> Ruleset:
    return Ruleset(id="t", name="test", nodes=nodes, lookup_tables=tables or {})


def _codes(ruleset) -> set[str]:
    return {i.code for i in validate_ruleset(ruleset)}


class TestBuiltinIsValid:
    def test_no_issues_at_all(self):
        # The shipped ruleset must be clean — not even warnings.
        assert validate_ruleset(DND_5E_2024_RULESET) == []

    def test_assert_does_not_raise(self):
        assert_valid_ruleset(DND_5E_2024_RULESET)  # no exception

    def test_known_operations_nonempty_and_sorted(self):
        ops = known_operations()
        assert "ability_mod" in ops and "add" in ops
        assert ops == sorted(ops)


class TestDefectsCaught:
    def test_unknown_op_is_error(self):
        nodes = {
            "a": ComputationNode(id="a", node_type=NodeType.INPUT, label="A"),
            "b": ComputationNode(id="b", node_type=NodeType.FORMULA, label="B",
                                 formula=FormulaSpec(op="no_such_op", args=["a"])),
        }
        assert "unknown_op" in _codes(_ruleset(nodes))

    def test_id_mismatch_is_error(self):
        nodes = {"a": ComputationNode(id="WRONG", node_type=NodeType.INPUT, label="A")}
        assert "id_mismatch" in _codes(_ruleset(nodes))

    def test_formula_node_without_formula_is_error(self):
        nodes = {"a": ComputationNode(id="a", node_type=NodeType.FORMULA, label="A")}
        assert "formula_missing" in _codes(_ruleset(nodes))

    def test_cycle_is_error(self):
        nodes = {
            "a": ComputationNode(id="a", node_type=NodeType.FORMULA, label="A",
                                 formula=FormulaSpec(op="add", args=["b"])),
            "b": ComputationNode(id="b", node_type=NodeType.FORMULA, label="B",
                                 formula=FormulaSpec(op="add", args=["a"])),
        }
        assert "cycle" in _codes(_ruleset(nodes))

    def test_unknown_input_ref_is_warning(self):
        nodes = {
            "a": ComputationNode(id="a", node_type=NodeType.INPUT, label="A",
                                 inputs=["ghost"]),
        }
        issues = validate_ruleset(_ruleset(nodes))
        assert any(i.code == "unknown_input_ref" and i.severity == "warning" for i in issues)

    def test_input_with_formula_is_warning(self):
        nodes = {
            "a": ComputationNode(id="a", node_type=NodeType.INPUT, label="A",
                                 formula=FormulaSpec(op="const", args=[1])),
        }
        issues = validate_ruleset(_ruleset(nodes))
        assert any(i.code == "input_with_formula" and i.severity == "warning" for i in issues)

    def test_missing_lookup_table_is_warning(self):
        nodes = {
            "k": ComputationNode(id="k", node_type=NodeType.INPUT, label="K"),
            "v": ComputationNode(id="v", node_type=NodeType.LOOKUP, label="V",
                                 formula=FormulaSpec(op="lookup", args=["absent_table", "k"])),
        }
        issues = validate_ruleset(_ruleset(nodes))
        assert any(i.code == "missing_lookup_table" for i in issues)


class TestAssertRaises:
    def test_raises_on_error_severity(self):
        nodes = {"a": ComputationNode(id="WRONG", node_type=NodeType.INPUT, label="A")}
        with pytest.raises(RulesetValidationError) as exc:
            assert_valid_ruleset(_ruleset(nodes))
        assert exc.value.issues  # carries the structured issues

    def test_does_not_raise_on_warnings_only(self):
        nodes = {
            "a": ComputationNode(id="a", node_type=NodeType.INPUT, label="A",
                                 inputs=["ghost"]),  # warning only
        }
        assert_valid_ruleset(_ruleset(nodes))  # no raise
