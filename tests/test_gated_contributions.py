"""Gated (conditional) contributions: a bonus that applies only while a condition holds.

A modifier may carry a ``condition`` ({op, args} over host nodes). The contribution then
tracks the host state — Defense (+1 AC while wearing armor) and Bracers of Defense (+2 AC
while unarmored *and* shieldless) recompute as equipment changes, with no re-compose.
"""

import pytest

from dndwright import (
    DND_5E_2024_RULESET as R,
    character_data_to_inputs,
    component_from_content,
    compose,
    evaluate,
    load_content,
    validate_ruleset,
)
from dndwright.rules.operations import OPERATIONS

FEATS = {f["name"]: f for f in load_content("feats")}
ITEMS = {i["name"]: i for i in load_content("magic_items")}


def _inputs(armor=None, shield=False):
    equip = {"shield": shield}
    if armor:
        equip["armor"] = {"type": armor}
    return character_data_to_inputs(
        ability_scores={"strength": 14, "dexterity": 14, "constitution": 13,
                        "intelligence": 10, "wisdom": 11, "charisma": 8},
        class_data={"class_name": "fighter"}, subclass_data=None,
        species_data={"name": "Human", "speed": 30}, background_data=None, level=5,
        equipment=equip,
    )


def test_new_boolean_ops_registered():
    assert OPERATIONS["ne"]([1, 2], {}) is True
    assert OPERATIONS["ne"]([2, 2], {}) is False
    assert OPERATIONS["all_true"]([True, True, 1], {}) is True
    assert OPERATIONS["all_true"]([True, False], {}) is False


@pytest.mark.parametrize("armor,delta", [(None, 0), ("chain_mail", 1)])
def test_defense_only_applies_while_armored(armor, delta):
    comp = component_from_content(FEATS["Defense"])
    composed = compose(R, comp)
    assert validate_ruleset(composed) == []
    base = evaluate(R, _inputs(armor))
    gated = evaluate(composed, _inputs(armor))
    assert gated["armor_class"] == base["armor_class"] + delta


@pytest.mark.parametrize("armor,shield,delta", [
    (None, False, 2),     # unarmored, no shield -> applies
    (None, True, 0),      # shield -> gated off
    ("chain_mail", False, 0),  # armored -> gated off
])
def test_bracers_compound_gate(armor, shield, delta):
    comp = component_from_content(ITEMS["Bracers of Defense"])
    composed = compose(R, comp)
    assert validate_ruleset(composed) == []
    base = evaluate(R, _inputs(armor, shield))
    gated = evaluate(composed, _inputs(armor, shield))
    assert gated["armor_class"] == base["armor_class"] + delta


def test_one_composed_ruleset_tracks_changing_state():
    # compose once; the SAME ruleset gives different AC as equipment changes (no re-compose)
    composed = compose(R, component_from_content(FEATS["Defense"]))
    assert evaluate(composed, _inputs(None))["armor_class"] == \
        evaluate(R, _inputs(None))["armor_class"]                       # gate off, unchanged
    assert evaluate(composed, _inputs("chain_mail"))["armor_class"] == \
        evaluate(R, _inputs("chain_mail"))["armor_class"] + 1           # gate on, +1


def test_gate_compiles_to_flat_nodes():
    comp = component_from_content(ITEMS["Bracers of Defense"])
    # compound condition (all_true of eq + not) + if_then_else -> 4 internal nodes
    assert len(comp.nodes) == 4
    ops = {n.formula.op for n in comp.nodes.values()}
    assert ops == {"eq", "not", "all_true", "if_then_else"}
