"""Character evaluator — single entry point for computing character sheets.

Replaces the old derive_character_sheet() with computation graph evaluation.
Pure functions, no I/O, no async.

Usage:
    from rules.character_evaluator import evaluate_character, compute_stat_diff

    sheet = evaluate_character(session_data)
    diff = compute_stat_diff(before_data, after_data)
"""

from __future__ import annotations

import copy
import logging
from typing import Any

from .adapters import character_data_to_inputs, computed_values_to_sheet
from .assembler import apply_modifiers
from .dnd_5e_2024 import DND_5E_2024_RULESET
from .evaluator import evaluate

logger = logging.getLogger(__name__)

# Key stats to include in diffs and summaries
KEY_STAT_NODES = {
    "hp_max": "Hit Points",
    "armor_class": "Armor Class",
    "initiative": "Initiative",
    "speed_base": "Speed",
    "proficiency_bonus": "Proficiency Bonus",
    "spell_save_dc": "Spell Save DC",
    "spell_attack": "Spell Attack",
    "save.strength.bonus": "STR Save",
    "save.dexterity.bonus": "DEX Save",
    "save.constitution.bonus": "CON Save",
    "save.intelligence.bonus": "INT Save",
    "save.wisdom.bonus": "WIS Save",
    "save.charisma.bonus": "CHA Save",
    "strength_mod": "STR Modifier",
    "dexterity_mod": "DEX Modifier",
    "constitution_mod": "CON Modifier",
    "intelligence_mod": "INT Modifier",
    "wisdom_mod": "WIS Modifier",
    "charisma_mod": "CHA Modifier",
    "passive_perception": "Passive Perception",
}


def _extract_session_fields(data: dict) -> dict:
    """Extract the fields needed for evaluation from session data.

    Session data may be the full session dict or the inner 'data' sub-dict.
    This normalizes either format.
    """
    # If this is a full session, unwrap to the data sub-dict
    inner = data.get("data", data)

    ability_scores = inner.get("ability_scores") or inner.get(
        "modified_ability_scores", {}
    )
    if not ability_scores:
        # Try identity phase format
        identity = inner.get("identity", {})
        ability_scores = identity.get("ability_scores", {})

    class_data = inner.get("class_data") or inner.get("class", {}) or {}
    subclass_data = inner.get("subclass_data") or inner.get("subclass")
    species_data = inner.get("species_data") or inner.get("species", {}) or {}
    background_data = inner.get("background_data") or inner.get("background")
    level = inner.get("level", 1)
    equipment = inner.get("equipment")
    spells = inner.get("spells")
    character_name = inner.get("character_name", "Unnamed")
    alignment = inner.get("alignment")
    selected_feats = inner.get("selected_feats", [])

    # Narrative pass-through
    narrative = {}
    for key in ("backstory", "personality", "appearance", "concept"):
        if inner.get(key):
            narrative[key] = inner[key]

    return {
        "ability_scores": ability_scores,
        "class_data": class_data,
        "subclass_data": subclass_data,
        "species_data": species_data,
        "background_data": background_data,
        "level": level,
        "equipment": equipment,
        "spells": spells,
        "narrative": narrative,
        "character_name": character_name,
        "alignment": alignment,
        "selected_feats": selected_feats,
    }


