"""Bundled SRD feats, the ones with graph-mappable effects, snap on as Components.

Feats exercise two things items don't: a *dynamic* contribution (Alert adds the
proficiency bonus, which scales with level) and a *parameterised* one (the ability a feat
boosts is the player's choice, expressed as a ``{placeholder}``).
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

FEATS = {f["name"]: f for f in load_content("feats")}
WITH_COMPONENT = [n for n, f in FEATS.items() if f.get("component")]


def _inputs(level=8):
    return character_data_to_inputs(
        ability_scores={"strength": 15, "dexterity": 14, "constitution": 13,
                        "intelligence": 10, "wisdom": 11, "charisma": 8},
        class_data={"class_name": "fighter"}, subclass_data=None,
        species_data={"name": "Human", "speed": 30}, background_data=None, level=level,
    )


def test_feats_category_is_registered():
    from dndwright import categories
    assert "feats" in categories()
    assert len(FEATS) == 16  # the SRD 5.2.1 feat set
    assert {"Alert", "Ability Score Improvement", "Grappler"} <= set(WITH_COMPONENT)


def _choices(feat):
    ch = feat.get("choices")
    return {k: v[0] for k, v in ch.items()} if ch else None


@pytest.mark.parametrize("name", WITH_COMPONENT)
def test_every_feat_component_targets_real_nodes_and_composes(name):
    comp = component_from_content(FEATS[name], choices=_choices(FEATS[name]))
    assert comp is not None and "." not in comp.id
    for c in comp.contributions:
        assert c.target in R.nodes, f"{name}: target {c.target!r} not in ruleset"
    composed = compose(R, comp)
    assert validate_ruleset(composed) == []
    evaluate(composed, _inputs())


def test_alert_adds_proficiency_bonus_to_initiative_and_scales():
    alert = component_from_content(FEATS["Alert"])
    for level in (1, 8, 20):
        base = evaluate(R, _inputs(level))
        sheet = evaluate(compose(R, alert), _inputs(level))
        assert sheet["initiative"] == base["initiative"] + base["proficiency_bonus"]


def test_grappler_boosts_chosen_ability_only():
    base = evaluate(R, _inputs())
    s_str = evaluate(compose(R, component_from_content(FEATS["Grappler"], choices={"ability": "strength"})), _inputs())
    assert s_str["strength_score"] == base["strength_score"] + 1
    assert s_str["dexterity_score"] == base["dexterity_score"]
    s_dex = evaluate(compose(R, component_from_content(FEATS["Grappler"], choices={"ability": "dexterity"})), _inputs())
    assert s_dex["dexterity_score"] == base["dexterity_score"] + 1
    assert s_dex["strength_score"] == base["strength_score"]


def test_asi_plus_two_cascades_to_modifier():
    base = evaluate(R, _inputs())
    asi = component_from_content(FEATS["Ability Score Improvement"], choices={"ability": "strength"})
    sheet = evaluate(compose(R, asi), _inputs())
    assert sheet["strength_score"] == base["strength_score"] + 2
    assert sheet["strength_mod"] == (base["strength_score"] + 2 - 10) // 2


def test_two_choices_of_same_feat_do_not_collide():
    # Grappler is repeatable-ish here only as a compose test: +1 STR and +1 DEX as two components
    g_str = component_from_content(FEATS["Grappler"], choices={"ability": "strength"})
    g_dex = component_from_content(FEATS["Grappler"], choices={"ability": "dexterity"})
    assert g_str.id != g_dex.id  # distinct ids -> no namespace clash
    base = evaluate(R, _inputs())
    sheet = evaluate(compose(R, g_str, g_dex), _inputs())
    assert sheet["strength_score"] == base["strength_score"] + 1
    assert sheet["dexterity_score"] == base["dexterity_score"] + 1


def test_missing_choice_raises():
    with pytest.raises(KeyError):
        component_from_content(FEATS["Grappler"])  # {ability} unfilled


def test_narrative_feat_has_no_component():
    assert component_from_content(FEATS["Savage Attacker"]) is None
