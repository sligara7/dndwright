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

from .rules.adapters import character_data_to_inputs, computed_values_to_sheet
from .rules.assembler import apply_modifiers, assemble_character_inputs
from .rules.character_evaluator import compute_key_stats, evaluate_character
from .rules.dnd_5e_2024 import DND_5E_2024_RULESET
from .rules.evaluator import evaluate
from .rules.schema import ComputationNode, FormulaSpec, NodeType, Ruleset

__version__ = "0.1.0"

__all__ = [
    # high-level (dict in -> computed sheet out)
    "evaluate_character",
    "compute_key_stats",
    # ruleset + low-level evaluation
    "DND_5E_2024_RULESET",
    "evaluate",
    "assemble_character_inputs",
    "apply_modifiers",
    # neutral adapters
    "character_data_to_inputs",
    "computed_values_to_sheet",
    # schema types
    "Ruleset",
    "ComputationNode",
    "FormulaSpec",
    "NodeType",
]
