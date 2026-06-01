"""Tests for the bundled D&D component ontology + loader."""


from dndwright import Ontology, load_ontology
from dndwright.ontology import EdgeTypeDef, NodeTypeDef, parse_ontology

ONTO = load_ontology()

CORE_NODE_TYPES = {
    "Class", "Subclass", "Species", "Background", "Feat",
    "Spell", "Equipment", "MagicItem", "Creature",
}
CHARACTER_EDGES = {
    "HAS_CLASS", "HAS_SUBCLASS", "HAS_SPECIES", "HAS_BACKGROUND",
    "HAS_FEAT", "HAS_SPELL", "HAS_EQUIPMENT",
}


class TestLoad:
    def test_loads_bundled_ontology(self):
        assert isinstance(ONTO, Ontology)
        assert ONTO.name == "dnd"
        assert isinstance(ONTO.version, int)

    def test_has_core_component_node_types(self):
        assert CORE_NODE_TYPES <= set(ONTO.node_types)

    def test_node_types_are_typed(self):
        cls = ONTO.node_types["Class"]
        assert isinstance(cls, NodeTypeDef)
        assert cls.properties["name"].required is True
        assert cls.properties["hit_die"].type == "string"

    def test_edges_are_typed_with_endpoints(self):
        e = ONTO.edge_types["HAS_CLASS"]
        assert isinstance(e, EdgeTypeDef)
        assert e.source == ["Character"]
        assert e.target == ["Class"]

    def test_multi_endpoint_edges_normalised_to_lists(self):
        # HAS_STAT_BLOCK / INSTANCE_OF have list-valued from/to.
        inst = ONTO.edge_types["INSTANCE_OF"]
        assert set(inst.source) == {"MagicItem", "Equipment", "Creature"}
        assert set(inst.target) == {"MagicItem", "Equipment", "Creature"}


class TestQueries:
    def test_edges_from_character(self):
        assert CHARACTER_EDGES <= set(ONTO.edges_from("Character"))

    def test_edges_to_class(self):
        assert "HAS_CLASS" in ONTO.edges_to("Class")

    def test_required_properties(self):
        # every component requires a name
        for nt in CORE_NODE_TYPES:
            assert "name" in ONTO.node_types[nt].required_properties()


class TestNeutrality:
    def test_no_app_specific_node_types_or_properties(self):
        # The public ontology must not leak host-app scoping.
        assert "Room" not in ONTO.node_types
        for nt in ONTO.node_types.values():
            assert "story_id" not in nt.properties
            assert "map_id" not in nt.properties


class TestParseDirect:
    def test_parse_minimal_schema(self):
        onto = parse_ontology({
            "schema": {
                "name": "toy",
                "version": 1,
                "node_types": {"Thing": {"properties": {"name": {"type": "string", "required": True}}}},
                "edge_types": {"REL": {"from": "Thing", "to": ["Thing"]}},
            }
        })
        assert onto.node_types["Thing"].properties["name"].required
        assert onto.edge_types["REL"].source == ["Thing"]
        assert onto.edge_types["REL"].target == ["Thing"]
