"""Quickstart: a dict of character data in, a fully computed sheet out.

    python examples/quickstart.py
"""

from dndwright import evaluate_character

sheet = evaluate_character({
    "ability_scores": {"strength": 8, "dexterity": 14, "constitution": 14,
                       "intelligence": 18, "wisdom": 12, "charisma": 10},
    "class_data": {"class_name": "wizard"},
    "species_data": {"name": "Human", "speed": 30},
    "level": 5,
})

print("proficiency_bonus:", sheet["proficiency_bonus"])      # 3
print("ability_modifiers:", sheet["ability_modifiers"])      # int: +4, dex: +2, ...
print("armor_class:", sheet["armor_class"])
print("hit_points:", sheet["hit_points"])

# strict=True turns malformed input into an error instead of a wrong sheet:
from dndwright import CharacterInputError  # noqa: E402

try:
    evaluate_character({"level": 0}, strict=True)
except CharacterInputError as e:
    print("\nstrict mode caught bad input:")
    print(e)
