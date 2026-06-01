"""Pydantic models for the computation graph schema."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Type of computation node."""

    INPUT = "input"  # User-provided value (ability score, level, class)
    FORMULA = "formula"  # Computed from other nodes via a formula
    LOOKUP = "lookup"  # Value from a lookup table keyed by another node
    AGGREGATE = "aggregate"  # Combines multiple nodes (e.g., sum of class HP contributions)
    OUTPUT = "output"  # Terminal display node (formatted string, etc.)


class FormulaSpec(BaseModel):
    """A formula expressed as a named operation + arguments.

    Safe, JSON-serializable, portable to TypeScript. Never eval().

    Examples:
        FormulaSpec(op="ability_mod", args=["str_score"])
        FormulaSpec(op="add", args=["dex_mod", "proficiency_bonus"])
        FormulaSpec(op="prof_add", args=["wis_mod", "proficiency_bonus", "save.wisdom.proficient"])
        FormulaSpec(op="lookup", args=["armor_base_ac", "armor_type"])
    """

    op: str
    args: list[Any] = Field(default_factory=list)


class ComputationNode(BaseModel):
    """A single node in the character sheet computation graph.

    Each node represents one value on the character sheet. Nodes can depend
    on other nodes via their formula args (which reference node IDs).
    """

    id: str  # Unique ID: "str_mod", "hp_max", "skill.perception"
    node_type: NodeType
    label: str  # Human-readable: "Strength Modifier"
    layer: int = 0  # 0=input, 1=simple derived, 2=complex derived
    group: str = ""  # "ability_scores", "combat", "skills", "spellcasting"
    formula: FormulaSpec | None = None  # How to compute this node
    inputs: list[str] = Field(default_factory=list)  # Explicit dependency list (node IDs)
    default_value: Any = None
    min_value: float | None = None  # Constraint: minimum allowed value
    max_value: float | None = None  # Constraint: maximum allowed value
    description: str = ""  # Rule citation, e.g., "PHB p.13"


class Ruleset(BaseModel):
    """A complete computation graph definition + lookup tables.

    The D&D 5e 2024 ruleset is the built-in default. Custom rulesets
    (Phase 4) will be stored in Neo4j.
    """

    id: str  # "dnd_5e_2024"
    name: str  # "D&D 5th Edition (2024)"
    version: str = "1.0.0"
    nodes: dict[str, ComputationNode]  # Keyed by node ID
    lookup_tables: dict[str, Any] = Field(default_factory=dict)  # Named tables
    metadata: dict[str, Any] = Field(default_factory=dict)
