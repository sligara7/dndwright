"""Each SRD background's ability increases ship as a parameterized Component.

The 2024 background ASI is player-allocated, so the ``component`` is a template with
``{plus_two}`` / ``{plus_one}`` placeholders filled from ``choices`` at compose time —
the same content-as-data pattern the Ability Score Improvement feat uses.
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

BACKGROUNDS = {b["name"]: b for b in load_content("backgrounds")}


def _inputs():
    return character_data_to_inputs(
        ability_scores=dict.fromkeys(
            ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"), 10),
        class_data={"class_name": "cleric"}, subclass_data=None,
        species_data={"name": "Human", "speed": 30}, background_data=None, level=1,
    )


def _pick(bg):
    """A valid +2/+1 choice from a background's three abilities."""
    abils = bg["choices"]["plus_two"]
    return {"plus_two": abils[0], "plus_one": abils[1]}


def test_every_background_carries_a_parameterized_component():
    for b in BACKGROUNDS.values():
        assert b["component"] and b["choices"]
        # placeholders only allow this background's own three abilities
        own = {a.lower() for a in b["ability_scores"]}
        assert set(b["choices"]["plus_two"]) == own
        assert set(b["choices"]["plus_one"]) == own


@pytest.mark.parametrize("name", list(BACKGROUNDS))
def test_component_targets_real_nodes_and_composes(name):
    bg = BACKGROUNDS[name]
    comp = component_from_content(bg, choices=_pick(bg))
    assert comp is not None and "." not in comp.id
    for c in comp.contributions:
        assert c.target in R.nodes, f"{name}: target {c.target!r} not in ruleset"
    composed = compose(R, comp)
    assert validate_ruleset(composed) == []
    evaluate(composed, _inputs())


def test_applies_the_two_one_spread():
    bg = BACKGROUNDS["Acolyte"]            # Int / Wis / Cha
    comp = component_from_content(bg, choices={"plus_two": "wisdom", "plus_one": "charisma"})
    s = evaluate(compose(R, comp), _inputs())
    assert s["wisdom_score"] == 12 and s["charisma_score"] == 11
    assert s["intelligence_score"] == 10  # untouched


def test_distinct_choices_do_not_collide_when_stacked():
    acolyte = component_from_content(BACKGROUNDS["Acolyte"],
                                     choices={"plus_two": "wisdom", "plus_one": "charisma"})
    soldier = component_from_content(BACKGROUNDS["Soldier"],
                                     choices={"plus_two": "strength", "plus_one": "dexterity"})
    assert acolyte.id != soldier.id        # cid encodes the choice
    s = evaluate(compose(R, acolyte, soldier), _inputs())
    assert s["wisdom_score"] == 12 and s["strength_score"] == 12 and s["dexterity_score"] == 11


def test_unfilled_placeholder_raises():
    with pytest.raises(KeyError):
        component_from_content(BACKGROUNDS["Acolyte"])  # no choices -> {plus_two} unfilled
