"""Feats as legos: snap SRD feats onto a character — including dynamic & chosen effects.

    python examples/feat_components.py

Feats show two things a flat magic-item bonus can't: a *dynamic* effect (Alert adds your
proficiency bonus to Initiative — it scales as you level) and a *chosen* effect (the ability
a feat boosts is the player's choice, a ``{placeholder}`` filled at compose time).
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

inputs = character_data_to_inputs(
    ability_scores={"strength": 15, "dexterity": 14, "constitution": 13,
                    "intelligence": 10, "wisdom": 11, "charisma": 8},
    class_data={"class_name": "fighter"}, subclass_data=None,
    species_data={"name": "Human", "speed": 30}, background_data=None, level=8,
)


def show(label, sheet):
    print(f"{label:30} STR {sheet['strength_score']:>2}  DEX {sheet['dexterity_score']:>2}  "
          f"init {sheet['initiative']:+d}")


print("SRD feats that carry a mechanical component:")
for n in sorted(n for n, f in feats.items() if f.get("component")):
    print(f"  • {n} ({feats[n]['category']})")
print()

show("base L8 fighter (prof +3)", evaluate(DND_5E_2024_RULESET, inputs))

# Alert: + proficiency bonus to Initiative (dynamic — scales with level).
alert = component_from_content(feats["Alert"])
show("+ Alert", evaluate(compose(DND_5E_2024_RULESET, alert), inputs))

# Ability Score Improvement: +2 to an ability of *your choice*.
asi = component_from_content(feats["Ability Score Improvement"], choices={"ability": "strength"})
show("+ ASI (chose Strength)", evaluate(compose(DND_5E_2024_RULESET, asi), inputs))

# Stack them like legos.
show("+ both", evaluate(compose(DND_5E_2024_RULESET, alert, asi), inputs))
