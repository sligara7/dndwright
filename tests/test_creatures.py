"""The bundled SRD bestiary — the full Monsters A–Z stat-block catalog."""

import pytest

from dndwright import load_content

CREATURES = load_content("creatures")
BY_NAME = {c["name"]: c for c in CREATURES}

SIZES = {"Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"}
TYPES = {"aberration", "beast", "celestial", "construct", "dragon", "elemental",
         "fey", "fiend", "giant", "humanoid", "monstrosity", "ooze", "plant", "undead"}
ABILITIES = {"str", "dex", "con", "int", "wis", "cha"}
DAMAGE_TYPES = {"acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic",
                "piercing", "poison", "psychic", "radiant", "slashing", "thunder"}
CONDITIONS = {"blinded", "charmed", "deafened", "exhaustion", "frightened", "grappled",
              "incapacitated", "invisible", "paralyzed", "petrified", "poisoned",
              "prone", "restrained", "stunned", "unconscious"}
FRAC = {"0": 0.0, "1/8": 0.125, "1/4": 0.25, "1/2": 0.5}
SECTIONS = ("traits", "actions", "bonus_actions", "reactions", "legendary_actions")


def test_full_srd_bestiary():
    assert len(CREATURES) >= 300
    assert len(BY_NAME) == len(CREATURES)            # names are unique
    assert BY_NAME["Aboleth"] and BY_NAME["Tarrasque"] and BY_NAME["Goblin Warrior"]


@pytest.mark.parametrize("c", CREATURES, ids=lambda c: c["name"])
def test_every_creature_well_formed(c):
    assert c["name"] and c["name"][0].isupper()
    assert c["size"] in SIZES
    assert c["creature_type"] in TYPES
    assert c["alignment"]
    assert isinstance(c["ac"], int) and c["ac"] > 0
    assert isinstance(c["hp"], int) and c["hp"] > 0
    assert c["hp_formula"]
    # speed: a dict of mode -> feet (+ optional hover flag), walk always present
    assert isinstance(c["speed"], dict) and "walk" in c["speed"]
    # all six ability scores, in range
    assert set(c["abilities"]) == ABILITIES
    assert all(1 <= v <= 30 for v in c["abilities"].values())
    # challenge rating + derived numeric agree
    assert c["cr"]
    assert c["cr_numeric"] == FRAC[c["cr"]] if c["cr"] in FRAC else c["cr_numeric"] == float(c["cr"])
    assert isinstance(c["xp"], int) and c["xp"] >= 0
    assert isinstance(c["proficiency_bonus"], int) and c["proficiency_bonus"] >= 2
    assert isinstance(c["languages"], list)
    # at least one of traits/actions/reactions (every stat block does something)
    assert any(c.get(s) for s in SECTIONS)
    # no extraction artifacts anywhere in the entry
    blob = repr(c)
    assert "System Reference" not in blob
    assert "Monsters A" not in blob
    assert "- " not in blob                          # leftover line-break hyphens


@pytest.mark.parametrize("c", CREATURES, ids=lambda c: c["name"])
def test_optional_fields_well_typed(c):
    for ab in c.get("saving_throws", {}):
        assert ab in ABILITIES
    assert all(isinstance(v, int) for v in c.get("skills", {}).values())
    senses = c.get("senses", {})
    assert all(isinstance(v, int) for v in senses.values())
    for t in c.get("damage_resistances", []) + c.get("damage_vulnerabilities", []):
        assert isinstance(t, str) and t
    # immunities are classified into the right bucket
    for t in c.get("condition_immunities", []):
        assert t.split(" (")[0].lower() in CONDITIONS
    # structured sections: every entry has a name + text
    for sect in SECTIONS:
        for e in c.get(sect, []):
            assert e["name"] and e["text"]
            if "attack_bonus" in e:
                assert isinstance(e["attack_bonus"], int)
            if "save_dc" in e:
                assert isinstance(e["save_dc"], int) and e["save_ability"] in ABILITIES
            for d in e.get("damage", []):
                assert d["dice"] and d["type"] in DAMAGE_TYPES


def test_cr_distribution():
    crs = [c["cr_numeric"] for c in CREATURES]
    assert min(crs) == 0.0 and max(crs) == 30.0       # Commoner .. Tarrasque
    assert sum(1 for x in crs if x < 1) >= 50          # plenty of low-CR fodder


def test_spot_checks():
    abo = BY_NAME["Aboleth"]
    assert abo["cr"] == "10" and abo["xp"] == 5900 and abo["xp_lair"] == 7200
    assert abo["ac"] == 17 and abo["hp"] == 150 and abo["creature_type"] == "aberration"
    assert abo["saving_throws"]["con"] == 6 and "Deep Speech" in abo["languages"]
    assert abo["legendary_actions"] and any(a["name"] == "Lash" for a in abo["legendary_actions"])

    tarr = BY_NAME["Tarrasque"]
    assert tarr["cr"] == "30" and tarr["size"] == "Gargantuan"
    assert "fire" in [t.lower() for t in tarr["damage_immunities"]]

    # a melee attacker's mechanics are parsed out of the prose
    bite = next(a for a in BY_NAME["Adult Red Dragon"]["actions"] if a["name"] == "Rend")
    assert bite["attack_bonus"] == 14 and bite["reach"] == "10 ft."
    assert any(d["type"] == "fire" for d in bite["damage"])

    # a swarm lists condition immunities (no damage immunities)
    swarm = BY_NAME["Swarm of Rats"]
    assert "Charmed" in swarm["condition_immunities"]
    assert not swarm.get("damage_immunities")
