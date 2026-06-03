"""The bundled SRD background catalog (4 backgrounds)."""

import re

from dndwright import load_content

BACKGROUNDS = load_content("backgrounds")
BY_NAME = {b["name"]: b for b in BACKGROUNDS}
ABILITIES = {"Strength", "Dexterity", "Constitution",
             "Intelligence", "Wisdom", "Charisma"}


def test_four_srd_backgrounds():
    assert set(BY_NAME) == {"Acolyte", "Criminal", "Sage", "Soldier"}


def test_every_background_well_formed():
    feat_names = {f["name"] for f in load_content("feats")}
    for b in BACKGROUNDS:
        assert len(b["ability_scores"]) == 3
        assert set(b["ability_scores"]) <= ABILITIES
        assert len(b["skill_proficiencies"]) == 2
        assert b["tool_proficiency"] and b["equipment"] and b["feat"]
        # the granted Origin feat resolves to a bundled SRD feat (base name, sans parenthetical)
        base = re.sub(r"\s*\(.*\)", "", b["feat"]).strip()
        assert base in feat_names, f"{b['name']} feat {base!r} not in feats catalog"
        assert "- " not in b["equipment"]  # no line-break hyphen artifacts


def test_spot_checks():
    assert BY_NAME["Acolyte"]["ability_scores"] == ["Intelligence", "Wisdom", "Charisma"]
    assert BY_NAME["Acolyte"]["feat"] == "Magic Initiate (Cleric)"
    assert BY_NAME["Criminal"]["feat"] == "Alert"
    assert BY_NAME["Soldier"]["skill_proficiencies"] == ["Athletics", "Intimidation"]
