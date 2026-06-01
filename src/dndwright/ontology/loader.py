"""Load and model the D&D component ontology (``dnd.yaml``).

Parses the bundled graph schema into typed, queryable pydantic models: node types
(with typed properties) and edge types (with normalised from/to endpoints). A host
graph app can use this to validate or drive its own D&D component graph.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class PropertyDef(BaseModel):
    """A node/edge property definition."""

    type: str
    required: bool = False
    indexed: bool = False
    description: str | None = None


class NodeTypeDef(BaseModel):
    """A node type: a named set of typed properties."""

    properties: dict[str, PropertyDef] = Field(default_factory=dict)
    embedding_field: str | None = None

    def required_properties(self) -> list[str]:
        return [name for name, p in self.properties.items() if p.required]


class EdgeTypeDef(BaseModel):
    """An edge type with normalised ``source``/``target`` node-type lists."""

    source: list[str] = Field(default_factory=list)  # the schema's `from`
    target: list[str] = Field(default_factory=list)  # the schema's `to`
    properties: dict[str, PropertyDef] = Field(default_factory=dict)
    description: str | None = None


class Ontology(BaseModel):
    """The parsed component ontology: node types + edge types."""

    name: str
    version: int
    node_types: dict[str, NodeTypeDef] = Field(default_factory=dict)
    edge_types: dict[str, EdgeTypeDef] = Field(default_factory=dict)

    def edges_from(self, node_type: str) -> list[str]:
        """Edge-type names that may originate at ``node_type``."""
        return [n for n, e in self.edge_types.items() if node_type in e.source]

    def edges_to(self, node_type: str) -> list[str]:
        """Edge-type names that may point at ``node_type``."""
        return [n for n, e in self.edge_types.items() if node_type in e.target]


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    return list(value) if isinstance(value, list) else [str(value)]


def parse_ontology(raw: dict) -> Ontology:
    """Build an :class:`Ontology` from a parsed schema mapping."""
    schema = raw["schema"]
    node_types = {
        name: NodeTypeDef(**(nt or {}))
        for name, nt in (schema.get("node_types") or {}).items()
    }
    edge_types: dict[str, EdgeTypeDef] = {}
    for name, edge in (schema.get("edge_types") or {}).items():
        edge = edge or {}
        edge_types[name] = EdgeTypeDef(
            source=_as_list(edge.get("from")),
            target=_as_list(edge.get("to")),
            properties={
                p: PropertyDef(**(d or {})) for p, d in (edge.get("properties") or {}).items()
            },
            description=(str(edge.get("description")).strip() or None)
            if edge.get("description")
            else None,
        )
    return Ontology(
        name=schema["name"],
        version=schema["version"],
        node_types=node_types,
        edge_types=edge_types,
    )


def load_ontology(path: str | Path | None = None) -> Ontology:
    """Load an ontology. With no ``path``, loads the bundled D&D ``dnd.yaml``."""
    if path is None:
        text = (importlib.resources.files("dndwright.ontology") / "dnd.yaml").read_text(
            encoding="utf-8"
        )
    else:
        text = Path(path).read_text(encoding="utf-8")
    return parse_ontology(yaml.safe_load(text))
