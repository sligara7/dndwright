"""The bundled SRD class catalog — 12 classes with traits, feature progression, subclass."""

import pytest

from dndwright import load_content
from dndwright.rules.lookup_tables import get_all_lookup_tables

CLASSES = load_content("classes")
BY_NAME = {c["name"]: c for c in CLASSES}
T = get_all_lookup_tables()


def test_twelve_srd_classes():
    assert {c["name"] for c in CLASSES} == {
        "Barbarian", "Bard", "Cleric", "Druid", "Fighter", "Monk",
        "Paladin", "Ranger", "Rogue", "Sorcerer", "Warlock", "Wizard",
    }


@pytest.mark.parametrize("cls", CLASSES, ids=lambda c: c["name"])
def test_every_class_well_formed(cls):
    assert cls["description"] and cls["hit_die"].startswith("d")
    assert cls["primary_ability"]
    assert len(cls["saving_throws"]) == 2
    assert cls["skill_proficiencies"] and cls["subclass"]
    assert cls["features"] and all(1 <= f["level"] <= 20 and f["name"] for f in cls["features"])
    # no leftover line-break hyphen artifacts in the parsed box values
    for field in ("skill_proficiencies", "starting_equipment", "armor_training"):
        assert "- " not in cls[field]


def test_mechanics_match_lookup_tables():
    # the bundled class catalog must agree with the computation engine's lookup tables
    for cls in CLASSES:
        lc = cls["name"].lower()
        assert cls["hit_die"] == f"d{T['hit_die_by_class'][lc]}"
        saves = {a.lower() for a in cls["saving_throws"]}
        assert saves == set(T["save_proficiencies_by_class"][lc])
        sct = T["spellcasting_type_by_class"].get(lc, "none")
        if sct == "none":
            assert cls["spellcasting"] is None
        else:
            assert cls["spellcasting"]["type"] == sct


def test_caster_spell_list_size_matches_catalog():
    spells = load_content("spells")
    for cls in CLASSES:
        if cls["spellcasting"]:
            expected = sum(1 for s in spells if cls["name"] in s["classes"])
            assert cls["spellcasting"]["spell_list_size"] == expected


def test_spot_checks():
    assert BY_NAME["Barbarian"]["hit_die"] == "d12"
    assert BY_NAME["Barbarian"]["subclass"] == "Path of the Berserker"
    assert BY_NAME["Wizard"]["spellcasting"]["ability"] == "Intelligence"
    assert BY_NAME["Fighter"]["primary_ability"] == "Strength or Dexterity"
    assert {"name": "Rage", "level": 1} in [
        {"name": f["name"], "level": f["level"]} for f in BY_NAME["Barbarian"]["features"]
    ]
