"""The weapon attack/damage helper — ability selection, proficiency, versatile, mastery."""

import pytest

from dndwright import load_content
from dndwright.combat import WeaponAttack, weapon_attack
from dndwright.dice import DiceEngine
from dndwright.rules.lookup_tables import WEAPON_MASTERY_DESCRIPTIONS, get_all_lookup_tables

WEAPONS = load_content("weapons")
MASTERY_MAP = get_all_lookup_tables()["weapon_mastery_map"]


def test_strength_melee_with_proficiency():
    a = weapon_attack("Longsword", strength_mod=3, proficiency_bonus=3)
    assert isinstance(a, WeaponAttack)
    assert a.ability == "strength"
    assert a.attack_bonus == 6            # +3 Str, +3 proficient
    assert a.damage_dice == "1d8" and a.damage_modifier == 3
    assert a.damage == "1d8 + 3" and a.damage_type == "Slashing"


def test_proficiency_excluded_when_not_proficient():
    a = weapon_attack("Greatsword", strength_mod=3, proficiency_bonus=3, proficient=False)
    assert a.proficiency_bonus == 0
    assert a.attack_bonus == 3            # ability only
    assert a.damage == "2d6 + 3"


def test_finesse_melee_uses_better_of_str_or_dex():
    rogue = weapon_attack("Rapier", strength_mod=0, dexterity_mod=4, proficiency_bonus=2)
    assert rogue.ability == "dexterity" and rogue.attack_bonus == 6 and rogue.damage == "1d8 + 4"
    # a strong, clumsy wielder of the same finesse weapon takes Strength
    brute = weapon_attack("Rapier", strength_mod=4, dexterity_mod=1, proficiency_bonus=2)
    assert brute.ability == "strength" and brute.damage == "1d8 + 4"
    # tie goes to Dexterity
    tie = weapon_attack("Shortsword", strength_mod=2, dexterity_mod=2, proficiency_bonus=2)
    assert tie.ability == "dexterity"


def test_ranged_always_uses_dexterity():
    # even when Strength is higher, a Ranged weapon uses Dex
    bow = weapon_attack("Longbow", strength_mod=5, dexterity_mod=2, proficiency_bonus=2)
    assert bow.ability == "dexterity" and bow.attack_bonus == 4 and bow.damage == "1d8 + 2"


def test_versatile_two_handed_uses_larger_die():
    one = weapon_attack("Longsword", strength_mod=2, proficiency_bonus=2)
    two = weapon_attack("Longsword", strength_mod=2, proficiency_bonus=2, two_handed=True)
    assert one.damage_dice == "1d8" and not one.two_handed
    assert two.damage_dice == "1d10" and two.two_handed and two.damage == "1d10 + 2"
    # two_handed on a non-versatile weapon is a no-op
    gs = weapon_attack("Greatsword", strength_mod=2, proficiency_bonus=2, two_handed=True)
    assert gs.damage_dice == "2d6"


def test_magic_and_feature_bonuses():
    a = weapon_attack("Longsword", strength_mod=3, proficiency_bonus=3,
                      attack_bonus=1, damage_bonus=2)
    assert a.attack_bonus == 7            # 3 + 3 + 1
    assert a.damage_modifier == 5 and a.damage == "1d8 + 5"  # 3 + 2


def test_damage_expression_formatting():
    neg = weapon_attack("Club", strength_mod=-1, proficiency_bonus=2)
    assert neg.damage == "1d4 - 1"
    zero = weapon_attack("Club", strength_mod=0, proficiency_bonus=2)
    assert zero.damage == "1d4"           # no trailing "+ 0"


def test_topple_reports_save_dc_others_dont():
    topple = weapon_attack("Maul", strength_mod=4, proficiency_bonus=3)  # Topple mastery
    assert topple.mastery == "Topple"
    assert topple.mastery_save_dc == 8 + 3 + 4
    sap = weapon_attack("Longsword", strength_mod=4, proficiency_bonus=3)
    assert sap.mastery == "Sap" and sap.mastery_save_dc is None


@pytest.mark.parametrize("w", WEAPONS, ids=lambda w: w["name"])
def test_mastery_matches_lookup_tables_and_has_effect_text(w):
    a = weapon_attack(w, strength_mod=1, dexterity_mod=1, proficiency_bonus=2)
    assert a.mastery == w["mastery"]
    assert MASTERY_MAP[w["name"].lower()] == a.mastery        # agrees with the rules table
    assert a.mastery_effect == WEAPON_MASTERY_DESCRIPTIONS[a.mastery]


@pytest.mark.parametrize("w", WEAPONS, ids=lambda w: w["name"])
def test_every_weapon_resolves_and_rolls(w):
    a = weapon_attack(w["name"], strength_mod=2, dexterity_mod=3, proficiency_bonus=2)
    assert a.ability in ("strength", "dexterity")
    assert a.damage_type in ("Slashing", "Piercing", "Bludgeoning")
    # the produced expression is rollable by the dice engine
    rolled = DiceEngine(seed=3).roll_damage(a.damage)
    assert rolled.roll.total >= 1


def test_unknown_weapon_raises():
    with pytest.raises(KeyError):
        weapon_attack("Lightsaber", strength_mod=3, proficiency_bonus=2)


def test_accepts_a_weapon_dict_without_reloading_catalog():
    longsword = next(w for w in WEAPONS if w["name"] == "Longsword")
    a = weapon_attack(longsword, strength_mod=3, proficiency_bonus=3)
    assert a.weapon == "Longsword" and a.attack_bonus == 6
