"""Adapters for backwards compatibility.

Converts between the old derive_character_sheet() input/output format
and the computation graph's flat input/output dictionaries.

Phase 1: transparent refactor — same inputs in, same output shape out.
"""

from __future__ import annotations

from typing import Any

from .lookup_tables import (
    HIT_DIE_BY_ARCHETYPE,
    HIT_DIE_BY_CLASS,
    SAVE_PROFICIENCIES_BY_CLASS,
    SKILL_ABILITY_MAP,
    SPELLCASTING_TYPE_BY_CLASS,
)

import re




def _resolve_hit_die(class_data: dict) -> int:
    """Return the resolved hit die size, applying lookup-table overrides.

    Mirrors the logic in ``character_data_to_inputs`` lines 51-58 so the display
    value matches the computation.
    """
    hit_die_str = class_data.get("hit_die", "d8")
    hit_die_size = int(hit_die_str.replace("d", "")) if isinstance(hit_die_str, str) else 8

    class_name = class_data.get("class_name", "").lower()
    archetype = (
        class_data.get("archetype")
        or class_data.get("properties", {}).get("archetype", "")
    )
    if class_name in HIT_DIE_BY_CLASS:
        hit_die_size = HIT_DIE_BY_CLASS[class_name]
    elif archetype in HIT_DIE_BY_ARCHETYPE:
        hit_die_size = HIT_DIE_BY_ARCHETYPE[archetype]

    return hit_die_size


_NATURAL_ARMOR_KEYWORDS = re.compile(
    r"(carapace|natural armor|chitin|exoskeleton|scales|tough hide|bark skin|"
    r"thick fur|bony plates|armored shell)",
    re.IGNORECASE,
)
_AC_VALUE_RE = re.compile(r"\bAC\b.*?(\d+)", re.IGNORECASE)


def _parse_natural_armor(species_data: dict) -> int:
    """Extract natural armor AC from species traits, or 0 if none."""
    # Explicit field (future-proof)
    explicit = species_data.get("natural_armor_ac")
    if isinstance(explicit, int) and explicit > 0:
        return explicit

    traits: list[dict] = species_data.get("traits", []) or []
    if not isinstance(traits, list):
        return 0

    for trait in traits:
        if not isinstance(trait, dict):
            continue
        name = (trait.get("name") or "").lower()
        desc = (trait.get("description") or "").lower()
        combined = name + " " + desc

        if _NATURAL_ARMOR_KEYWORDS.search(combined):
            match = _AC_VALUE_RE.search(combined)
            if match:
                return int(match.group(1))

    return 0


