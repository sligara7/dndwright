"""dndwright — a domain-neutral D&D 5e (2024) rules & character-computation engine.

A character sheet is modelled as a **directed acyclic computation graph**: nodes
are values, edges are dependencies, and formulas are *data* (a JSON-serialisable
DSL), not code. The engine is pure (pydantic + stdlib) — no application or
framework coupling — so any tool can map its own character data in and read
computed stats out.

Quickstart (one call — dict in, computed sheet out):

    from dndwright import evaluate_character
    sheet = evaluate_character({
        "ability_scores": {"strength": 8, "dexterity": 14, "constitution": 14,
                            "intelligence": 18, "wisdom": 12, "charisma": 10},
        "class_data": {"class_name": "wizard"},
        "species_data": {"name": "Human", "speed": 30},
        "level": 5,
    })
    sheet["proficiency_bonus"]   # 3
    sheet["ability_modifiers"]   # {"intelligence": 4, ...}

Lower level (assemble typed inputs, evaluate against the ruleset):

    from dndwright import (DND_5E_2024_RULESET, assemble_character_inputs,
                           evaluate, apply_modifiers)
    from dndwright.rules.components import ClassMechanics
    inputs = assemble_character_inputs(class_mechanics=..., ability_scores={...}, level=5)
    computed = apply_modifiers(evaluate(DND_5E_2024_RULESET, inputs), inputs)

The rules tables (hit dice, spell slots, armour AC, save proficiencies) encode
game mechanics derived from the **D&D SRD 5.2 (CC-BY-4.0)** — see NOTICE.
"""

from .content import categories, generate_library, load_content
from .dice import DiceEngine
from .ontology import Ontology, load_ontology
from .rules.adapters import character_data_to_inputs, computed_values_to_sheet
from .rules.assembler import apply_modifiers, assemble_character_inputs
from .rules.character_evaluator import (
    CharacterInputError,
    compute_key_stats,
    compute_stat_diff,
    evaluate_character,
    validate_character_data,
)
from .rules.dnd_5e_2024 import DND_5E_2024_RULESET
from .rules.evaluator import (
    evaluate,
    get_downstream_nodes,
    get_evaluation_order,
    get_graph_edges,
    get_node_dependencies,
)
from .rules.export import to_dot, to_mermaid
from .rules.lookup_tables import get_all_lookup_tables
from .rules.operations import Operation, register_operation
from .rules.schema import ComputationNode, FormulaSpec, NodeType, Ruleset
from .rules.validation import (
    RulesetValidationError,
    ValidationIssue,
    assert_valid_ruleset,
    known_operations,
    validate_ruleset,
)

__version__ = "0.6.0"

__all__ = [
    # high-level (dict in -> computed sheet out)
    "evaluate_character",
    "compute_key_stats",
    "compute_stat_diff",
    "validate_character_data",
    "CharacterInputError",
    # ruleset + low-level evaluation
    "DND_5E_2024_RULESET",
    "evaluate",
    "assemble_character_inputs",
    "apply_modifiers",
    # graph introspection (evaluation order, dependencies, edges)
    "get_evaluation_order",
    "get_node_dependencies",
    "get_downstream_nodes",
    "get_graph_edges",
    # SRD reference tables (hit dice, spell slots, AC, rarity, XP, …)
    "get_all_lookup_tables",
    # neutral adapters
    "character_data_to_inputs",
    "computed_values_to_sheet",
    # schema types
    "Ruleset",
    "ComputationNode",
    "FormulaSpec",
    "NodeType",
    # ruleset validation (catch authoring errors before evaluation)
    "validate_ruleset",
    "assert_valid_ruleset",
    "ValidationIssue",
    "RulesetValidationError",
    "known_operations",
    # extend the formula DSL with custom operations
    "register_operation",
    "Operation",
    # graph export (visualise the DAG)
    "to_mermaid",
    "to_dot",
    # component ontology (graph schema)
    "load_ontology",
    "Ontology",
    # content (bundled starter + generator)
    "load_content",
    "categories",
    "generate_library",
    # dice engine (full typed surface in dndwright.dice)
    "DiceEngine",
]
