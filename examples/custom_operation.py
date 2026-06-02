"""Extend the formula DSL with your own operation, then build a tiny custom ruleset.

Shows ``register_operation`` + authoring a ``Ruleset`` from nodes + ``validate_ruleset``.
Everything that consults the registry (evaluate, validation, known_operations) picks up
the new op automatically.

    python examples/custom_operation.py
"""

from dndwright import (
    ComputationNode,
    FormulaSpec,
    NodeType,
    Ruleset,
    assert_valid_ruleset,
    evaluate,
    register_operation,
)

# A pure (args, tables) -> value function — same shape as the built-ins.
register_operation("average", lambda args, _tables: sum(args) / len(args))

ruleset = Ruleset(
    id="demo", name="Average demo",
    nodes={
        "a": ComputationNode(id="a", node_type=NodeType.INPUT, label="A"),
        "b": ComputationNode(id="b", node_type=NodeType.INPUT, label="B"),
        "mean": ComputationNode(id="mean", node_type=NodeType.FORMULA, label="Mean",
                                formula=FormulaSpec(op="average", args=["a", "b"])),
    },
)

assert_valid_ruleset(ruleset)                         # raises if the graph is broken
print("mean of 4 and 8 =", evaluate(ruleset, {"a": 4, "b": 8})["mean"])   # 6.0