def character_data_to_inputs(
    ability_scores: dict[str, int],
    class_data: dict,
    subclass_data: dict | None,
    species_data: dict,
    background_data: dict | None,
    level: int,
    equipment: dict | None = None,
) -> dict[str, Any]:
    """Convert the old derive_character_sheet() parameters to flat graph inputs.

    Returns a dict keyed by computation node IDs.
    """
    inputs: dict[str, Any] = {}

    # --- Ability scores ---
    for ability in ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"):
        inputs[f"{ability}_score"] = ability_scores.get(ability, 10)

    # --- Level and class ---
    inputs["character_level"] = level

    class_name = class_data.get("class_name", "").lower()
    inputs["primary_class"] = class_name

    # Build class_levels dict (single class for now, multiclass in Phase 2)
    inputs["class_levels"] = {class_name: level} if class_name else {"unknown": level}

    # Hit dice per class
    hit_die_str = class_data.get("hit_die", "d8")
    hit_die_size = int(hit_die_str.replace("d", "")) if isinstance(hit_die_str, str) else 8
    # Also try lookup by class name or archetype
    archetype = class_data.get("archetype") or class_data.get("properties", {}).get("archetype", "")
    if class_name in HIT_DIE_BY_CLASS:
        hit_die_size = HIT_DIE_BY_CLASS[class_name]
    elif archetype in HIT_DIE_BY_ARCHETYPE:
        hit_die_size = HIT_DIE_BY_ARCHETYPE[archetype]
    inputs["class_hit_dice"] = (
        {class_name: hit_die_size} if class_name else {"unknown": hit_die_size}
    )

    # --- Speed ---
    speed = species_data.get("speed", 30)
    if isinstance(speed, dict):
        inputs["speed_base"] = speed.get("walk", 30)
    else:
        inputs["speed_base"] = speed

    # --- Equipment → AC inputs ---
    armor_type = "none"
    armor_magic = 0
    has_shield = False
    if equipment:
        armor = equipment.get("armor")
        if armor:
            armor_type = (
                (armor.get("type") or armor.get("armor_type") or armor.get("base_armor") or "none")
                .lower()
                .replace(" ", "_")
            )
            armor_magic = armor.get("magic_bonus", 0)
        has_shield = bool(equipment.get("shield"))

    inputs["armor_type"] = armor_type
    inputs["armor_magic_bonus"] = armor_magic
    inputs["has_shield"] = has_shield

    # --- Species natural armor ---
    inputs["natural_armor_ac"] = _parse_natural_armor(species_data)

    # --- Spellcasting ---
    spellcasting_type = class_data.get("properties", {}).get("spellcasting_type") or class_data.get(
        "spellcasting_type", "none"
    )
    # Also use lookup table as fallback
    if spellcasting_type == "none" and class_name in SPELLCASTING_TYPE_BY_CLASS:
        spellcasting_type = SPELLCASTING_TYPE_BY_CLASS[class_name]
    inputs["spellcasting_type"] = spellcasting_type
    inputs["class_spellcasting_types"] = {class_name: spellcasting_type} if class_name else {}

    # --- Saving throw proficiencies ---
    class_save_profs = (
        class_data.get("properties", {}).get("saving_throw_proficiencies", [])
        or class_data.get("saving_throw_proficiencies", [])
        or class_data.get("properties", {}).get("saving_throws", [])
        or class_data.get("saving_throws", [])
    )
    save_prof_set = {s.lower() for s in class_save_profs}
    # Fallback to lookup table
    if not save_prof_set and class_name in SAVE_PROFICIENCIES_BY_CLASS:
        save_prof_set = set(SAVE_PROFICIENCIES_BY_CLASS[class_name])

    for ability in ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"):
        inputs[f"save.{ability}.proficient"] = ability in save_prof_set

    # --- Skill proficiencies ---
    skill_profs: set[str] = set()
    expertise_skills: set[str] = set()

    # From class
    class_skills = class_data.get("properties", {}).get(
        "skill_proficiencies", []
    ) or class_data.get("skill_proficiencies", [])
    skill_profs.update(s.lower().replace(" ", "_") for s in class_skills)

    # From background
    if background_data:
        bg_skills = background_data.get("skill_proficiencies", [])
        skill_profs.update(s.lower().replace(" ", "_") for s in bg_skills)

    # From species
    species_skills = species_data.get("properties", {}).get(
        "skill_proficiencies", []
    ) or species_data.get("skill_proficiencies", [])
    skill_profs.update(s.lower().replace(" ", "_") for s in species_skills)

    for skill in SKILL_ABILITY_MAP:
        inputs[f"skill.{skill}.proficient"] = skill in skill_profs
        inputs[f"skill.{skill}.expertise"] = skill in expertise_skills

    return inputs


