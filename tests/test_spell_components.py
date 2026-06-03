"""Curated SRD spells carry their mechanical effect as a composable Component.

A spell whose effect maps onto the character graph (today: the AC-affecting spells)
ships a ``component`` field — the same content-as-data contract magic items use.
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

SPELLS = {s["name"]: s for s in load_content("spells")}
WITH_COMPONENT = [name for name, s in SPELLS.items() if s.get("component")]


def _inputs(armor_type="none", dex=14):
    inp = character_data_to_inputs(
        ability_scores={"strength": 12, "dexterity": dex, "constitution": 13,
                        "intelligence": 10, "wisdom": 11, "charisma": 8},
        class_data={"class_name": "wizard"}, subclass_data=None,
        species_data={"name": "Human", "speed": 30}, background_data=None, level=3,
    )
    inp["armor_type"] = armor_type
    return inp


def test_curated_ac_spells_carry_components():
    assert set(WITH_COMPONENT) == {"Mage Armor", "Shield of Faith", "Shield"}


def test_reference_only_spell_has_no_component():
    assert component_from_content(SPELLS["Fireball"]) is None
    assert component_from_content(SPELLS["Bless"]) is None  # no generic attack/save node yet


@pytest.mark.parametrize("name", WITH_COMPONENT)
def test_every_contribution_targets_a_real_node(name):
    comp = component_from_content(SPELLS[name])
    assert comp is not None and "." not in comp.id
    for c in comp.contributions:
        assert c.target in R.nodes, f"{name}: target {c.target!r} not in ruleset"
        assert c.mode in ("add", "set", "union")


@pytest.mark.parametrize("name", WITH_COMPONENT)
def test_each_spell_composes_without_cycles(name):
    composed = compose(R, component_from_content(SPELLS[name]))
    assert validate_ruleset(composed) == []
    evaluate(composed, _inputs())


def test_flat_ac_bonuses():
    base = evaluate(R, _inputs())["armor_class"]            # 10 + DEX 2 = 12
    assert base == 12
    sof = evaluate(compose(R, component_from_content(SPELLS["Shield of Faith"])), _inputs())
    assert sof["armor_class"] == base + 2
    shield = evaluate(compose(R, component_from_content(SPELLS["Shield"])), _inputs())
    assert shield["armor_class"] == base + 5


def test_mage_armor_is_gated_on_being_unarmored():
    comp = component_from_content(SPELLS["Mage Armor"])
    # unarmored: 10 + DEX -> 13 + DEX (a flat +3)
    unarmored = evaluate(compose(R, comp), _inputs(armor_type="none"))
    assert unarmored["armor_class"] == 13 + 2
    # wearing armor: Mage Armor contributes nothing (the gate is false)
    armored_base = evaluate(R, _inputs(armor_type="leather"))["armor_class"]
    armored_spell = evaluate(compose(R, comp), _inputs(armor_type="leather"))["armor_class"]
    assert armored_spell == armored_base
