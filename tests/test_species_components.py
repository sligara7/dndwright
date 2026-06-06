"""The 9 SRD species, the ones with graph-mappable traits, snap on as Components.

Species exercise the resistance union channels (Dwarf poison, Dragonborn/Tiefling chosen),
a dynamic HP bump (Dwarven Toughness +1/level), and a speed override (Goliath 35).
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

SPECIES = {s["name"]: s for s in load_content("species")}
WITH_COMPONENT = [n for n, s in SPECIES.items() if s.get("component")]


def _inputs(level=8):
    return character_data_to_inputs(
        ability_scores={"strength": 14, "dexterity": 12, "constitution": 13,
                        "intelligence": 10, "wisdom": 11, "charisma": 8},
        class_data={"class_name": "fighter"}, subclass_data=None,
        species_data={"name": "Human", "speed": 30}, background_data=None, level=level,
    )


def test_nine_srd_species_bundled():
    assert set(SPECIES) == {"Dragonborn", "Dwarf", "Elf", "Gnome", "Goliath",
                            "Halfling", "Human", "Orc", "Tiefling"}
    assert set(WITH_COMPONENT) == {"Dragonborn", "Dwarf", "Goliath", "Tiefling"}


def _choices(name):
    ch = SPECIES[name].get("choices")
    return {k: v[0] for k, v in ch.items()} if ch else None


@pytest.mark.parametrize("name", WITH_COMPONENT)
def test_every_species_component_composes_cleanly(name):
    comp = component_from_content(SPECIES[name], choices=_choices(name))
    assert comp is not None
    composed = compose(R, comp)
    assert validate_ruleset(composed) == []
    evaluate(composed, _inputs())


def test_dwarf_poison_resistance_and_toughness():
    comp = component_from_content(SPECIES["Dwarf"])
    base = evaluate(R, _inputs(8))
    sheet = evaluate(compose(R, comp), _inputs(8))
    assert "poison" in sheet["resistances"]
    assert sheet["hp_max"] == base["hp_max"] + 8  # Dwarven Toughness: +1 per level, level 8


def test_goliath_speed_override():
    sheet = evaluate(compose(R, component_from_content(SPECIES["Goliath"])), _inputs())
    assert sheet["speed_base"] == 35


def test_dragonborn_chosen_ancestry_resistance():
    for ancestry in ("fire", "cold", "acid", "lightning", "poison"):
        comp = component_from_content(SPECIES["Dragonborn"], choices={"ancestry": ancestry})
        sheet = evaluate(compose(R, comp), _inputs())
        assert sheet["resistances"] == (ancestry,)


def test_tiefling_legacy_resistance():
    comp = component_from_content(SPECIES["Tiefling"], choices={"legacy": "necrotic"})
    assert "necrotic" in evaluate(compose(R, comp), _inputs())["resistances"]


def test_dragonborn_without_choice_raises():
    with pytest.raises(KeyError):  # {ancestry} unfilled — the player must choose
        component_from_content(SPECIES["Dragonborn"])


def test_narrative_species_have_no_component():
    for name in ("Elf", "Gnome", "Halfling", "Human", "Orc"):
        assert component_from_content(SPECIES[name]) is None


def test_species_damage_immunity_categorised_as_immunity():
    # Regression: damage immunities were tagged "resistance" instead of "immunity".
    from dndwright.rules.adapters import _build_species_traits

    traits = _build_species_traits(
        {"immunities": {"damage": ["fire"], "conditions": ["poisoned"]}}
    )
    by_name = {t["name"]: t["category"] for t in traits}
    assert by_name["fire Immunity"] == "immunity"
    assert by_name["poisoned Immunity"] == "immunity"
