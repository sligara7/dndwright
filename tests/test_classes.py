"""The bundled SRD class catalog — 12 classes with traits, feature progression, subclass."""

import re

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


def _feature_entries(cls):
    return cls["features"] + cls["subclass_features"]


@pytest.mark.parametrize("cls", CLASSES, ids=lambda c: c["name"])
def test_features_and_subclass_features_have_clean_descriptions(cls):
    # every class feature now carries SRD prose, and the SRD subclass has its own progression
    assert cls["subclass_features"]
    for f in cls["subclass_features"]:
        assert 1 <= f["level"] <= 20 and f["name"]
    for f in _feature_entries(cls):
        desc = f.get("description", "")
        assert len(desc) >= 15, f"{cls['name']} {f['name']}: missing/short description"
        # no extraction artifacts: page footer, interleaved table cells, broken hyphenation
        assert "System Reference" not in desc
        assert not re.search(r"\b\d+ \+\d+ \d+\b", desc), f"{cls['name']} {f['name']}: table cells"
        assert "  " not in desc and "- " not in desc


def test_feature_prose_spot_checks():
    rage = next(f for f in BY_NAME["Barbarian"]["features"] if f["name"] == "Rage")
    assert "Resistance to Bludgeoning, Piercing, and Slashing" in rage["description"]
    champion = next(f for f in BY_NAME["Fighter"]["subclass_features"]
                    if f["name"] == "Improved Critical")
    assert "Critical Hit on a roll of 19 or 20" in champion["description"]
    # the option-catalog over-capture is trimmed, not absorbed into the last feature
    assert len(next(f for f in BY_NAME["Warlock"]["features"]
                    if f["name"] == "Eldritch Master")["description"]) < 300


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