def computed_values_to_sheet(
    computed: dict[str, Any],
    ability_scores: dict[str, int],
    class_data: dict,
    subclass_data: dict | None,
    species_data: dict,
    background_data: dict | None,
    level: int,
    equipment: dict | None = None,
    spells: dict | None = None,
    narrative: dict | None = None,
    character_name: str = "Unnamed",
    alignment: str | None = None,
    selected_feats: list[dict] | None = None,
) -> dict:
    """Reshape flat computed values back into the nested dict format.

    This produces the same output shape as the old derive_character_sheet().
    Non-computed fields (features, equipment details, personality) are passed through.
    """

    def _fmt(val: int | None) -> str:
        if val is None:
            val = 0
        return f"+{val}" if val >= 0 else str(val)

    class_name = class_data.get("class_name", "Unknown")

    # --- Ability modifiers ---
    # `ability_modifiers` is the integer-typed canonical shape — the
    # frontend (and the prior Rust compute_stats stub) consume it as
    # numbers and do downstream math like `mod + prof_bonus`. The
    # formatted "+N" strings ship in parallel as
    # `ability_modifiers_display` so any display-only callers can keep
    # using them without reformatting. Originally only the display
    # shape was emitted, which silently NaN'd downstream math.
    ability_modifiers_int = {}
    ability_modifiers_display = {}
    for ability in ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"):
        ability_modifiers_int[ability] = int(computed.get(f"{ability}_mod", 0))
        ability_modifiers_display[ability] = computed.get(
            f"{ability}_mod_display", _fmt(computed.get(f"{ability}_mod", 0))
        )

    # --- Saving throws ---
    saving_throws = {}
    for ability in ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"):
        mod = computed.get(f"{ability}_mod", 0)
        proficient = computed.get(f"save.{ability}.proficient", False)
        bonus = computed.get(f"save.{ability}.bonus", mod)
        saving_throws[ability] = {
            "modifier": mod,
            "proficient": proficient,
            "bonus": bonus,
            "display": computed.get(f"save.{ability}.display", _fmt(bonus)),
        }

    # --- Skills ---
    skills = {}
    for skill, ability in SKILL_ABILITY_MAP.items():
        proficient = computed.get(f"skill.{skill}.proficient", False)
        expertise = computed.get(f"skill.{skill}.expertise", False)
        bonus = computed.get(f"skill.{skill}.bonus", 0)
        skills[skill] = {
            "ability": ability,
            "proficient": proficient,
            "expertise": expertise,
            "bonus": bonus,
            "display": computed.get(f"skill.{skill}.display", _fmt(bonus)),
        }

    # --- Passive scores ---
    passive_scores = {
        "perception": computed.get("passive_perception", 10),
        "investigation": computed.get("passive_investigation", 10),
        "insight": computed.get("passive_insight", 10),
    }

    # --- Speed ---
    speed = species_data.get("speed", 30)
    if isinstance(speed, dict):
        movement_types = speed
        speed_val = speed.get("walk", 30)
    else:
        movement_types = {"walk": speed}
        speed_val = speed

    # --- Hit dice ---
    hit_die_size = _resolve_hit_die(class_data)
    hit_die = f"d{hit_die_size}"
    hit_dice_str = computed.get("hit_dice", f"{level}{hit_die}")

    # --- Spellcasting ---
    # `character_data_to_inputs` falls back to SPELLCASTING_TYPE_BY_CLASS when
    # class_data doesn't declare spellcasting_type — but only writes it into
    # `inputs["spellcasting_type"]`. The sheet builder used to re-read from
    # class_data only, so a thin class_data (e.g. {"class_name": "wizard"})
    # ended up with `spellcasting=None` even though the inputs/compute path
    # correctly identified it as a full_caster. Fall back to the computed
    # value (which carries the lookup-resolved type) before defaulting to "none".
    spellcasting_info = None
    spellcasting_type = (
        class_data.get("properties", {}).get("spellcasting_type")
        or class_data.get("spellcasting_type")
        or computed.get("spellcasting_type")
        or "none"
    )

    if spellcasting_type and spellcasting_type != "none":
        spell_ability_name = computed.get("spell_ability", "charisma")

        cantrips_known = []
        spells_known = []
        if spells:
            cantrips_known = spells.get("selected_cantrips", [])
            spells_known = spells.get("selected_spells", [])

        # Determine which spell slots to use (multiclass vs single)
        class_levels = computed.get("class_levels", {})
        num_classes = len(class_levels) if isinstance(class_levels, dict) else 1
        if num_classes > 1:
            spell_slots = computed.get("multiclass_spell_slots", {})
        else:
            spell_slots = computed.get("spell_slots", {})

        spellcasting_info = {
            "ability": spell_ability_name.capitalize()
            if isinstance(spell_ability_name, str)
            else "Charisma",
            "save_dc": computed.get("spell_save_dc", 8),
            "attack_bonus": computed.get("spell_attack", 0),
            "attack_display": computed.get(
                "spell_attack_display", _fmt(computed.get("spell_attack", 0))
            ),
            "spell_slots": spell_slots,
            "cantrips_known": cantrips_known,
            "spells_known": spells_known,
            "spellcasting_type": spellcasting_type,
        }

    # --- Proficiencies (pass-through from input data) ---
    proficiencies = _build_proficiencies(class_data, species_data, background_data)

    # --- Features & traits (pass-through from input data) ---
    features_and_traits = _build_features(
        class_data, subclass_data, species_data, background_data, selected_feats
    )
    species_traits_consolidated = _build_species_traits(species_data)

    # --- Equipment (pass-through — weapon attack/damage calc stays imperative for now) ---
    equipment_info = _build_equipment_info(equipment, computed, level)

    # --- Personality (pass-through) ---
    personality = _build_personality(narrative)

    # --- Assemble ---
    return {
        "character_name": character_name,
        "class_name": class_name,
        "subclass_name": subclass_data.get("subclass_name") if subclass_data else None,
        "level": level,
        "species_name": species_data.get("species_name", species_data.get("name", "Unknown")),
        "background_name": (
            background_data.get("background_name", background_data.get("name", "Unknown"))
            if background_data
            else None
        ),
        "alignment": alignment,
        "ability_scores": ability_scores,
        "ability_modifiers": ability_modifiers_int,
        "ability_modifiers_display": ability_modifiers_display,
        "armor_class": computed.get("armor_class", 10),
        "hit_points": computed.get("hp_max", 1),
        "hit_dice": hit_dice_str,
        "hit_die_type": hit_die,
        "speed": speed_val,
        "movement_types": movement_types,
        "initiative": computed.get("initiative", 0),
        "initiative_display": computed.get("initiative_display", "+0"),
        "proficiency_bonus": computed.get("proficiency_bonus", 2),
        "proficiency_display": computed.get("proficiency_bonus_display", "+2"),
        "saving_throws": saving_throws,
        "skills": skills,
        "passive_scores": passive_scores,
        "proficiencies": proficiencies,
        "spellcasting": spellcasting_info,
        "features_and_traits": features_and_traits,
        "species_traits_consolidated": species_traits_consolidated,
        "equipment": equipment_info,
        "personality": personality,
    }


