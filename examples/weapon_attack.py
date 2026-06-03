"""Turn a weapon + an attacker into a to-hit bonus and a damage roll — pure, no IDs.

    python examples/weapon_attack.py

weapon_attack() looks the weapon up in the bundled SRD table, picks the right ability
(Ranged -> Dex, Finesse melee -> better of Str/Dex, else Str), applies proficiency and
any magic/feature bonuses, and hands you an attack bonus + a damage expression. Feed
those to a DiceEngine to actually roll. The attacker's modifiers are exactly the
strength_mod / dexterity_mod / proficiency_bonus you get from an evaluated character sheet.
"""

from dndwright.combat import weapon_attack
from dndwright.dice import DiceEngine

eng = DiceEngine(seed=7)  # reproducible

# A level-5 fighter (Str 18 -> +4, proficiency +3) swinging a longsword two-handed.
atk = weapon_attack("Longsword", strength_mod=4, proficiency_bonus=3, two_handed=True)
print(f"{atk.weapon}: {atk.ability} attack +{atk.attack_bonus}, "
      f"{atk.damage} {atk.damage_type}  (mastery: {atk.mastery})")

hit = eng.roll_attack(modifier=atk.attack_bonus, target_ac=15)
print(f"  attack roll {hit.roll.total} vs AC 15 -> {'HIT' if hit.is_hit else 'miss'}"
      f"{' (CRIT!)' if hit.roll.is_critical else ''}")
if hit.is_hit:
    dmg = eng.roll_damage(atk.damage, is_critical=hit.roll.is_critical)
    print(f"  damage: {dmg.roll.total} {atk.damage_type}")

# A dexterous rogue with a finesse rapier: the rules take Dexterity automatically.
rogue = weapon_attack("Rapier", strength_mod=0, dexterity_mod=4, proficiency_bonus=2)
print(f"\n{rogue.weapon}: used {rogue.ability}, attack +{rogue.attack_bonus}, {rogue.damage}")

# A magic weapon and a damage-boosting feature stack via the bonus args.
magic = weapon_attack("Greatsword", strength_mod=4, proficiency_bonus=3,
                      attack_bonus=1, damage_bonus=2)  # +1 weapon, +2 from a feature
print(f"{magic.weapon} +1: attack +{magic.attack_bonus}, {magic.damage} {magic.damage_type}")
