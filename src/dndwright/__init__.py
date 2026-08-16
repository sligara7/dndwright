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
    from dndwright import ClassMechanics
    inputs = assemble_character_inputs(class_mechanics=..., ability_scores={...}, level=5)
    computed = apply_modifiers(evaluate(DND_5E_2024_RULESET, inputs), inputs)

The rules tables (hit dice, spell slots, armour AC, save proficiencies) encode
game mechanics derived from the **D&D SRD 5.2 (CC-BY-4.0)** — see NOTICE.
"""

from .combat import weapon_attack
from .content import categories, generate_library, load_content
from .content.models import (
    CONTENT_MODELS,
    Armor,
    Background,
    CharClass,
    Condition,
    Creature,
    Feat,
    MagicItem,
    Modifier,
    Species,
    Spell,
    Weapon,
)
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
from .rules.components import ClassMechanics
from .rules.compose import (
    COMPONENT_SCHEMA_VERSION,
    Component,
    Contribution,
    component_from_content,
    component_from_dict,
    component_to_dict,
    compose,
    modifier,
)
from .rules.dnd_5e_2024 import (
    DAMAGE_CHANNELS,
    DND_5E_2024_RULESET,
    IMMUNITIES_NODE,
    RESISTANCES_NODE,
    VULNERABILITIES_NODE,
)
from .rules.evaluator import (
    evaluate,
    get_downstream_nodes,
    get_evaluation_order,
    get_graph_edges,
    get_node_dependencies,
)
from .rules.export import to_dot, to_mermaid
from .rules.lookup_tables import get_all_lookup_tables
from .rules.operations import Operation, describe_operations, register_operation
from .rules.schema import ComputationNode, FormulaSpec, NodeType, Ruleset
from .rules.theme_scaling import (
    PREDEFINED_THEME_SCALING,
    ThemeScalingLayer,
    apply_theme_scaling,
    get_theme_scaling,
    list_predefined_themes,
)
from .rules.validation import (
    RulesetValidationError,
    ValidationIssue,
    assert_valid_ruleset,
    known_operations,
    validate_ruleset,
)

__version__ = "0.29.0"

# homebrew validation (structural rules checks on LLM-generated components)
from .rules.homebrew_validator import (
    VALIDATORS as HOMEBREW_VALIDATORS,
)
from .rules.homebrew_validator import (
    validate_background_homebrew,
    validate_class_homebrew,
    validate_homebrew,
    validate_power_budget,
    validate_species_homebrew,
    validate_subclass_homebrew,
)

__all__ = [
    "COMPONENT_SCHEMA_VERSION",
    # content structure contract — canonical Pydantic models per category.
    # Consumers (e.g. generation_plus homebrew) conform to / subclass these so
    # generated content is structurally identical to official SRD content.
    "CONTENT_MODELS",
    "DAMAGE_CHANNELS",
    # ruleset + low-level evaluation
    "DND_5E_2024_RULESET",
    "HOMEBREW_VALIDATORS",
    "IMMUNITIES_NODE",
    "PREDEFINED_THEME_SCALING",
    # damage-defence channels (union nodes on the ruleset; feed combatant_defenses)
    "RESISTANCES_NODE",
    "VULNERABILITIES_NODE",
    "Armor",
    "Background",
    "CharClass",
    "CharacterInputError",
    "ClassMechanics",
    "Component",
    "ComputationNode",
    "Condition",
    "Contribution",
    "Creature",
    # dice engine (full typed surface in dndwright.dice)
    "DiceEngine",
    "Feat",
    "FormulaSpec",
    "MagicItem",
    "Modifier",
    "NodeType",
    "Ontology",
    "Operation",
    # schema types
    "Ruleset",
    "RulesetValidationError",
    "Species",
    "Spell",
    "ThemeScalingLayer",
    "ValidationIssue",
    "Weapon",
    "apply_modifiers",
    # theme scaling (mechanical profiles per setting theme)
    "apply_theme_scaling",
    "assemble_character_inputs",
    "assert_valid_ruleset",
    "categories",
    # neutral adapters
    "character_data_to_inputs",
    "component_from_content",
    "component_from_dict",
    # component (de)serialisation — persist a Component as data + rebuild it
    "component_to_dict",
    # graph composition — snap mini-graphs (items/feats/traits) onto a ruleset
    "compose",
    "compute_key_stats",
    "compute_stat_diff",
    "computed_values_to_sheet",
    "describe_operations",
    "evaluate",
    # high-level (dict in -> computed sheet out)
    "evaluate_character",
    "generate_library",
    # SRD reference tables (hit dice, spell slots, AC, rarity, XP, …)
    "get_all_lookup_tables",
    "get_downstream_nodes",
    # graph introspection (evaluation order, dependencies, edges)
    "get_evaluation_order",
    "get_graph_edges",
    "get_node_dependencies",
    "get_theme_scaling",
    "known_operations",
    "list_predefined_themes",
    # content (bundled starter + generator)
    "load_content",
    # component ontology (graph schema)
    "load_ontology",
    "modifier",
    # extend the formula DSL with custom operations
    "register_operation",
    "to_dot",
    # graph export (visualise the DAG)
    "to_mermaid",
    "validate_background_homebrew",
    "validate_character_data",
    # homebrew validation (structural rules checks on LLM-generated components)
    "validate_class_homebrew",
    "validate_homebrew",
    "validate_power_budget",
    # ruleset validation (catch authoring errors before evaluation)
    "validate_ruleset",
    "validate_species_homebrew",
    "validate_subclass_homebrew",
    "weapon_attack",
]
