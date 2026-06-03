"""Bundled magic items as legos: snap SRD items onto a character — stats cascade.

    python examples/content_components.py

Each item in the bundled ``magic_items`` content can carry its mechanical effect *as
data* (a ``component`` field). ``component_from_content`` turns that into a Component;
``compose`` snaps it onto the character graph and every downstream value recomputes.
"""

from dndwright import (
    DND_5E_2024_RULESET,
    character_data_to_inputs,
    component_from_content,
    compose,
    evaluate,
    load_content,
)

items = {i["name"]: i for i in load_content("magic_items")}

inputs = character_data_to_inputs(
    ability_scores={"strength": 14, "dexterity": 12, "constitution": 13,
                    "intelligence": 10, "wisdom": 11, "charisma": 8},
    class_data={"class_name": "fighter"}, subclass_data=None,
    species_data={"name": "Human", "speed": 30}, background_data=None, level=5,
)


def show(label, sheet):
    print(f"{label:28} STR {sheet['strength_score']:>2}  CON {sheet['constitution_score']:>2}  "
          f"AC {sheet['armor_class']:>2}  save(wis) {sheet['save.wisdom.bonus']:+d}")


print("Items that carry a mechanical component:")
for name in sorted(n for n, i in items.items() if i.get("component")):
    print(f"  • {name} ({items[name]['rarity']})")
print()

show("base fighter", evaluate(DND_5E_2024_RULESET, inputs))

# Equip three iconic SRD items — each is just data in magic_items.json.
loadout = ["Gauntlets of Ogre Power", "Amulet of Health", "Cloak of Protection"]
components = [component_from_content(items[n]) for n in loadout]
ruleset = compose(DND_5E_2024_RULESET, *components)
show("+ " + ", ".join(loadout), evaluate(ruleset, inputs))

print("\nbase content & ruleset untouched:",
      component_from_content(items["Gauntlets of Ogre Power"]).contributions[0].mode == "set"
      and DND_5E_2024_RULESET.nodes["strength_score"].node_type.value == "input")
