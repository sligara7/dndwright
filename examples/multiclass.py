"""Multiclass via the lower-level engine: typed inputs → evaluate → apply_modifiers.

A Fighter 5 / Wizard 3. The high-level ``evaluate_character`` is single-class; for
multiclass you assemble typed inputs and hand them to the engine.

    python examples/multiclass.py
"""

from dndwright import (
    DND_5E_2024_RULESET,
    apply_modifiers,
    assemble_character_inputs,
    evaluate,
)
from dndwright.rules.components import ClassMechanics

fighter = ClassMechanics(hit_die=10, archetype="warrior",
                         saving_throw_proficiencies=["strength", "constitution"])
wizard = ClassMechanics(hit_die=6, archetype="mage",
                        saving_throw_proficiencies=["intelligence", "wisdom"],
                        spellcasting_type="full_caster", spellcasting_ability="intelligence")

inputs = assemble_character_inputs(
    class_mechanics=fighter, class_name="fighter", level=8,        # total level
    additional_classes={"wizard": wizard},
    additional_class_levels={"wizard": 3},                         # → fighter 5 / wizard 3
    ability_scores={"strength": 16, "dexterity": 12, "constitution": 14,
                    "intelligence": 15, "wisdom": 10, "charisma": 8},
)

computed = apply_modifiers(evaluate(DND_5E_2024_RULESET, inputs), inputs)

print("class levels:", inputs["class_levels"])     # {'fighter': 5, 'wizard': 3}
print("hit dice:   ", computed["hit_dice"])        # 5d10 + 3d6
print("max HP:     ", computed["hp_max"])
print("prof bonus: ", computed["proficiency_bonus"])
