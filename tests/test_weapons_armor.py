"""The bundled SRD weapon + armor tables — and their agreement with the rules lookups."""

import pytest

from dndwright import load_content
from dndwright.rules.lookup_tables import get_all_lookup_tables

WEAPONS = load_content("weapons")
ARMOR = load_content("armor")
T = get_all_lookup_tables()
MASTERIES = {"Slow", "Nick", "Push", "Vex", "Sap", "Topple", "Graze", "Cleave"}
DMG_TYPES = {"Bludgeoning", "Piercing", "Slashing"}


# --- weapons ----------------------------------------------------------------

def test_weapon_count_and_categories():
    assert len(WEAPONS) == 38
    cats = {(w["category"], w["kind"]) for w in WEAPONS}
    assert cats == {("Simple", "Melee"), ("Simple", "Ranged"),
                    ("Martial", "Melee"), ("Martial", "Ranged")}


@pytest.mark.parametrize("w", WEAPONS, ids=lambda w: w["name"])
def test_every_weapon_well_formed(w):
    assert w["category"] in {"Simple", "Martial"} and w["kind"] in {"Melee", "Ranged"}
    assert w["damage_type"] in DMG_TYPES
    assert w["mastery"] in MASTERIES
    assert isinstance(w["properties"], list)
    assert w["weight"] and w["cost"]


def test_weapon_mastery_agrees_with_lookup():
    mm = T["weapon_mastery_map"]
    for w in WEAPONS:
        key = w["name"].lower()
        if key in mm:
            assert w["mastery"] == mm[key], f"{w['name']} mastery {w['mastery']} != {mm[key]}"


def test_weapon_spot_checks():
    by = {w["name"]: w for w in WEAPONS}
    assert by["Greatsword"]["damage_dice"] == "2d6" and by["Greatsword"]["mastery"] == "Graze"
    assert "Finesse" in by["Dagger"]["properties"] and "Light" in by["Dagger"]["properties"]
    assert by["Longbow"]["category"] == "Martial" and by["Longbow"]["kind"] == "Ranged"


# --- armor ------------------------------------------------------------------

def test_armor_count_and_categories():
    assert len(ARMOR) == 13
    assert {a["category"] for a in ARMOR} == {"Light", "Medium", "Heavy", "Shield"}


@pytest.mark.parametrize("a", ARMOR, ids=lambda a: a["name"])
def test_every_armor_well_formed(a):
    assert a["category"] in {"Light", "Medium", "Heavy", "Shield"}
    assert a["weight"] and a["cost"]
    if a["category"] == "Shield":
        assert a["base_ac"] is None and a["ac_bonus"] == 2
    else:
        assert isinstance(a["base_ac"], int)


def test_armor_ac_agrees_with_lookup():
    ab = T["armor_base_ac"]
    for a in ARMOR:
        if a["category"] == "Shield":
            continue
        key = a["name"].lower().replace(" armor", "").strip()
        if key in ab:
            assert a["base_ac"] == ab[key], f"{a['name']} AC {a['base_ac']} != {ab[key]}"


def test_armor_spot_checks():
    by = {a["name"]: a for a in ARMOR}
    assert by["Chain Mail"]["base_ac"] == 16 and by["Chain Mail"]["strength_requirement"] == 13
    assert by["Chain Mail"]["stealth_disadvantage"] is True
    assert by["Plate Armor"]["base_ac"] == 18
    assert by["Hide Armor"]["dex_cap"] == 2 and by["Hide Armor"]["adds_dex"] is True
