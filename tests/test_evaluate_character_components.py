"""evaluate_character(..., components=[...]) — compose allocated item modifiers onto the sheet.

Covers the v0.26 `components` kwarg: an allocated item's dndwright Component (or a
component_from_dict-shaped spec dict, as persisted on a storyflow GraphComponent) is composed
onto the ruleset before evaluation, so its modifier lands on the computed sheet. `None`/[]
is a pure no-op (default behaviour unchanged).
"""

from dndwright.rules.character_evaluator import evaluate_character
from dndwright.rules.compose import (
    Component,
    component_from_content,
    component_to_dict,
    modifier,
)

# Wizard, DEX 14 (+2) → unarmored AC 12; deterministic base.
CHAR = {
    "ability_scores": {"strength": 8, "dexterity": 14, "constitution": 14,
                       "intelligence": 18, "wisdom": 12, "charisma": 10},
    "class_data": {"class_name": "wizard"},
    "species_data": {"name": "Human", "speed": 30},
    "level": 5,
}


def _plus1_ac() -> Component:
    return component_from_content({"component": [{"target": "armor_class", "mode": "add", "amount": 1}]})


def test_no_components_is_a_noop():
    assert evaluate_character(CHAR) == evaluate_character(CHAR, components=None)
    assert evaluate_character(CHAR) == evaluate_character(CHAR, components=[])


def test_plus1_ac_component_object_composes():
    base = evaluate_character(CHAR)["armor_class"]
    composed = evaluate_character(CHAR, components=[_plus1_ac()])["armor_class"]
    assert composed == base + 1, f"expected +1 AC ({base + 1}), got {composed}"


def test_plus1_ac_serialized_dict_composes():
    """A component_to_dict-round-tripped spec (as stored on a GraphComponent) composes too."""
    base = evaluate_character(CHAR)["armor_class"]
    spec = component_to_dict(_plus1_ac())
    composed = evaluate_character(CHAR, components=[spec])["armor_class"]
    assert composed == base + 1, f"expected +1 AC ({base + 1}) from serialized spec, got {composed}"


def test_two_unique_ac_items_stack():
    """Two DISTINCT-id AC items stack (+1 +1 = +2). Item components MUST carry unique ids —
    dndwright namespaces each component's nodes by ``component.id``, so two components sharing
    an id (e.g. the ``component_from_content`` default ``"item"``) collide and cross-contaminate.
    storyflow uses each owned GraphComponent's unique node id, so real allocations are safe."""
    base = evaluate_character(CHAR)["armor_class"]
    comps = [
        modifier("shield_of_vantor", target="armor_class", amount=1),
        modifier("ring_of_protection", target="armor_class", amount=1),
    ]
    composed = evaluate_character(CHAR, components=comps)["armor_class"]
    assert composed == base + 2, f"two +1-AC items should stack to +2 ({base + 2}), got {composed}"


# SCOPE NOTE (inc-4 v1): item components compose onto the computed graph, but only targets the
# character-sheet reshape reads from computed NODES surface on the sheet — confirmed: `armor_class`
# and `initiative` do; `hp_max`/`speed`/ability-scores/`resistances` compose the node but the
# reshape reads those from input/other keys, so they don't yet surface. inc-4 targets AC (the
# "+1 shield → +1 AC" headline). Ability-score-setting + resistance items (sheet-reshape to read
# composed values) are a tracked dndwright follow-up in the items workstream.