# ---------------------------------------------------------------------------
# Pass-through builders (features, proficiencies, etc. not in the graph yet)
# ---------------------------------------------------------------------------


def _build_proficiencies(
    class_data: dict,
    species_data: dict,
    background_data: dict | None,
) -> dict:
    """Build proficiencies dict from source data (not computed by graph)."""
    from .lookup_tables import ARCHETYPE_ARMOR_PROFICIENCIES, ARCHETYPE_WEAPON_PROFICIENCIES

    # Languages
    languages = []
    species_langs = species_data.get("properties", {}).get("languages", []) or species_data.get(
        "languages", []
    )
    languages.extend(species_langs)
    if background_data:
        languages.extend(background_data.get("languages", []))
    languages = list(set(languages)) or ["Common"]

    # Weapon proficiencies
    weapon_profs = class_data.get("properties", {}).get(
        "weapon_proficiencies", []
    ) or class_data.get("weapon_proficiencies", [])
    armor_profs = class_data.get("properties", {}).get("armor_proficiencies", []) or class_data.get(
        "armor_proficiencies", []
    )

    archetype = class_data.get("archetype") or class_data.get("properties", {}).get("archetype", "")
    if not weapon_profs and archetype:
        weapon_profs = ARCHETYPE_WEAPON_PROFICIENCIES.get(archetype, ["Simple weapons"])
    if not armor_profs and archetype:
        armor_profs = ARCHETYPE_ARMOR_PROFICIENCIES.get(archetype, [])

    # Tool proficiencies
    tool_profs = []
    if background_data:
        bg_tools = background_data.get(
            "tool_proficiency", background_data.get("tool_proficiencies", [])
        )
        if isinstance(bg_tools, str):
            tool_profs.append(bg_tools)
        elif isinstance(bg_tools, list):
            tool_profs.extend(bg_tools)
    class_tools = class_data.get("properties", {}).get("tool_proficiencies", [])
    tool_profs.extend(class_tools)
    tool_profs = list(set(tool_profs))

    # Save prof names
    class_save_profs = (
        class_data.get("properties", {}).get("saving_throw_proficiencies", [])
        or class_data.get("saving_throw_proficiencies", [])
        or class_data.get("properties", {}).get("saving_throws", [])
        or class_data.get("saving_throws", [])
    )
    save_prof_names = [s.capitalize() for s in class_save_profs]

    # Skill proficiency names
    skill_profs: set[str] = set()
    class_skills = class_data.get("properties", {}).get(
        "skill_proficiencies", []
    ) or class_data.get("skill_proficiencies", [])
    skill_profs.update(s.lower().replace(" ", "_") for s in class_skills)
    if background_data:
        bg_skills = background_data.get("skill_proficiencies", [])
        skill_profs.update(s.lower().replace(" ", "_") for s in bg_skills)
    species_skills = species_data.get("properties", {}).get(
        "skill_proficiencies", []
    ) or species_data.get("skill_proficiencies", [])
    skill_profs.update(s.lower().replace(" ", "_") for s in species_skills)

    return {
        "languages": languages,
        "weapons": weapon_profs,
        "armor": armor_profs,
        "tools": tool_profs,
        "saving_throws": save_prof_names,
        "skills": list(skill_profs),
    }


