"""D&D component ontology — a graph schema for D&D building blocks.

    from dndwright import load_ontology
    onto = load_ontology()
    onto.node_types["Class"].properties["hit_die"].type   # "string"
    onto.edges_from("Character")                           # ["HAS_CLASS", ...]
"""

from .loader import (
    EdgeTypeDef,
    NodeTypeDef,
    Ontology,
    PropertyDef,
    load_ontology,
    parse_ontology,
)

__all__ = [
    "load_ontology",
    "parse_ontology",
    "Ontology",
    "NodeTypeDef",
    "EdgeTypeDef",
    "PropertyDef",
]
