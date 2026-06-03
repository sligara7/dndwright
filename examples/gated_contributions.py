"""Gated legos: a contribution that applies only while a condition holds.

    python examples/gated_contributions.py

Some bonuses are conditional — Defense (+1 AC *while wearing armor*), Bracers of Defense
(+2 AC *while unarmored and shieldless*). A modifier carries a `condition` (a formula over
host nodes); compose it once and the bonus tracks the character's equipment automatically.
"""

from dndwright import (
    DND_5E_2024_RULESET,
    character_data_to_inputs,
    component_from_content,
    compose,
    evaluate,
    load_content,
)

feats = {f["name"]: f for f in load_content("feats")}
items = {i["name"]: i for i in load_content("magic_items")}


def inputs(armor=None, shield=False):
    equip = {"shield": shield}
    if armor:
        equip["armor"] = {"type": armor}
    return character_data_to_inputs(
        ability_scores={"strength": 14, "dexterity": 14, "constitution": 13,
                        "intelligence": 10, "wisdom": 11, "charisma": 8},
        class_data={"class_name": "fighter"}, subclass_data=None,
        species_data={"name": "Human", "speed": 30}, background_data=None, level=5,
        equipment=equip,
    )


# Compose each ONCE, then read AC across changing equipment — the gate re-evaluates.
defense = compose(DND_5E_2024_RULESET, component_from_content(feats["Defense"]))
bracers = compose(DND_5E_2024_RULESET, component_from_content(items["Bracers of Defense"]))

print("Defense fighting style — +1 AC only while wearing armor:")
for armor in (None, "chain_mail"):
    ac = evaluate(defense, inputs(armor))["armor_class"]
    print(f"  armor={str(armor):12} AC {ac}")

print("\nBracers of Defense — +2 AC only while unarmored AND shieldless:")
for armor, shield in [(None, False), (None, True), ("chain_mail", False)]:
    ac = evaluate(bracers, inputs(armor, shield))["armor_class"]
    print(f"  armor={str(armor):12} shield={str(shield):5} AC {ac}")
