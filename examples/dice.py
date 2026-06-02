"""Roll D&D 5e dice with a typed, reproducible engine.

    python examples/dice.py

For unpredictable production rolls, inject OS entropy instead of seeding:
    import secrets; DiceEngine(rng=secrets.SystemRandom())
"""

from dndwright.dice import DiceEngine

eng = DiceEngine(seed=42)  # reproducible — same seed, same rolls

# Basic expressions → ExpressionResult
print("2d6+3      =", eng.roll("2d6+3").total)
print("4d6kh3     =", eng.roll("4d6kh3").total, "(keep highest 3 of 4)")

# Advantage on a single d20
adv = eng.roll("1d20", advantage=True)
print(f"1d20 adv   = {adv.total}  (rolled {adv.advantage_data.roll1} & "
      f"{adv.advantage_data.roll2}, kept {adv.advantage_data.chosen})")

# Attack vs AC, save vs DC
atk = eng.roll_attack(modifier=5, target_ac=15)
print(f"attack +5 vs AC 15 = {atk.roll.total} → {'HIT' if atk.is_hit else 'miss'}")
save = eng.roll_save(modifier=3, dc=13)
print(f"save +3 vs DC 13   = {save.roll.total} → {'pass' if save.is_success else 'fail'}")

# Critical damage doubles the dice
crit = eng.roll_damage("2d8", is_critical=True)
print(f"crit 2d8   = {crit.roll.total}  (rolled as {crit.roll.dice_results[0].dice_group})")

# A full ability-score array
array = eng.roll_stat_array("4d6kh3")
print("stat array =", array.scores)
