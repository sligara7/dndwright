"""Computation graph evaluator.

Pure function: evaluate(ruleset, input_values) -> all_computed_values.
No I/O, no side effects, trivially testable.

1. Topological sort on the graph (respecting node dependencies)
2. Walk in order, resolve each node's formula from its resolved inputs
3. Apply min/max constraints
"""

from __future__ import annotations

import weakref
from typing import Any

from .operations import OPERATIONS
from .schema import ComputationNode, NodeType, Ruleset


class EvaluationError(Exception):
    """Raised when the evaluator encounters an unresolvable node."""


# Cache of computed evaluation orders, keyed by (id(ruleset), node_count).
# The topological sort depends only on graph *structure*, which is immutable for
# the built-in singleton and for the usual build-once-then-evaluate pattern — so
# we compute it once per ruleset instead of on every evaluate() call. A
# weakref.finalize callback evicts the entry when the ruleset is garbage
# collected, preventing both memory leaks and id-reuse staleness. The node_count
# in the key guards against in-place add/remove of nodes on a mutable ruleset.
_ORDER_CACHE: dict[tuple[int, int], list[str]] = {}


def _cached_eval_order(ruleset: Ruleset) -> list[str]:
    """Return the topological evaluation order for ``ruleset``, cached per instance."""
    key = (id(ruleset), len(ruleset.nodes))
    order = _ORDER_CACHE.get(key)
    if order is None:
        order = _topological_sort(ruleset.nodes)
        _ORDER_CACHE[key] = order
        weakref.finalize(ruleset, _ORDER_CACHE.pop, key, None)
    return order


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

    # Sort nodes in dependency order (cached per ruleset instance)
    order = _cached_eval_order(ruleset)

    computed: dict[str, Any] = {}

    for nid in order:
        node = nodes[nid]

        if node.node_type == NodeType.INPUT:
            # Use provided value (under input_key, defaulting to the node id), else default.
            key = node.input_key if node.input_key is not None else nid
            value = input_values.get(key, node.default_value)
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
    return _cached_eval_order(ruleset)


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


def get_graph_edges(ruleset: Ruleset) -> list[tuple[str, str]]:
    """Return the dependency edges of the graph as ``(from_node, to_node)`` pairs.

    Each edge points from a dependency to the node that consumes it (evaluation order),
    sorted for deterministic output. Useful for building a graph/adjacency view without
    re-deriving edges from ``node.inputs`` + ``formula.args`` by hand.
    """
    nodes = ruleset.nodes
    edges: list[tuple[str, str]] = []
    for nid, node in nodes.items():
        for dep in _get_dependencies(node, nodes):
            edges.append((dep, nid))
    return sorted(edges)
