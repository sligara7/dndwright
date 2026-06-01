"""Computation graph evaluator.

Pure function: evaluate(ruleset, input_values) -> all_computed_values.
No I/O, no side effects, trivially testable.

1. Topological sort on the graph (respecting node dependencies)
2. Walk in order, resolve each node's formula from its resolved inputs
3. Apply min/max constraints
"""

from __future__ import annotations

from typing import Any

from .operations import OPERATIONS
from .schema import ComputationNode, NodeType, Ruleset


class EvaluationError(Exception):
    """Raised when the evaluator encounters an unresolvable node."""


def _topological_sort(nodes: dict[str, ComputationNode]) -> list[str]:
    """Kahn's algorithm for topological sort.

    Returns node IDs in evaluation order (dependencies before dependents).
    Raises EvaluationError if cycles are detected.
    """
    # Build adjacency and in-degree
    in_degree: dict[str, int] = dict.fromkeys(nodes, 0)
    dependents: dict[str, list[str]] = {nid: [] for nid in nodes}

    for nid, node in nodes.items():
        deps = _get_dependencies(node, nodes)
        in_degree[nid] = len(deps)
        for dep in deps:
            if dep in dependents:
                dependents[dep].append(nid)

    # Start with nodes that have no dependencies
    queue = [nid for nid, deg in in_degree.items() if deg == 0]
    order: list[str] = []

    while queue:
        # Sort for deterministic order
        queue.sort()
        nid = queue.pop(0)
        order.append(nid)
        for dep_nid in dependents[nid]:
            in_degree[dep_nid] -= 1
            if in_degree[dep_nid] == 0:
                queue.append(dep_nid)

    if len(order) != len(nodes):
        missing = set(nodes.keys()) - set(order)
        raise EvaluationError(f"Cycle detected in computation graph. Unresolvable nodes: {missing}")

    return order


def _get_dependencies(node: ComputationNode, all_nodes: dict[str, ComputationNode]) -> list[str]:
    """Extract dependency node IDs from a node's formula args and explicit inputs.

    Formula args that are strings matching a node ID are dependencies.
    Non-string args (constants) are not dependencies.
    """
    deps = set()

    # Explicit inputs
    for inp in node.inputs:
        if inp in all_nodes:
            deps.add(inp)

    # Formula args that reference other nodes
    if node.formula:
        for arg in node.formula.args:
            if isinstance(arg, str) and arg in all_nodes:
                deps.add(arg)

    return list(deps)


def _resolve_args(
    args: list[Any],
    computed: dict[str, Any],
    all_nodes: dict[str, ComputationNode],
) -> list[Any]:
    """Resolve formula arguments.

    - If an arg is a string matching a computed node ID, substitute the computed value.
    - Otherwise, pass the arg through as a literal constant.
    """
    resolved = []
    for arg in args:
        if isinstance(arg, str) and arg in all_nodes:
            resolved.append(computed.get(arg))
        else:
            resolved.append(arg)
    return resolved


def evaluate(
    ruleset: Ruleset,
    input_values: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate the computation graph with given inputs.

    Args:
        ruleset: The graph definition (nodes + lookup tables).
        input_values: Values for INPUT nodes, keyed by node ID.

    Returns:
        Dict of all computed values, keyed by node ID.
    """
    nodes = ruleset.nodes
    tables = ruleset.lookup_tables

    # Sort nodes in dependency order
    order = _topological_sort(nodes)

    computed: dict[str, Any] = {}

    for nid in order:
        node = nodes[nid]

        if node.node_type == NodeType.INPUT:
            # Use provided value, fall back to default
            value = input_values.get(nid, node.default_value)
            computed[nid] = value
            continue

        if node.formula is None:
            # No formula — use default or None
            computed[nid] = node.default_value
            continue

        # Resolve formula arguments
        resolved_args = _resolve_args(node.formula.args, computed, nodes)

        # Look up operation
        op_fn = OPERATIONS.get(node.formula.op)
        if op_fn is None:
            raise EvaluationError(f"Unknown operation '{node.formula.op}' in node '{nid}'")

        # Execute operation
        try:
            value = op_fn(resolved_args, tables)
        except Exception as e:
            raise EvaluationError(
                f"Error evaluating node '{nid}' (op={node.formula.op}, args={resolved_args}): {e}"
            ) from e

        # Apply constraints
        if value is not None and isinstance(value, (int, float)):
            if node.min_value is not None:
                value = max(value, node.min_value)
            if node.max_value is not None:
                value = min(value, node.max_value)

        computed[nid] = value

    return computed


def get_evaluation_order(ruleset: Ruleset) -> list[str]:
    """Return the topological evaluation order for debugging/visualization."""
    return _topological_sort(ruleset.nodes)


def get_node_dependencies(ruleset: Ruleset, node_id: str) -> list[str]:
    """Return all upstream dependencies of a node (transitive closure)."""
    nodes = ruleset.nodes
    if node_id not in nodes:
        return []

    visited = set()
    stack = [node_id]

    while stack:
        nid = stack.pop()
        if nid in visited:
            continue
        visited.add(nid)
        node = nodes[nid]
        deps = _get_dependencies(node, nodes)
        stack.extend(deps)

    visited.discard(node_id)
    return sorted(visited)


def get_downstream_nodes(ruleset: Ruleset, node_id: str) -> list[str]:
    """Return all downstream nodes that depend on a given node."""
    nodes = ruleset.nodes
    if node_id not in nodes:
        return []

    # Build reverse adjacency
    dependents: dict[str, set[str]] = {nid: set() for nid in nodes}
    for nid, node in nodes.items():
        deps = _get_dependencies(node, nodes)
        for dep in deps:
            if dep in dependents:
                dependents[dep].add(nid)

    visited = set()
    stack = [node_id]

    while stack:
        nid = stack.pop()
        if nid in visited:
            continue
        visited.add(nid)
        stack.extend(dependents.get(nid, set()))

    visited.discard(node_id)
    return sorted(visited)
