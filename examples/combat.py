"""Resolve a combat round with the pure rules + dice — no database, no IDs.

    python examples/combat.py

Every op is (state, input) -> (new_state, explanation). Your app owns persistence:
load a row -> call these -> write the new state back. The rules never see a DB.
"""

from dndwright.combat import (
    CombatantState,
    apply_damage,
    apply_healing,
    roll_death_save,
    set_temp_hp,
    stabilize,
)
from dndwright.dice import DiceEngine

eng = DiceEngine(seed=7)  # reproducible

hero = CombatantState(current_hp=12, max_hp=12)
print(f"start:        {hero.current_hp}/{hero.max_hp} HP")

hero = set_temp_hp(hero, 5)
print(f"+5 temp HP:   {hero.current_hp}/{hero.max_hp} (+{hero.temp_hp} temp)")

hero, applied = apply_damage(hero, 9)  # temp HP soaks 5, 4 to HP
print(f"take 9:       {hero.current_hp}/{hero.max_hp} "
      f"(temp absorbed {applied.absorbed_by_temp_hp}, {applied.damage_to_hp} to HP)")

hero, _ = apply_damage(hero, 10)  # down to 0 (overkill 2 < max, so not massive)
print(f"take 10:      {hero.current_hp}/{hero.max_hp}  dying={hero.is_dying}")

# Make death saves until stable or dead.
while hero.is_dying:
    hero, save = roll_death_save(hero, eng)
    tag = "NAT20!" if save.is_critical_success else ("nat1" if save.is_critical_failure else
          ("success" if save.is_success else "failure"))
    print(f"  death save {save.roll:>2}: {tag}  "
          f"({hero.death_save_successes} ✓ / {hero.death_save_failures} ✗)")

print(f"resolved:     stable={hero.is_stable} dead={hero.is_dead} hp={hero.current_hp}")

if hero.is_stable:
    hero, change = apply_healing(hero, 8)  # an ally heals them
    print(f"healed 8:     {hero.current_hp}/{hero.max_hp} "
          f"(regained consciousness={change.was_healed_from_zero})")
elif not hero.is_dead:
    hero = stabilize(hero)  # Spare the Dying
    print(f"stabilized:   stable={hero.is_stable}")
