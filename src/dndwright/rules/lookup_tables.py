"""All D&D 5e 2024 lookup tables extracted from generation.py constants.

These tables are pure data — no logic, no code. They become part of the
Ruleset and are available to any formula operation via the `tables` parameter.
"""

from __future__ import annotations

# =============================================================================
# Armor
# =============================================================================

ARMOR_BASE_AC: dict[str, int] = {
    "none": 10,
    "unarmored": 10,
    "padded": 11,
    "leather": 11,
    "studded": 12,
    "studded_leather": 12,
    "studded leather": 12,
    "hide": 12,
    "chain_shirt": 13,
    "chain shirt": 13,
    "scale_mail": 14,
    "scale mail": 14,
    "breastplate": 14,
    "half_plate": 15,
    "half plate": 15,
    "ring_mail": 14,
    "ring mail": 14,
    "chain_mail": 16,
    "chain mail": 16,
    "splint": 17,
    "plate": 18,
}

# Maximum DEX bonus allowed by armor type.
# None = unlimited (light/unarmored), 0 = no DEX bonus (heavy).
ARMOR_MAX_DEX: dict[str, int | None] = {
    "none": None,
    "unarmored": None,
    "padded": None,
    "leather": None,
    "studded": None,
    "studded_leather": None,
    "studded leather": None,
    "hide": 2,
    "chain_shirt": 2,
    "chain shirt": 2,
    "scale_mail": 2,
    "scale mail": 2,
    "breastplate": 2,
    "half_plate": 2,
    "half plate": 2,
    "ring_mail": 0,
    "ring mail": 0,
    "chain_mail": 0,
    "chain mail": 0,
    "splint": 0,
    "plate": 0,
}

# =============================================================================
# Skill → Ability mapping
# =============================================================================

SKILL_ABILITY_MAP: dict[str, str] = {
    "acrobatics": "dexterity",
    "animal_handling": "wisdom",
    "arcana": "intelligence",
    "athletics": "strength",
    "deception": "charisma",
    "history": "intelligence",
    "insight": "wisdom",
    "intimidation": "charisma",
    "investigation": "intelligence",
    "medicine": "wisdom",
    "nature": "intelligence",
    "perception": "wisdom",
    "performance": "charisma",
    "persuasion": "charisma",
    "religion": "intelligence",
    "sleight_of_hand": "dexterity",
    "stealth": "dexterity",
    "survival": "wisdom",
}

# =============================================================================
# Spellcasting ability by class
# =============================================================================

SPELL_ABILITY_BY_CLASS: dict[str, str] = {
    "wizard": "intelligence",
    "artificer": "intelligence",
    "cleric": "wisdom",
    "druid": "wisdom",
    "ranger": "wisdom",
    "monk": "wisdom",
    "bard": "charisma",
    "paladin": "charisma",
    "sorcerer": "charisma",
    "warlock": "charisma",
}

# =============================================================================
# Hit die by class
# =============================================================================

HIT_DIE_BY_CLASS: dict[str, int] = {
    "barbarian": 12,
    "fighter": 10,
    "paladin": 10,
    "ranger": 10,
    "monk": 8,
    "rogue": 8,
    "bard": 8,
    "cleric": 8,
    "druid": 8,
    "warlock": 8,
    "artificer": 8,
    "wizard": 6,
    "sorcerer": 6,
}

# Hit die by archetype (fallback when class name not available)
HIT_DIE_BY_ARCHETYPE: dict[str, int] = {
    "full_martial": 10,
    "skill_martial": 8,
    "primal_martial": 12,
    "half_caster": 10,
    "full_caster": 6,
    "pact_caster": 8,
    "support_caster": 8,
    "gish": 8,
    "tank": 10,
    "martial": 10,
}

# =============================================================================
# Spell slot progression tables
# =============================================================================