def _build_features(
    class_data: dict,
    subclass_data: dict | None,
    species_data: dict,
    background_data: dict | None,
    selected_feats: list[dict] | None,
) -> dict:
    """Build features and traits dict from source data."""
    class_features = class_data.get("properties", {}).get("core_features", []) or class_data.get(
        "core_features", []
    )

    subclass_features = []
    if subclass_data:
        subclass_features = subclass_data.get("features", []) or subclass_data.get(
            "properties", {}
        ).get("features", [])

    species_traits = species_data.get("traits", []) or species_data.get("properties", {}).get(
        "core_traits", []
    )

    background_feature = None
    origin_feat = None
    if background_data:
        bg_feature = background_data.get("feature", {})
        if bg_feature:
            background_feature = {
                "name": bg_feature.get("name", "Background Feature"),
                "description": bg_feature.get("description", ""),
            }
        origin_feat_data = background_data.get("origin_feat") or background_data.get("feat")
        if origin_feat_data:
            if isinstance(origin_feat_data, str):
                origin_feat = {"name": origin_feat_data, "description": ""}
            elif isinstance(origin_feat_data, dict):
                origin_feat = {
                    "name": origin_feat_data.get("name", origin_feat_data.get("feat_name", "")),
                    "description": origin_feat_data.get("description", ""),
                }

    return {
        "class_features": class_features,
        "subclass_features": subclass_features,
        "species_traits": species_traits,
        "background_feature": background_feature,
        "origin_feat": origin_feat,
        "selected_feats": selected_feats or [],
    }


