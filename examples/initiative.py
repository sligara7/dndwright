"""Roll initiative, order the combatants, and walk the turn tracker — pure, no DB.

    python examples/initiative.py
"""

from dndwright.combat.initiative import (
    InitiativeEntry,
    advance_turn,
    order_initiative,
    roll_initiative,
)
from dndwright.dice import DiceEngine

eng = DiceEngine(seed=3)  # reproducible

# Roll initiative for each combatant (1d20 + DEX-ish modifier).
combatants = [("Rogue", 4), ("Goblin", 2), ("Ogre", -1), ("Goblin", 2)]
entries = []
for name, dex in combatants:
    r = roll_initiative(eng, modifier=dex)
    entries.append(InitiativeEntry(name=name, total=r.total, dexterity_modifier=dex))
    print(f"{name:7} rolled {r.roll:>2} + {dex:+d} = {r.total}")

order = order_initiative(entries)  # total desc, DEX tiebreak, stable
print("\norder:", " → ".join(f"{e.name}({e.total})" for e in order))

# Walk two rounds of turns.
print()
round_number, turn_index = 1, 0
print(f"round 1 starts on {order[0].name}")
for _ in range(len(order) + 1):
    t = advance_turn(order, round_number, turn_index)
    round_number, turn_index = t.round_number, t.turn_index
    marker = "  (new round!)" if t.new_round else ""
    print(f"  → round {round_number}: {order[turn_index].name}{marker}")
