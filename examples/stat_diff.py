"""See exactly which stats change when a character levels up (or re-equips).

``compute_stat_diff`` evaluates two character states and reports the key stats that
differ — handy for "what did this change do?" UIs.

    python examples/stat_diff.py
"""

from dndwright.rules.character_evaluator import compute_stat_diff

base = {
    "ability_scores": {"strength": 15, "dexterity": 14, "constitution": 14,
                       "intelligence": 10, "wisdom": 12, "charisma": 8},
    "class_data": {"class_name": "fighter"},
    "species_data": {"name": "Human", "speed": 30},
    "level": 4,
}
leveled_up = {**base, "level": 5}

diff = compute_stat_diff(base, leveled_up)

print("Level 4 → 5 changes:")
for node_id, change in diff.items():
    sign = "+" if change["delta"] >= 0 else ""
    print(f"  {change['label']:18} {change['before']} → {change['after']}  ({sign}{change['delta']})")