def _build_species_traits(species_data: dict) -> list[dict]:
    """Build consolidated species traits list."""
    result = []
    senses = species_data.get("senses", {})
    if isinstance(senses, dict):
        darkvision = senses.get("darkvision")
        if darkvision:
            distance = darkvision if isinstance(darkvision, int) else 60
            result.append({"name": f"Darkvision {distance}ft", "category": "sense"})
        for s in senses.get("special") or []:
            s_name = s.get("name", s) if isinstance(s, dict) else s
            result.append({"name": str(s_name), "category": "sense"})

    rest_type = species_data.get("rest_type")
    if (
        rest_type
        and isinstance(rest_type, str)
        and rest_type.lower() not in ("long", "long rest", "standard")
    ):
        result.append({"name": rest_type, "category": "rest"})

    for r in species_data.get("resistances", []):
        r_name = r.get("type", r.get("name", r)) if isinstance(r, dict) else r
        result.append({"name": f"{r_name} Resistance", "category": "resistance"})

    sp_immunities = species_data.get("immunities", {})
    if isinstance(sp_immunities, dict):
        for c in sp_immunities.get("conditions", []):
            result.append({"name": f"{c} Immunity", "category": "immunity"})
        for d in sp_immunities.get("damage", []):
            result.append({"name": f"{d} Immunity", "category": "immunity"})
    elif isinstance(sp_immunities, list):
        for im in sp_immunities:
            result.append({"name": f"{im} Immunity", "category": "immunity"})

    for nw in species_data.get("natural_weapons", []):
        nw_name = nw.get("name", nw) if isinstance(nw, dict) else nw
        result.append({"name": str(nw_name), "category": "natural_weapon"})

    for ct in species_data.get("traits", []):
        ct_name = ct.get("name", ct) if isinstance(ct, dict) else ct
        result.append({"name": str(ct_name), "category": "custom"})

    return result


