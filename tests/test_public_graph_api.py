"""The graph-introspection + lookup-table accessors promoted to the public API.

These were private (`dndwright.rules.*`) but are load-bearing for downstream consumers
(e.g. a /rules/graph UI, rarity/spell-slot lookups). This pins them as public.
"""

import dndwright
from dndwright import (
    DND_5E_2024_RULESET,
    compute_stat_diff,
    get_all_lookup_tables,
    get_downstream_nodes,
    get_evaluation_order,
    get_graph_edges,
    get_node_dependencies,
)

R = DND_5E_2024_RULESET


def test_all_promoted_symbols_are_public():
    for name in (
        "compute_stat_diff", "get_evaluation_order", "get_node_dependencies",
        "get_downstream_nodes", "get_graph_edges", "get_all_lookup_tables",
    ):
        assert name in dndwright.__all__, f"{name} missing from __all__"
        assert hasattr(dndwright, name)


class TestGraphIntrospection:
    def test_evaluation_order_covers_all_nodes(self):
        order = get_evaluation_order(R)
        assert set(order) == set(R.nodes)

    def test_edges_are_sorted_dependency_pairs(self):
        edges = get_graph_edges(R)
        assert edges == sorted(edges)
        assert all(dep in R.nodes and node in R.nodes for dep, node in edges)
        # edges are consistent with get_node_dependencies for a known node
        deps = set(get_node_dependencies(R, "armor_class"))
        edge_deps = {dep for dep, node in edges if node == "armor_class"}
        # direct edges are a subset of the transitive dependency closure
        assert edge_deps <= deps

    def test_dependencies_and_downstream_are_inverse(self):
        # if X is a dependency of Y, then Y is downstream of X
        node = "proficiency_bonus"
        for down in get_downstream_nodes(R, node):
            assert node in get_node_dependencies(R, down)


class TestLookupTablesAccessor:
    def test_returns_the_srd_reference_tables(self):
        tables = get_all_lookup_tables()
        # the tables downstream consumers (e.g. gen_plus) depend on
        for key in (
            "rarity_level_requirements", "rarity_unlock_requirements",
            "spellcasting_type_by_class", "spell_slots_full", "spell_slots_half",
            "spell_slots_warlock", "armor_base_ac", "xp_thresholds", "weapon_mastery_map",
        ):
            assert key in tables, f"{key} missing from get_all_lookup_tables()"
            assert tables[key]  # non-empty

    def test_is_a_fresh_dict(self):
        # mutating the returned dict must not corrupt the engine's tables
        a = get_all_lookup_tables()
        a["armor_base_ac"] = {}
        assert get_all_lookup_tables()["armor_base_ac"]  # still intact


def test_compute_stat_diff_is_usable_from_top_level():
    base = {"ability_scores": {"strength": 15, "dexterity": 14, "constitution": 14,
                               "intelligence": 10, "wisdom": 12, "charisma": 8},
            "class_data": {"class_name": "fighter"},
            "species_data": {"name": "Human", "speed": 30}, "level": 4}
    diff = compute_stat_diff(base, {**base, "level": 5})
    assert "proficiency_bonus" in diff  # +2 → +3 at level 5


class TestOperationsAndThemeAccessors:
    def test_describe_operations_returns_name_to_doc(self):
        from dndwright import describe_operations, known_operations
        ops = describe_operations()
        assert set(ops) == set(known_operations())  # same names as known_operations
        assert ops["ability_mod"].startswith("(score - 10)")  # first docstring line
        assert all(isinstance(v, str) for v in ops.values())

    def test_theme_scaling_public_surface(self):
        from dndwright import (
            PREDEFINED_THEME_SCALING,
            ThemeScalingLayer,
            get_theme_scaling,
            list_predefined_themes,
        )
        themes = list_predefined_themes()
        assert themes and all("theme" in t for t in themes)
        name = themes[0]["theme"]
        assert name in PREDEFINED_THEME_SCALING
        assert isinstance(get_theme_scaling(name), ThemeScalingLayer)
        assert get_theme_scaling("nonexistent-theme") is None
