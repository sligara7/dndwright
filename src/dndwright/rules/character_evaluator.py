"""Character evaluator — single entry point for computing character sheets.

Replaces the old derive_character_sheet() with computation graph evaluation.
Pure functions, no I/O, no async.

Usage:
    from rules.character_evaluator import evaluate_character, compute_stat_diff

    sheet = evaluate_character(session_data)
    diff = compute_stat_diff(before_data, after_data)
"""

from __future__ import annotations

import logging
from typing import Any

from .adapters import character_data_to_inputs, computed_values_to_sheet
from .assembler import apply_modifiers
from .compose import Component, compose, component_from_dict
from .dnd_5e_2024 import DND_5E_2024_RULESET
from .evaluator import evaluate
from .theme_scaling import ThemeScalingLayer, apply_theme_scaling

logger = logging.getLogger(__name__)


def _ruleset_for(scaling: ThemeScalingLayer | None):
    """Base ruleset, theme-scaled when a ``scaling`` layer is supplied.

    ``None`` returns ``DND_5E_2024_RULESET`` unchanged (the default path), so existing
    callers are unaffected; a layer returns a fresh themed ``Ruleset`` via
    :func:`apply_theme_scaling`.
    """
    if scaling is None:
        return DND_5E_2024_RULESET
    return apply_theme_scaling(DND_5E_2024_RULESET, scaling)

_ABILITIES = ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")


class CharacterInputError(ValueError):
    """Raised by ``evaluate_character(..., strict=True)`` on malformed character data."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        joined = "\n".join(f"  - {p}" for p in problems)
        super().__init__(f"character data has {len(problems)} problem(s):\n{joined}")


def validate_character_data(session_data: dict) -> list[str]:
    """Return human-readable problems with ``session_data`` (empty list = usable).

    Surfaces input that would otherwise be silently coerced into a plausible-but-wrong
    sheet: missing/out-of-range ability scores default to 10, an omitted level defaults
    to 1, a missing class zeroes HP and spellcasting, etc. Use
    ``evaluate_character(data, strict=True)`` to raise on these.
    """
    if not isinstance(session_data, dict):
        return [f"character data must be a JSON object, got {type(session_data).__name__}"]

    fields = _extract_session_fields(session_data)
    problems: list[str] = []

    scores = fields["ability_scores"]
    if not scores:
        problems.append("ability_scores is missing or empty")
    elif not isinstance(scores, dict):
        problems.append(f"ability_scores must be a mapping, got {type(scores).__name__}")
    else:
        for ability in _ABILITIES:
            if ability not in scores:
                problems.append(f"ability_scores is missing {ability!r}")
                continue
            value = scores[ability]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                problems.append(f"ability score {ability!r} must be a number, got {value!r}")
            elif isinstance(value, float) and not value.is_integer():
                problems.append(f"ability score {ability!r}={value} must be a whole number")
            elif not 1 <= value <= 30:
                problems.append(f"ability score {ability!r}={value} is out of range 1..30")

    # Check the *raw* input for level presence: _extract_session_fields defaults a
    # missing level to 1, so we can't tell "omitted" from "1" from the normalized field.
    inner = session_data.get("data", session_data)
    level_given = isinstance(inner, dict) and "level" in inner
    level = fields["level"]
    if not level_given:
        problems.append("level is missing")
    elif isinstance(level, bool) or not isinstance(level, int):
        problems.append(f"level must be an integer, got {level!r}")
    elif level < 1:
        problems.append(f"level must be >= 1, got {level}")

    class_data = fields["class_data"]
    if not (isinstance(class_data, dict) and class_data.get("class_name")):
        problems.append("class_data.class_name is missing")

    return problems


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


def evaluate_character(
    session_data: dict,
    *,
    strict: bool = False,
    scaling: ThemeScalingLayer | None = None,
    components: list | None = None,
) -> dict:
    """Evaluate a character from session data → full computed character sheet.

    This is the single entry point that replaces derive_character_sheet().
    Pure function, no I/O, no async.

    Args:
        session_data: Session data dict (full session or inner data sub-dict).
        strict: If True, raise :class:`CharacterInputError` when the input is malformed
            (see :func:`validate_character_data`) instead of silently coercing it into a
            plausible-but-wrong sheet. Default False preserves the lenient behaviour.
        scaling: Optional :class:`ThemeScalingLayer` (e.g. ``get_theme_scaling("sci_fi")``
            or an LLM-generated layer). When given, the sheet is computed against the
            theme-scaled ruleset (re-baselined input defaults + merged lookup tables) so
            mechanical values fit the setting. ``None`` (default) uses the stock 5e ruleset.

    Returns:
        Complete character sheet dict matching the old derive_character_sheet() shape.

    Raises:
        CharacterInputError: when ``strict`` is True and the input has problems.
    """
    if strict:
        problems = validate_character_data(session_data)
        if problems:
            raise CharacterInputError(problems)

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

    # Compose any adopted item/equipment components onto the ruleset before evaluating —
    # e.g. an allocated "+1 armor_class" or "resistance to fire" item snaps its modifier onto
    # the computed sheet (each `component` is a Component, or a component_from_dict-shaped spec
    # dict as persisted on a GraphComponent). Then evaluate the (theme-scaled) computation graph.
    ruleset = _ruleset_for(scaling)
    if components:
        comps = [c if isinstance(c, Component) else component_from_dict(c) for c in components]
        ruleset = compose(ruleset, *comps)
    computed = evaluate(ruleset, inputs)

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
    *,
    scaling: ThemeScalingLayer | None = None,
) -> dict[str, dict[str, Any]]:
    """Compute before/after stat changes between two session states.

    Returns a dict of node_id → {before, after, delta, label} for stats
    that changed. Only includes KEY_STAT_NODES for readability.

    Args:
        before_data: Session data before the change.
        after_data: Session data after the change.
        scaling: Optional :class:`ThemeScalingLayer`; both states are evaluated against
            the same theme-scaled ruleset so the deltas reflect the campaign's setting.

    Returns:
        Dict of changed stats with before/after/delta/label.
    """
    ruleset = _ruleset_for(scaling)
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

    # Evaluate both (against the same themed ruleset when scaling is supplied)
    before_computed = apply_modifiers(
        evaluate(ruleset, before_inputs), before_inputs
    )
    after_computed = apply_modifiers(
        evaluate(ruleset, after_inputs), after_inputs
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


def compute_key_stats(
    session_data: dict, *, scaling: ThemeScalingLayer | None = None
) -> dict[str, Any]:
    """Compute key stats from session data for display purposes.

    Returns a flat dict of node_id → value for KEY_STAT_NODES only.
    Useful for showing baseline stats in advancement options.

    Args:
        session_data: Session data dict (full session or inner data sub-dict).
        scaling: Optional :class:`ThemeScalingLayer` to compute against a theme-scaled
            ruleset (defaults to the stock 5e ruleset).
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
        evaluate(_ruleset_for(scaling), inputs), inputs
    )

    return {
        node_id: {"value": computed.get(node_id), "label": label}
        for node_id, label in KEY_STAT_NODES.items()
        if computed.get(node_id) is not None
    }
