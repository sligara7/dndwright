"""The bundled SRD spell catalog (data-only reference)."""

import pytest

from dndwright import load_content

SPELLS = load_content("spells")
BY_NAME = {s["name"]: s for s in SPELLS}
SCHOOLS = {"Abjuration", "Conjuration", "Divination", "Enchantment",
           "Evocation", "Illusion", "Necromancy", "Transmutation"}
CLASSES = {"Bard", "Cleric", "Druid", "Paladin", "Ranger",
           "Sorcerer", "Warlock", "Wizard"}


def test_full_srd_spell_set():
    assert len(SPELLS) == 339
    assert len({s["name"] for s in SPELLS}) == 339  # unique
    assert BY_NAME["Acid Arrow"] and BY_NAME["Wish"] and BY_NAME["Zone of Truth"]


@pytest.mark.parametrize("spell", SPELLS, ids=lambda s: s["name"])
def test_every_spell_well_formed(spell):
    assert spell["name"] and spell["name"][0].isupper()
    assert spell["school"] in SCHOOLS
    assert 0 <= spell["level"] <= 9
    for field in ("casting_time", "range", "components", "duration", "description"):
        assert spell[field], f"{spell['name']} missing {field}"
    assert spell["classes"] and set(spell["classes"]) <= CLASSES
    assert "System Reference" not in spell["description"]  # no page-marker artifacts


def test_level_distribution():
    dist = {lvl: sum(1 for s in SPELLS if s["level"] == lvl) for lvl in range(10)}
    assert dist[0] == 27  # cantrips
    assert sum(dist.values()) == 339


def test_spot_checks():
    fireball = BY_NAME["Fireball"]
    assert fireball["level"] == 3 and fireball["school"] == "Evocation"
    assert fireball["range"] == "150 feet"
    assert set(fireball["classes"]) == {"Sorcerer", "Wizard"}
    # a reaction spell keeps its full trigger clause in casting_time
    assert "Reaction" in BY_NAME["Shield"]["casting_time"]
    # a cantrip is level 0
    assert BY_NAME["Acid Splash"]["level"] == 0
