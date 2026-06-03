"""Snap mini-graphs ("legos") onto a character's computation graph — they cascade.

    python examples/compose.py

A magic item is a Component (a mini-graph + how it attaches). compose() merges it into
the ruleset; because the attached node keeps its id, every downstream value recomputes
automatically. Composition is pure (the base ruleset is untouched) and stacks.
"""

from dndwright import (
    DND_5E_2024_RULESET,
    character_data_to_inputs,
    compose,
    evaluate,
    modifier,
    validate_ruleset,
)

inputs = character_data_to_inputs(
    ability_scores={"strength": 14, "dexterity": 12, "constitution": 14,
                    "intelligence": 10, "wisdom": 11, "charisma": 8},
    class_data={"class_name": "fighter"}, subclass_data=None,
    species_data={"name": "Human", "speed": 30}, background_data=None, level=5,
)


def show(label, sheet):
    print(f"{label:24} STR {sheet['strength_score']:>2}  mod {sheet['strength_mod']:+d}  "
          f"save {sheet['save.strength.bonus']:+d}  athletics {sheet['skill.athletics.bonus']:+d}")


show("base character", evaluate(DND_5E_2024_RULESET, inputs))

# Gauntlets of Ogre Power: your Strength becomes 19 (a "set" — takes the higher).
gauntlets = modifier("gauntlets_of_ogre_power", target="strength_score", amount=19, mode="set")
show("+ gauntlets (set 19)", evaluate(compose(DND_5E_2024_RULESET, gauntlets), inputs))

# Stack a Manual of Gainful Exercise (+2 STR, an additive bonus) on top.
manual = modifier("manual_of_gainful_exercise", target="strength_score", amount=2, mode="add")
both = compose(DND_5E_2024_RULESET, gauntlets, manual)
assert validate_ruleset(both) == []
show("+ both (max(19, 14+2))", evaluate(both, inputs))

print("\nbase ruleset untouched:",
      "strength_score" in DND_5E_2024_RULESET.nodes
      and DND_5E_2024_RULESET.nodes["strength_score"].node_type.value == "input")
