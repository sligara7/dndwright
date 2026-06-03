"""0.13.0 integration surface: damage-defence channels, Component (de)serialisation,
and combatant_defenses() — the seams storyflow consumes to persist components and feed
the composed resistances/immunities/vulnerabilities into combat.
"""

from dndwright import (
    COMPONENT_SCHEMA_VERSION,
    DAMAGE_CHANNELS,
    DND_5E_2024_RULESET as R,
    IMMUNITIES_NODE,
    RESISTANCES_NODE,
    VULNERABILITIES_NODE,
    character_data_to_inputs,
    component_from_content,
    component_from_dict,
    component_to_dict,
    compose,
    evaluate,
    modifier,
    validate_ruleset,
)
from dndwright.combat import CombatantState, apply_damage, combatant_defenses


def _inputs():
    return character_data_to_inputs(
        ability_scores={"strength": 14, "dexterity": 12, "constitution": 13,
                        "intelligence": 10, "wisdom": 11, "charisma": 8},
        class_data={"class_name": "fighter"}, subclass_data=None,
        species_data={"name": "Human", "speed": 30}, background_data=None, level=5,
    )


# --- channels ---------------------------------------------------------------

def test_channels_bundled_and_empty_by_default():
    assert DAMAGE_CHANNELS == (RESISTANCES_NODE, IMMUNITIES_NODE, VULNERABILITIES_NODE)
    for ch in DAMAGE_CHANNELS:
        assert ch in R.nodes
    sheet = evaluate(R, _inputs())
    for ch in DAMAGE_CHANNELS:
        assert sheet[ch] == ()  # always present, empty until a component contributes


def test_union_components_populate_channels():
    ring = component_from_content({"name": "Ring of Resistance (Fire)",
        "component": [{"target": "resistances", "mode": "union", "amount": ["fire"]}]})
    poison = modifier("dwarf_resilience", target="resistances", amount=["poison"], mode="union")
    immune = modifier("golem_immunity", target="immunities", amount=["poison"], mode="union")
    composed = compose(R, ring, poison, immune)
    assert validate_ruleset(composed) == []
    sheet = evaluate(composed, _inputs())
    assert set(sheet["resistances"]) == {"fire", "poison"}
    assert set(sheet["immunities"]) == {"poison"}
    assert sheet["vulnerabilities"] == ()


# --- serialisation ----------------------------------------------------------

def test_component_dict_round_trip_and_version_stamp():
    comp = component_from_content({"name": "Gauntlets of Ogre Power",
        "component": [{"target": "strength_score", "amount": 19, "mode": "set"}]})
    data = component_to_dict(comp)
    assert data["_schema_version"] == COMPONENT_SCHEMA_VERSION
    rebuilt = component_from_dict(data)
    assert rebuilt.model_dump() == comp.model_dump()


def test_from_dict_tolerates_missing_version():
    comp = modifier("x", target="armor_class", amount=1)
    raw = comp.model_dump(mode="json")  # no _schema_version key
    assert component_from_dict(raw).model_dump() == comp.model_dump()


def test_rebuilt_component_still_composes():
    comp = component_from_content({"name": "Ring of Resistance (Cold)",
        "component": [{"target": "resistances", "mode": "union", "amount": ["cold"]}]})
    rebuilt = component_from_dict(component_to_dict(comp))
    sheet = evaluate(compose(R, rebuilt), _inputs())
    assert set(sheet["resistances"]) == {"cold"}


# --- combatant_defenses -> combat ------------------------------------------

def test_combatant_defenses_extracts_and_filters():
    composed = compose(
        R,
        modifier("r", target="resistances", amount=["fire", "COLD"], mode="union"),
        modifier("junk", target="resistances", amount=["Fire Resistance"], mode="union"),
    )
    sheet = evaluate(composed, _inputs())
    defenses = combatant_defenses(sheet)
    # lowercased + intersected with DAMAGE_TYPES, so "Fire Resistance" junk is dropped
    assert defenses["resistances"] == frozenset({"fire", "cold"})
    assert defenses["immunities"] == frozenset()


def test_defenses_feed_apply_damage_multiplier():
    sheet = evaluate(compose(R, modifier("r", target="resistances", amount=["fire"], mode="union")), _inputs())
    state = CombatantState(current_hp=20, max_hp=20, **combatant_defenses(sheet))
    resisted, applied = apply_damage(state, 10, damage_type="fire")
    assert resisted.current_hp == 15 and applied.multiplier == 0.5
    normal, applied2 = apply_damage(state, 10, damage_type="cold")
    assert normal.current_hp == 10 and applied2.multiplier == 1.0


def test_empty_defenses_on_plain_character():
    assert combatant_defenses(evaluate(R, _inputs())) == {
        "resistances": frozenset(), "immunities": frozenset(), "vulnerabilities": frozenset(),
    }
