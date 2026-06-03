"""Weapon attack & damage — compose a weapon with an attacker's ability modifiers,
proficiency, and the weapon's mastery into a to-hit bonus and a damage expression.

Pure data + lookup, no RNG: feed the resulting ``attack_bonus`` / ``damage`` to
:class:`dndwright.dice.DiceEngine` (``roll_attack`` / ``roll_damage``) to actually roll.

    from dndwright.combat import weapon_attack
    from dndwright.dice import DiceEngine

    atk = weapon_attack("Longsword", strength_mod=3, proficiency_bonus=3)
    atk.attack_bonus            # 6  (Str +3, proficient +3)
    atk.damage                  # "1d8 + 3"  (Slashing)
    two = weapon_attack("Longsword", strength_mod=3, proficiency_bonus=3, two_handed=True)
    two.damage                  # "1d10 + 3"  (Versatile)

    engine = DiceEngine(seed=1)
    hit = engine.roll_attack(modifier=atk.attack_bonus, target_ac=15)
    if hit.is_hit:
        engine.roll_damage(atk.damage, is_critical=hit.roll.is_critical)

The ability is chosen by the rules: a Ranged weapon uses Dexterity; a Finesse melee
weapon uses the better of Strength/Dexterity; any other melee weapon uses Strength.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..content import load_content
from ..rules.lookup_tables import WEAPON_MASTERY_DESCRIPTIONS

_VERSATILE = re.compile(r"Versatile\s*\((\d+d\d+)\)", re.IGNORECASE)


@dataclass(frozen=True)
class WeaponAttack:
    """A weapon attack resolved against one attacker — to-hit bonus + damage spec.

    ``attack_bonus`` and ``damage`` are ready to hand to :class:`DiceEngine`.
    """

    weapon: str
    ability: str               # "strength" | "dexterity" — the ability this attack used
    ability_modifier: int
    proficiency_bonus: int     # the bonus actually applied (0 when not proficient)
    proficient: bool
    attack_bonus: int          # total to-hit = ability_mod + proficiency + extra
    damage_dice: str           # e.g. "1d8" (the Versatile die when two_handed)
    damage_modifier: int       # ability_mod + extra damage
    damage_type: str           # "Slashing" | "Piercing" | "Bludgeoning"
    damage: str                # full expression, e.g. "1d8 + 3" / "2d6" / "1d4 - 1"
    two_handed: bool
    mastery: str | None
    mastery_effect: str | None
    mastery_save_dc: int | None  # for Topple (8 + prof + ability mod); else None


def _resolve_weapon(weapon: str | dict, weapons: list[dict] | None) -> dict:
    if isinstance(weapon, dict):
        return weapon
    catalog = weapons if weapons is not None else load_content("weapons")
    key = weapon.strip().lower()
    for w in catalog:
        if w["name"].lower() == key:
            return w
    raise KeyError(f"unknown weapon: {weapon!r}")


def _damage_expression(dice: str, modifier: int) -> str:
    if modifier > 0:
        return f"{dice} + {modifier}"
    if modifier < 0:
        return f"{dice} - {abs(modifier)}"
    return dice


def weapon_attack(
    weapon: str | dict,
    *,
    strength_mod: int = 0,
    dexterity_mod: int = 0,
    proficiency_bonus: int = 0,
    proficient: bool = True,
    two_handed: bool = False,
    attack_bonus: int = 0,
    damage_bonus: int = 0,
    weapons: list[dict] | None = None,
) -> WeaponAttack:
    """Resolve a weapon attack into a to-hit bonus and a damage expression.

    Args:
        weapon: weapon name (case-insensitive) or a weapons.json entry dict.
        strength_mod, dexterity_mod: the attacker's ability *modifiers* (e.g. the
            ``strength_mod`` / ``dexterity_mod`` from an evaluated character sheet).
        proficiency_bonus: the attacker's proficiency bonus.
        proficient: whether the attacker is proficient with the weapon (adds the
            proficiency bonus to the attack roll when True).
        two_handed: for a Versatile weapon, use its larger two-handed damage die.
        attack_bonus: extra to-hit (magic weapon, Archery style, …).
        damage_bonus: extra flat damage (magic weapon, Dueling, Rage, …).
        weapons: optional preloaded weapons catalog (defaults to ``load_content("weapons")``).

    Returns:
        A :class:`WeaponAttack`. ``ability`` reports which ability the rules picked.
    """
    w = _resolve_weapon(weapon, weapons)
    props = w.get("properties", [])
    is_finesse = any(p.lower().startswith("finesse") for p in props)
    is_ranged = w["kind"].lower() == "ranged"

    # ability selection: Ranged -> Dex; Finesse melee -> better of Str/Dex; else Str
    if is_ranged:
        ability, ability_mod = "dexterity", dexterity_mod
    elif is_finesse and dexterity_mod >= strength_mod:
        ability, ability_mod = "dexterity", dexterity_mod
    else:
        ability, ability_mod = "strength", strength_mod

    prof = proficiency_bonus if proficient else 0
    to_hit = ability_mod + prof + attack_bonus

    dice = w["damage_dice"]
    if two_handed:
        for p in props:
            m = _VERSATILE.search(p)
            if m:
                dice = m.group(1)
                break

    dmg_mod = ability_mod + damage_bonus
    mastery = w.get("mastery")
    save_dc = 8 + prof + ability_mod if mastery == "Topple" else None

    return WeaponAttack(
        weapon=w["name"],
        ability=ability,
        ability_modifier=ability_mod,
        proficiency_bonus=prof,
        proficient=proficient,
        attack_bonus=to_hit,
        damage_dice=dice,
        damage_modifier=dmg_mod,
        damage_type=w["damage_type"],
        damage=_damage_expression(dice, dmg_mod),
        two_handed=two_handed,
        mastery=mastery,
        mastery_effect=WEAPON_MASTERY_DESCRIPTIONS.get(mastery) if mastery else None,
        mastery_save_dc=save_dc,
    )
