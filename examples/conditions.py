"""Inspect 5e conditions and tick their durations — pure rules over bundled SRD data.

    python examples/conditions.py
"""

from dndwright.combat.conditions import (
    ROUND_END,
    SAVE_ENDS,
    ActiveCondition,
    attempt_save,
    condition_effects,
    implied_conditions,
    is_immune,
    tick_conditions,
)

# Mechanical flags come from the bundled SRD catalog (dndwright.content "conditions").
para = condition_effects("paralyzed")
print(f"{para.display_name}: incapacitated={para.is_incapacitating} "
      f"attackers_have_advantage={para.grants_advantage_to_attackers}")
print(f"  implies: {implied_conditions('paralyzed')}")
print(f"  effects: {para.effects[0]} …")

# Exhaustion stacks cumulatively by level.
print("exhaustion lvl 3:", condition_effects("exhaustion", level=3).effects)

# Immunity: a petrified creature can't be poisoned.
print("petrified → immune to poisoned:", is_immune(["petrified"], "poisoned"))

# Duration ticking: a 2-round hex counts down, then expires.
hex_cond = ActiveCondition("hexed", "rounds", rounds_remaining=2)
for round_no in (1, 2):
    [change] = tick_conditions([hex_cond], ROUND_END)
    print(f"round {round_no}: hex {change.change}"
          + (f" ({change.rounds_remaining} left)" if change.rounds_remaining else ""))
    if change.change == "ticked":
        hex_cond = ActiveCondition("hexed", "rounds", rounds_remaining=change.rounds_remaining)

# A save-ends condition: roll vs the DC to shake it off.
poisoned = ActiveCondition("poisoned", SAVE_ENDS, save_dc=13)
save = attempt_save(poisoned, roll_total=15)
print(f"save vs poisoned (DC 13, rolled 15): {save.reason}, removed={save.condition_removed}")