# Full casters: Wizard, Cleric, Druid, Sorcerer, Bard
SPELL_SLOTS_FULL: dict[int, dict[str, int]] = {
    1: {"1st": 2},
    2: {"1st": 3},
    3: {"1st": 4, "2nd": 2},
    4: {"1st": 4, "2nd": 3},
    5: {"1st": 4, "2nd": 3, "3rd": 2},
    6: {"1st": 4, "2nd": 3, "3rd": 3},
    7: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 1},
    8: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 2},
    9: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 1},
    10: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2},
    11: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1},
    12: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1},
    13: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1},
    14: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1},
    15: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1},
    16: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1},
    17: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
    18: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 3, "6th": 1, "7th": 1, "8th": 1, "9th": 1},
    19: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 3, "6th": 2, "7th": 1, "8th": 1, "9th": 1},
    20: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 3, "6th": 2, "7th": 2, "8th": 1, "9th": 1},
}

# Half casters: Paladin, Ranger — start at level 2
SPELL_SLOTS_HALF: dict[int, dict[str, int]] = {
    1: {},
    2: {"1st": 2},
    3: {"1st": 3},
    4: {"1st": 3},
    5: {"1st": 4, "2nd": 2},
    6: {"1st": 4, "2nd": 2},
    7: {"1st": 4, "2nd": 3},
    8: {"1st": 4, "2nd": 3},
    9: {"1st": 4, "2nd": 3, "3rd": 2},
    10: {"1st": 4, "2nd": 3, "3rd": 2},
    11: {"1st": 4, "2nd": 3, "3rd": 3},
    12: {"1st": 4, "2nd": 3, "3rd": 3},
    13: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 1},
    14: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 1},
    15: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 2},
    16: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 2},
    17: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 1},
    18: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 1},
    19: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2},
    20: {"1st": 4, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2},
}

# Warlock pact magic — separate system
SPELL_SLOTS_WARLOCK: dict[int, dict[str, int]] = {
    1: {"pact": 1, "pact_level": 1},
    2: {"pact": 2, "pact_level": 1},
    3: {"pact": 2, "pact_level": 2},
    4: {"pact": 2, "pact_level": 2},
    5: {"pact": 2, "pact_level": 3},
    6: {"pact": 2, "pact_level": 3},
    7: {"pact": 2, "pact_level": 4},
    8: {"pact": 2, "pact_level": 4},
    9: {"pact": 2, "pact_level": 5},
    10: {"pact": 2, "pact_level": 5},
    11: {"pact": 3, "pact_level": 5},
    12: {"pact": 3, "pact_level": 5},
    13: {"pact": 3, "pact_level": 5},
    14: {"pact": 3, "pact_level": 5},
    15: {"pact": 3, "pact_level": 5},
    16: {"pact": 3, "pact_level": 5},
    17: {"pact": 4, "pact_level": 5},
    18: {"pact": 4, "pact_level": 5},
    19: {"pact": 4, "pact_level": 5},
    20: {"pact": 4, "pact_level": 5},
}

# =============================================================================
# Spellcasting type by class
# =============================================================================

SPELLCASTING_TYPE_BY_CLASS: dict[str, str] = {
    "wizard": "full_caster",
    "cleric": "full_caster",
    "druid": "full_caster",
    "sorcerer": "full_caster",
    "bard": "full_caster",
    "paladin": "half_caster",
    "ranger": "half_caster",
    "artificer": "half_caster",
    "warlock": "pact_caster",
    "fighter": "none",
    "barbarian": "none",
    "rogue": "none",
    "monk": "none",
}

# =============================================================================
# XP thresholds
# =============================================================================

XP_THRESHOLDS: dict[int, int] = {
    1: 0,
    2: 300,
    3: 900,
    4: 2700,
    5: 6500,
    6: 14000,
    7: 23000,
    8: 34000,
    9: 48000,
    10: 64000,
    11: 85000,
    12: 100000,
    13: 120000,
    14: 140000,
    15: 165000,
    16: 195000,
    17: 225000,
    18: 265000,
    19: 305000,
    20: 355000,
}

# =============================================================================
# Item rarity unlock requirements
# =============================================================================

RARITY_UNLOCK_REQUIREMENTS: dict[str, dict[str, int]] = {
    "common": {"min_level": 1, "min_xp": 0},
    "uncommon": {"min_level": 1, "min_xp": 0},
    "rare": {"min_level": 5, "min_xp": 6500},
    "very_rare": {"min_level": 11, "min_xp": 85000},
    "legendary": {"min_level": 17, "min_xp": 225000},
    "artifact": {"min_level": 17, "min_xp": 225000},
}

