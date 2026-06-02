"""Static integrity checks for a :class:`Ruleset`.

Catches authoring mistakes *before* evaluation, with clear messages instead of a
deep runtime ``EvaluationError``. Useful when forking/building custom rulesets.

    from dndwright import validate_ruleset, assert_valid_ruleset
    issues = validate_ruleset(my_ruleset)        # -> list[ValidationIssue]
    assert_valid_ruleset(my_ruleset)             # raises if any error-severity issue

What is checked (and what deliberately is *not*):
  * **error**   ``unknown_op``        — a formula's op is not in the operation registry.
  * **error**   ``id_mismatch``       — a node's dict key differs from ``node.id``.
  * **error**   ``cycle``             — the graph is not a DAG (would fail topo sort).
  * **error**   ``formula_missing``   — a FORMULA node has no ``formula`` to run.
  * **warning** ``input_with_formula``— an INPUT node carries a formula (ignored at eval).
  * **warning** ``unknown_input_ref`` — an explicit ``inputs`` entry names no real node.
  * **warning** ``missing_lookup_table`` — a ``lookup`` op references an absent table.

String formula args are intentionally *not* validated as references: the evaluator
treats any string matching a node id as a dependency and every other string as a
literal constant (table names, ability names, …), so an "unknown" string arg is
indistinguishable from a valid literal and would produce false positives.
"""

from __future__ import annotations

from typing import NamedTuple

from .evaluator import _topological_sort
from .operations import OPERATIONS
from .schema import NodeType, Ruleset


class ValidationIssue(NamedTuple):
    """One problem found in a ruleset.

    ``severity`` is ``"error"`` (evaluation would break) or ``"warning"`` (tolerated
    but likely a mistake). ``code`` is a stable machine-readable tag; ``node_id`` is
    the offending node, or ``None`` for graph-wide issues.
    """

    severity: str
    code: str
    message: str
    node_id: str | None = None


class RulesetValidationError(Exception):
    """Raised by :func:`assert_valid_ruleset` when error-severity issues are found."""

    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = issues
        lines = "\n".join(f"  [{i.code}] {i.message}" for i in issues)
        super().__init__(f"ruleset failed validation with {len(issues)} error(s):\n{lines}")


def validate_ruleset(ruleset: Ruleset) -> list[ValidationIssue]:
    """Return all integrity issues in ``ruleset`` (empty list = valid).

    Issues are returned, not raised, so callers can inspect warnings too. Use
    :func:`assert_valid_ruleset` to fail hard on error-severity issues.
    """
    nodes = ruleset.nodes
    tables = ruleset.lookup_tables
    issues: list[ValidationIssue] = []

    for key, node in nodes.items():
        # Dict key must agree with node.id — the evaluator keys by both.
        if node.id != key:
            issues.append(ValidationIssue(
                "error", "id_mismatch",
                f"node under key {key!r} has mismatched id {node.id!r}", key,
            ))

        # Explicit dependency ids that name no node (likely a typo).
        for inp in node.inputs:
            if inp not in nodes:
                issues.append(ValidationIssue(
                    "warning", "unknown_input_ref",
                    f"node {key!r} lists input {inp!r}, which is not a node", key,
                ))

        if node.node_type == NodeType.INPUT:
            if node.formula is not None:
                issues.append(ValidationIssue(
                    "warning", "input_with_formula",
                    f"INPUT node {key!r} has a formula, which is ignored at evaluation", key,
                ))
            continue

        if node.formula is None:
            if node.node_type == NodeType.FORMULA:
                issues.append(ValidationIssue(
                    "error", "formula_missing",
                    f"FORMULA node {key!r} has no formula to evaluate", key,
                ))
            continue

        # The op must exist, or evaluation raises EvaluationError.
        if node.formula.op not in OPERATIONS:
            issues.append(ValidationIssue(
                "error", "unknown_op",
                f"node {key!r} uses unknown op {node.formula.op!r}", key,
            ))

        # `lookup` ops name their table literally in args[0]; flag absent tables.
        if node.formula.op == "lookup" and node.formula.args:
            table_name = node.formula.args[0]
            if isinstance(table_name, str) and table_name not in tables:
                issues.append(ValidationIssue(
                    "warning", "missing_lookup_table",
                    f"node {key!r} looks up table {table_name!r}, absent from lookup_tables",
                    key,
                ))

    # Graph-wide: must be a DAG.
    try:
        _topological_sort(nodes)
    except Exception as e:  # EvaluationError on cycle
        issues.append(ValidationIssue("error", "cycle", str(e), None))

    return issues


def assert_valid_ruleset(ruleset: Ruleset) -> None:
    """Raise :class:`RulesetValidationError` if ``ruleset`` has error-severity issues.

    Warnings do not raise. To inspect warnings, call :func:`validate_ruleset` directly.
    """
    errors = [i for i in validate_ruleset(ruleset) if i.severity == "error"]
    if errors:
        raise RulesetValidationError(errors)


# Re-exported for convenience: the set of valid operation names a formula may use.
def known_operations() -> list[str]:
    """Return the sorted names of all operations a formula's ``op`` may reference."""
    return sorted(OPERATIONS)
