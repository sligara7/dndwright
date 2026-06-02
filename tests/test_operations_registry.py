"""Custom operation registry — register, use end-to-end, and the guard rails.

Registration mutates the process-global ``OPERATIONS``, so each test restores it.
"""

import pytest

from dndwright import (
    ComputationNode,
    FormulaSpec,
    NodeType,
    Ruleset,
    evaluate,
    known_operations,
    register_operation,
    validate_ruleset,
)
from dndwright.rules import operations as ops_mod


@pytest.fixture(autouse=True)
def _restore_operations():
    snapshot = dict(ops_mod.OPERATIONS)
    yield
    ops_mod.OPERATIONS.clear()
    ops_mod.OPERATIONS.update(snapshot)


def test_register_and_use_in_evaluation():
    register_operation("double", lambda args, _tables: args[0] * 2)
    nodes = {
        "x": ComputationNode(id="x", node_type=NodeType.INPUT, label="X"),
        "y": ComputationNode(id="y", node_type=NodeType.FORMULA, label="Y",
                             formula=FormulaSpec(op="double", args=["x"])),
    }
    ruleset = Ruleset(id="t", name="test", nodes=nodes)
    assert evaluate(ruleset, {"x": 21})["y"] == 42


def test_registered_op_is_known_and_passes_validation():
    register_operation("triple", lambda args, _tables: args[0] * 3)
    assert "triple" in known_operations()
    nodes = {
        "x": ComputationNode(id="x", node_type=NodeType.INPUT, label="X"),
        "y": ComputationNode(id="y", node_type=NodeType.FORMULA, label="Y",
                             formula=FormulaSpec(op="triple", args=["x"])),
    }
    # Would be flagged unknown_op before registration; clean after.
    assert validate_ruleset(Ruleset(id="t", name="test", nodes=nodes)) == []


def test_cannot_overwrite_builtin():
    with pytest.raises(ValueError, match="built-in"):
        register_operation("add", lambda args, _t: 0)


def test_duplicate_custom_requires_overwrite():
    register_operation("myop", lambda args, _t: 1)
    with pytest.raises(ValueError, match="already registered"):
        register_operation("myop", lambda args, _t: 2)
    register_operation("myop", lambda args, _t: 2, overwrite=True)  # ok


def test_rejects_empty_name_and_non_callable():
    with pytest.raises(ValueError):
        register_operation("", lambda args, _t: 1)
    with pytest.raises(TypeError):
        register_operation("bad", 123)  # type: ignore[arg-type]