# Simple level-only lookup (convenience alias)
RARITY_LEVEL_REQUIREMENTS: dict[str, int] = {
    rarity: req["min_level"] for rarity, req in RARITY_UNLOCK_REQUIREMENTS.items()
}

# =============================================================================
# Weapon mastery (D&D 2024)
# =============================================================================

WEAPON_MASTERY_MAP: dict[str, str] = {
    # Simple melee
    "club": "Slow",
    "dagger": "Nick",
    "greatclub": "Push",
    "handaxe": "Vex",
    "javelin": "Slow",
    "light hammer": "Nick",
    "mace": "Sap",
    "quarterstaff": "Topple",
    "sickle": "Nick",
    "spear": "Sap",
    # Simple ranged
    "dart": "Vex",
    "light crossbow": "Slow",
    "shortbow": "Vex",
    "sling": "Slow",
    # Martial melee
    "battleaxe": "Topple",
    "flail": "Sap",
    "glaive": "Graze",
    "greataxe": "Cleave",
    "greatsword": "Graze",
    "halberd": "Cleave",
    "lance": "Topple",
    "longsword": "Sap",
    "maul": "Topple",
    "morningstar": "Sap",
    "pike": "Push",
    "rapier": "Vex",
    "scimitar": "Nick",
    "shortsword": "Vex",
    "trident": "Topple",
    "war pick": "Sap",
    "warhammer": "Push",
    "whip": "Slow",
    # Martial ranged
    "blowgun": "Vex",
    "hand crossbow": "Vex",
    "heavy crossbow": "Push",
    "longbow": "Slow",
    "musket": "Slow",
    "pistol": "Vex",
}

# D&D 2024 weapon mastery rule text — paraphrased from PHB pp. 213-214,
# keyed by the canonical mastery label that WEAPON_MASTERY_MAP emits.
# Used by adapters.py::_build_equipment_info to surface the effect in
# the character-sheet response. An unknown key MUST
# surface as `mastery_unknown: true` rather than silently empty
# description.
WEAPON_MASTERY_DESCRIPTIONS: dict[str, str] = {
    "Cleave": (
        "After hitting a creature with a melee attack, you can make "
        "a melee attack with the same weapon against a second "
        "creature within 5 feet of the first, using the same attack "
        "roll. The second target must be within the weapon's reach. "
        "You can use this once per turn."
    ),
    "Graze": (
        "If your attack roll against a creature misses, you can deal "
        "damage to that creature equal to the ability modifier used "
        "to make the attack roll. The damage is the same type as the "
        "weapon's damage. Doesn't apply on a critical miss."
    ),
    "Nick": (
        "When you make the extra attack of the Light property, you "
        "can make it as part of the Attack action instead of as a "
        "Bonus Action. You can make this extra attack only once per "
        "turn."
    ),
    "Push": (
        "When you hit a creature with this weapon, you can push the "
        "creature up to 10 feet straight away from you if it's Large "
        "or smaller."
    ),
    "Sap": (
        "When you hit a creature with this weapon, that creature has "
        "Disadvantage on its next attack roll before the start of "
        "your next turn."
    ),
    "Slow": (
        "When you hit a creature with this weapon and deal damage, "
        "you can reduce that creature's Speed by 10 feet until the "
        "start of your next turn. If the creature is hit more than "
        "once, the speed reduction doesn't stack."
    ),
    "Topple": (
        "When you hit a creature with this weapon, you can force the "
        "creature to make a Constitution saving throw (DC 8 + your "
        "proficiency bonus + the ability modifier used to make the "
        "attack roll). On a failed save, the creature has the Prone "
        "condition."
    ),
    "Vex": (
        "When you hit a creature with this weapon and deal damage, "
        "you have Advantage on your next attack roll against that "
        "creature before the end of your next turn."
    ),
}

# =============================================================================
# Archetype-based proficiency defaults
# =============================================================================

ARCHETYPE_WEAPON_PROFICIENCIES: dict[str, list[str]] = {
    "full_martial": ["Simple weapons", "Martial weapons"],
    "skill_martial": ["Simple weapons", "Martial weapons"],
    "half_caster": ["Simple weapons", "Martial weapons"],
    "full_caster": ["Daggers", "Darts", "Slings", "Quarterstaffs", "Light crossbows"],
    "support_caster": ["Simple weapons"],
    "gish": ["Simple weapons", "Martial weapons"],
}