def _build_equipment_info(
    equipment: dict | None,
    computed: dict[str, Any],
    level: int,
) -> dict:
    """Build equipment info dict. Weapon attack/damage calcs still imperative."""
    from .lookup_tables import (
        ARMOR_BASE_AC,
        ARMOR_MAX_DEX,
        RARITY_UNLOCK_REQUIREMENTS,
        WEAPON_MASTERY_DESCRIPTIONS,
        WEAPON_MASTERY_MAP,
    )

    equipment_info: dict[str, Any] = {
        "weapons": [],
        "armor": None,
        "shield": False,
        "other": [],
        "currency": {"gp": 0, "sp": 0, "cp": 0},
    }

    if not equipment:
        return equipment_info

    str_mod = computed.get("strength_mod", 0)
    dex_mod = computed.get("dexterity_mod", 0)
    prof_bonus = computed.get("proficiency_bonus", 2)

    def _fmt(val: int) -> str:
        return f"+{val}" if val >= 0 else str(val)

    def _is_unlocked(rarity: str) -> bool:
        reqs = RARITY_UNLOCK_REQUIREMENTS.get(rarity, {"min_level": 1})
        return level >= reqs["min_level"]

    # Weapons
    weapons = list(equipment.get("weapons", []))
    weapons.extend(equipment.get("signature_weapons", []))
    for weapon in weapons:
        weapon_name = weapon.get("name") or weapon.get("themed_name", "Unknown Weapon")
        weapon_props = weapon.get("properties", [])
        is_finesse = "finesse" in [p.lower() for p in weapon_props] if weapon_props else False
        is_ranged = (
            weapon.get("weapon_type", "").endswith("_ranged") or weapon.get("type") == "ranged"
        )

        if is_ranged:
            attack_mod = dex_mod
        elif is_finesse:
            attack_mod = max(str_mod, dex_mod)
        else:
            attack_mod = str_mod

        magic_bonus = weapon.get("magic_bonus", 0)
        attack_bonus = attack_mod + prof_bonus + magic_bonus
        damage_bonus = attack_mod + magic_bonus

        weapon_rarity = weapon.get("rarity", "common")
        unlock_reqs = RARITY_UNLOCK_REQUIREMENTS.get(weapon_rarity, {"min_level": 1, "min_xp": 0})

        weapon_mastery = weapon.get("mastery")
        if not weapon_mastery and weapon.get("base_weapon"):
            weapon_mastery = WEAPON_MASTERY_MAP.get(weapon["base_weapon"].lower())
        if not weapon_mastery:
            weapon_mastery = WEAPON_MASTERY_MAP.get(weapon_name.lower())

        # rule-text join for the equipped weapon's
        # mastery. `mastery_description` is null for weapons with no
        # mastery (simple 2024 weapons) AND for weapons with a mastery
        # label that isn't in the descriptions map (typos / unknown).
        # `mastery_unknown` distinguishes the two — when true, the
        # frontend surfaces an "unknown mastery" warning rather than
        # silently rendering a blank cell (anti-pattern #7).
        mastery_description = (
            WEAPON_MASTERY_DESCRIPTIONS.get(weapon_mastery) if weapon_mastery else None
        )
        mastery_unknown = weapon_mastery is not None and mastery_description is None

        equipment_info["weapons"].append(
            {
                "name": weapon_name,
                "attack_bonus": _fmt(attack_bonus),
                "damage": weapon.get("damage", "1d6"),
                "damage_type": weapon.get("damage_type", "bludgeoning"),
                "damage_bonus": _fmt(damage_bonus) if damage_bonus != 0 else "",
                "properties": weapon_props,
                "mastery": weapon_mastery,
                "mastery_description": mastery_description,
                "mastery_unknown": mastery_unknown,
                "magic_bonus": magic_bonus,
                "description": weapon.get("description"),
                "lore": weapon.get("lore"),
                "appearance": weapon.get("appearance"),
                "rarity": weapon_rarity,
                "requires_attunement": weapon.get("requires_attunement", False),
                "special_abilities": weapon.get("special_abilities", []),
                "is_signature": weapon.get("is_signature", False),
                "symbolism": weapon.get("symbolism", []),
                "base_weapon": weapon.get("base_weapon"),
                "unlock_level": unlock_reqs["min_level"],
                "unlock_xp": unlock_reqs["min_xp"],
                "is_locked": not _is_unlocked(weapon_rarity),
            }
        )

    # Armor
    armor = equipment.get("armor")
    if armor:
        armor_type = (
            (armor.get("type") or armor.get("armor_type") or armor.get("base_armor") or "none")
            .lower()
            .replace(" ", "_")
        )
        base_armor_ac = ARMOR_BASE_AC.get(armor_type, armor.get("base_ac", 10))
        max_dex = ARMOR_MAX_DEX.get(armor_type, armor.get("max_dex_bonus"))

        if max_dex == 0:
            armor_ac = base_armor_ac
        elif max_dex is not None:
            armor_ac = base_armor_ac + min(dex_mod, max_dex)
        else:
            armor_ac = base_armor_ac + dex_mod
        armor_ac += armor.get("magic_bonus", 0)

        armor_rarity = armor.get("rarity", "common")
        armor_unlock_reqs = RARITY_UNLOCK_REQUIREMENTS.get(
            armor_rarity, {"min_level": 1, "min_xp": 0}
        )

        equipment_info["armor"] = {
            "name": armor.get("name") or armor.get("themed_name", "Armor"),
            "ac": armor_ac,
            "type": armor_type,
            "base_ac": base_armor_ac,
            "magic_bonus": armor.get("magic_bonus", 0),
            "description": armor.get("description"),
            "appearance": armor.get("appearance"),
            "rarity": armor_rarity,
            "is_signature": armor.get("is_signature", False),
            "unlock_level": armor_unlock_reqs["min_level"],
            "unlock_xp": armor_unlock_reqs["min_xp"],
            "is_locked": not _is_unlocked(armor_rarity),
        }

    # Shield
    if equipment.get("shield"):
        equipment_info["shield"] = True

    # Other
    equipment_info["other"] = equipment.get("other_equipment", [])
    equipment_info["currency"] = equipment.get("currency", {"gp": 0})

    return equipment_info


def _build_personality(narrative: dict | None) -> dict:
    """Build personality dict from narrative data."""
    personality = {
        "traits": [],
        "ideals": [],
        "bonds": [],
        "flaws": [],
        "backstory": "",
    }
    if narrative:
        pers = narrative.get("personality", {})
        personality["traits"] = pers.get("traits", [])
        personality["ideals"] = pers.get("ideals", [])
        personality["bonds"] = pers.get("bonds", [])
        personality["flaws"] = pers.get("flaws", [])
        backstory_obj = narrative.get("backstory", {})
        if isinstance(backstory_obj, dict):
            personality["backstory"] = backstory_obj.get("full_narrative", "")
        else:
            personality["backstory"] = str(backstory_obj) if backstory_obj else ""
    return personality
