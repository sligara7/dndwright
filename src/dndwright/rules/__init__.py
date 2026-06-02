"""Character sheet computation graph engine.

Models D&D character sheets as a directed acyclic graph where nodes are values
and edges are dependencies. Formulas are data (JSON-serializable DSL), not code.

Usage:
    from rules.dnd_5e_2024 import DND_5E_2024_RULESET
    from rules.evaluator import evaluate
    from rules.assembler import assemble_character_inputs, apply_modifiers
    from rules.components import ClassMechanics, SpeciesMechanics, ...

    inputs = assemble_character_inputs(
        class_mechanics=class_mech,
        species_mechanics=species_mech,
        background_mechanics=bg_mech,
        ability_scores={...},
        level=5,
    )
    computed = evaluate(DND_5E_2024_RULESET, inputs)
    computed = apply_modifiers(computed, inputs)
"""

from .assembler import apply_modifiers, assemble_character_inputs
from .evaluator import (
    evaluate,
    get_downstream_nodes,
    get_evaluation_order,
    get_graph_edges,
    get_node_dependencies,
)
from .export import to_dot, to_mermaid
from .lookup_tables import get_all_lookup_tables
from .operations import Operation, register_operation
from .schema import ComputationNode, FormulaSpec, NodeType, Ruleset
from .validation import (
    RulesetValidationError,
    ValidationIssue,
    assert_valid_ruleset,
    known_operations,
    validate_ruleset,
)

__all__ = [
    "ComputationNode",
    "FormulaSpec",
    "NodeType",
    "Operation",
    "Ruleset",
    "RulesetValidationError",
    "ValidationIssue",
    "apply_modifiers",
    "assemble_character_inputs",
    "assert_valid_ruleset",
    "evaluate",
    "get_all_lookup_tables",
    "get_downstream_nodes",
    "get_evaluation_order",
    "get_graph_edges",
    "get_node_dependencies",
    "known_operations",
    "register_operation",
    "to_dot",
    "to_mermaid",
    "validate_ruleset",
]