ARCHETYPE_ARMOR_PROFICIENCIES: dict[str, list[str]] = {
    "full_martial": ["Light armor", "Medium armor", "Heavy armor", "Shields"],
    "skill_martial": ["Light armor", "Medium armor"],
    "half_caster": ["Light armor", "Medium armor", "Shields"],
    "full_caster": [],
    "support_caster": ["Light armor"],
    "gish": ["Light armor", "Medium armor"],
}

# =============================================================================
# Saving throw proficiencies by class
# =============================================================================

SAVE_PROFICIENCIES_BY_CLASS: dict[str, list[str]] = {
    "barbarian": ["strength", "constitution"],
    "bard": ["dexterity", "charisma"],
    "cleric": ["wisdom", "charisma"],
    "druid": ["intelligence", "wisdom"],
    "fighter": ["strength", "constitution"],
    "monk": ["strength", "dexterity"],
    "paladin": ["wisdom", "charisma"],
    "ranger": ["strength", "dexterity"],
    "rogue": ["dexterity", "intelligence"],
    "sorcerer": ["constitution", "charisma"],
    "warlock": ["wisdom", "charisma"],
    "wizard": ["intelligence", "wisdom"],
    "artificer": ["constitution", "intelligence"],
}

# =============================================================================
# Monster/creature stat block tables (for future creature computation graph)
# =============================================================================

# Challenge Rating to Proficiency Bonus
CR_PROFICIENCY_BONUS: dict[str, int] = {
    "0": 2,
    "1/8": 2,
    "1/4": 2,
    "1/2": 2,
    "1": 2,
    "2": 2,
    "3": 2,
    "4": 2,
    "5": 3,
    "6": 3,
    "7": 3,
    "8": 3,
    "9": 4,
    "10": 4,
    "11": 4,
    "12": 4,
    "13": 5,
    "14": 5,
    "15": 5,
    "16": 5,
    "17": 6,
    "18": 6,
    "19": 6,
    "20": 6,
    "21": 7,
    "22": 7,
    "23": 7,
    "24": 7,
    "25": 8,
    "26": 8,
    "27": 8,
    "28": 8,
    "29": 9,
    "30": 9,
}

# Size categories to hit die size
CREATURE_SIZE_HIT_DIE: dict[str, int] = {
    "tiny": 4,
    "small": 6,
    "medium": 8,
    "large": 10,
    "huge": 12,
    "gargantuan": 20,
}


def get_all_lookup_tables() -> dict:
    """Return all lookup tables as a flat dict for use in a Ruleset."""
    return {
        "armor_base_ac": ARMOR_BASE_AC,
        "armor_max_dex": ARMOR_MAX_DEX,
        "skill_ability_map": SKILL_ABILITY_MAP,
        "spell_ability_by_class": SPELL_ABILITY_BY_CLASS,
        "hit_die_by_class": HIT_DIE_BY_CLASS,
        "hit_die_by_archetype": HIT_DIE_BY_ARCHETYPE,
        "spell_slots_full": SPELL_SLOTS_FULL,
        "spell_slots_half": SPELL_SLOTS_HALF,
        "spell_slots_warlock": SPELL_SLOTS_WARLOCK,
        "spellcasting_type_by_class": SPELLCASTING_TYPE_BY_CLASS,
        "xp_thresholds": XP_THRESHOLDS,
        "rarity_unlock_requirements": RARITY_UNLOCK_REQUIREMENTS,
        "weapon_mastery_map": WEAPON_MASTERY_MAP,
        "archetype_weapon_proficiencies": ARCHETYPE_WEAPON_PROFICIENCIES,
        "archetype_armor_proficiencies": ARCHETYPE_ARMOR_PROFICIENCIES,
        "save_proficiencies_by_class": SAVE_PROFICIENCIES_BY_CLASS,
        "cr_proficiency_bonus": CR_PROFICIENCY_BONUS,
        "creature_size_hit_die": CREATURE_SIZE_HIT_DIE,
    }
