"""Evaluation-order caching — correctness, reuse, and GC eviction.

The topological sort depends only on graph structure, so the evaluator caches it
per ruleset instance (see ``_cached_eval_order``). These tests pin that the cache
is transparent (same answer as a fresh sort) and well-behaved (reused for the
singleton, evicted when a transient ruleset is collected).
"""

import gc

from dndwright import DND_5E_2024_RULESET
from dndwright.rules import evaluator
from dndwright.rules.evaluator import (
    _ORDER_CACHE,
    _cached_eval_order,
    _topological_sort,
    get_evaluation_order,
)


def test_cached_order_matches_fresh_sort():
    fresh = _topological_sort(DND_5E_2024_RULESET.nodes)
    assert get_evaluation_order(DND_5E_2024_RULESET) == fresh


def test_order_is_a_valid_topological_order():
    nodes = DND_5E_2024_RULESET.nodes
    order = get_evaluation_order(DND_5E_2024_RULESET)
    assert set(order) == set(nodes)  # every node appears exactly once
    position = {nid: i for i, nid in enumerate(order)}
    for nid, node in nodes.items():
        for dep in evaluator._get_dependencies(node, nodes):
            assert position[dep] < position[nid], f"{dep} must precede {nid}"


def test_singleton_order_is_cached_and_reused():
    first = _cached_eval_order(DND_5E_2024_RULESET)
    second = _cached_eval_order(DND_5E_2024_RULESET)
    assert first is second  # same list object → served from cache


def test_transient_ruleset_entry_is_evicted_on_gc():
    clone = DND_5E_2024_RULESET.model_copy()
    key = (id(clone), len(clone.nodes))
    _cached_eval_order(clone)
    assert key in _ORDER_CACHE
    del clone
    gc.collect()
    assert key not in _ORDER_CACHE  # weakref.finalize cleaned it up