def evaluate_character(session_data: dict) -> dict:
    """Evaluate a character from session data → full computed character sheet.

    This is the single entry point that replaces derive_character_sheet().
    Pure function, no I/O, no async.

    Args:
        session_data: Session data dict (full session or inner data sub-dict).

    Returns:
        Complete character sheet dict matching the old derive_character_sheet() shape.
    """
    fields = _extract_session_fields(session_data)

    # Convert to flat graph inputs
    inputs = character_data_to_inputs(
        ability_scores=fields["ability_scores"],
        class_data=fields["class_data"],
        subclass_data=fields["subclass_data"],
        species_data=fields["species_data"],
        background_data=fields["background_data"],
        level=fields["level"],
        equipment=fields["equipment"],
    )

    # Evaluate the computation graph
    computed = evaluate(DND_5E_2024_RULESET, inputs)

    # Apply NodeModifiers from feats, class features, etc.
    computed = apply_modifiers(computed, inputs)

    # Reshape to character sheet format
    sheet = computed_values_to_sheet(
        computed=computed,
        ability_scores=fields["ability_scores"],
        class_data=fields["class_data"],
        subclass_data=fields["subclass_data"],
        species_data=fields["species_data"],
        background_data=fields["background_data"],
        level=fields["level"],
        equipment=fields["equipment"],
        spells=fields["spells"],
        narrative=fields["narrative"],
        character_name=fields["character_name"],
        alignment=fields["alignment"],
        selected_feats=fields["selected_feats"],
    )

    return sheet


def compute_stat_diff(
    before_data: dict,
    after_data: dict,
) -> dict[str, dict[str, Any]]:
    """Compute before/after stat changes between two session states.

    Returns a dict of node_id → {before, after, delta, label} for stats
    that changed. Only includes KEY_STAT_NODES for readability.

    Args:
        before_data: Session data before the change.
        after_data: Session data after the change.

    Returns:
        Dict of changed stats with before/after/delta/label.
    """
    before_fields = _extract_session_fields(before_data)
    after_fields = _extract_session_fields(after_data)

    # Build graph inputs for both states
    before_inputs = character_data_to_inputs(
        ability_scores=before_fields["ability_scores"],
        class_data=before_fields["class_data"],
        subclass_data=before_fields["subclass_data"],
        species_data=before_fields["species_data"],
        background_data=before_fields["background_data"],
        level=before_fields["level"],
        equipment=before_fields["equipment"],
    )
    after_inputs = character_data_to_inputs(
        ability_scores=after_fields["ability_scores"],
        class_data=after_fields["class_data"],
        subclass_data=after_fields["subclass_data"],
        species_data=after_fields["species_data"],
        background_data=after_fields["background_data"],
        level=after_fields["level"],
        equipment=after_fields["equipment"],
    )

    # Evaluate both
    before_computed = apply_modifiers(
        evaluate(DND_5E_2024_RULESET, before_inputs), before_inputs
    )
    after_computed = apply_modifiers(
        evaluate(DND_5E_2024_RULESET, after_inputs), after_inputs
    )

    # Build diff for key stats only
    diff: dict[str, dict[str, Any]] = {}
    for node_id, label in KEY_STAT_NODES.items():
        before_val = before_computed.get(node_id)
        after_val = after_computed.get(node_id)

        # Skip non-numeric values and unchanged values
        if not isinstance(before_val, (int, float)) or not isinstance(
            after_val, (int, float)
        ):
            continue
        if before_val == after_val:
            continue

        diff[node_id] = {
            "before": before_val,
            "after": after_val,
            "delta": after_val - before_val,
            "label": label,
        }

    return diff


def compute_key_stats(session_data: dict) -> dict[str, Any]:
    """Compute key stats from session data for display purposes.

    Returns a flat dict of node_id → value for KEY_STAT_NODES only.
    Useful for showing baseline stats in advancement options.
    """
    fields = _extract_session_fields(session_data)

    inputs = character_data_to_inputs(
        ability_scores=fields["ability_scores"],
        class_data=fields["class_data"],
        subclass_data=fields["subclass_data"],
        species_data=fields["species_data"],
        background_data=fields["background_data"],
        level=fields["level"],
        equipment=fields["equipment"],
    )

    computed = apply_modifiers(
        evaluate(DND_5E_2024_RULESET, inputs), inputs
    )

    return {
        node_id: {"value": computed.get(node_id), "label": label}
        for node_id, label in KEY_STAT_NODES.items()
        if computed.get(node_id) is not None
    }
