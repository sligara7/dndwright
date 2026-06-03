"""Bundled magic items carry their mechanical effect as a composable Component.

These tests pin the content-as-data contract: an item's ``component`` field expands to a
real :class:`Component`, every contribution targets a node that exists in the shipped
ruleset, and snapping items on cascades through the character graph.
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

ITEMS = {i["name"]: i for i in load_content("magic_items")}
WITH_COMPONENT = [name for name, i in ITEMS.items() if i.get("component")]


def _inputs():
    return character_data_to_inputs(
        ability_scores={"strength": 14, "dexterity": 12, "constitution": 13,
                        "intelligence": 10, "wisdom": 11, "charisma": 8},
        class_data={"class_name": "fighter"}, subclass_data=None,
        species_data={"name": "Human", "speed": 30}, background_data=None, level=5,
    )


def test_some_items_carry_a_component():
    # the curated set is bundled; don't pin the exact count (more may be added)
    assert "Gauntlets of Ogre Power" in WITH_COMPONENT
    assert len(WITH_COMPONENT) >= 6


def test_narrative_item_has_no_component():
    assert component_from_content(ITEMS["Adamantine Armor"]) is None
    assert component_from_content({"name": "Plain"}) is None


@pytest.mark.parametrize("name", WITH_COMPONENT)
def test_every_contribution_targets_a_real_node(name):
    comp = component_from_content(ITEMS[name])
    assert comp is not None
    # id is dot-free (dots namespace component-local nodes), and every target exists
    assert "." not in comp.id
    for c in comp.contributions:
        assert c.target in R.nodes, f"{name}: target {c.target!r} not in ruleset"
        assert c.mode in ("add", "set", "union")


@pytest.mark.parametrize("name", WITH_COMPONENT)
def test_each_item_composes_without_cycles(name):
    comp = component_from_content(ITEMS[name])
    composed = compose(R, comp)
    assert validate_ruleset(composed) == []
    evaluate(composed, _inputs())  # evaluates cleanly


def test_gauntlets_set_strength_cascades():
    comp = component_from_content(ITEMS["Gauntlets of Ogre Power"])
    sheet = evaluate(compose(R, comp), _inputs())
    assert sheet["strength_score"] == 19          # set 14 -> 19
    assert sheet["strength_mod"] == 4             # cascaded
    assert sheet["save.strength.bonus"] == 4 + sheet["proficiency_bonus"]


def test_cloak_adds_one_to_ac_and_all_saves():
    base = evaluate(R, _inputs())
    sheet = evaluate(compose(R, component_from_content(ITEMS["Cloak of Protection"])), _inputs())
    assert sheet["armor_class"] == base["armor_class"] + 1
    for ab in ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"):
        assert sheet[f"save.{ab}.bonus"] == base[f"save.{ab}.bonus"] + 1


def test_items_stack_like_legos():
    comps = [component_from_content(ITEMS[n]) for n in
             ("Gauntlets of Ogre Power", "Amulet of Health", "Cloak of Protection")]
    base = evaluate(R, _inputs())
    sheet = evaluate(compose(R, *comps), _inputs())
    assert sheet["strength_score"] == 19
    assert sheet["constitution_score"] == 19
    assert sheet["armor_class"] == base["armor_class"] + 1
    # base ruleset is untouched
    assert R.nodes["strength_score"].node_type.value == "input"


def test_belt_of_dwarvenkind_adds_constitution():
    base = evaluate(R, _inputs())
    sheet = evaluate(compose(R, component_from_content(ITEMS["Belt of Dwarvenkind"])), _inputs())
    assert sheet["constitution_score"] == base["constitution_score"] + 2


def test_component_metadata_carries_rarity():
    comp = component_from_content(ITEMS["Gauntlets of Ogre Power"])
    assert comp.metadata["rarity"] == ITEMS["Gauntlets of Ogre Power"]["rarity"]
    assert comp.metadata["source"] == "srd_magic_item"
