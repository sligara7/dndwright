"""Validators for homebrew-generated D&D 5e 2024 components.

Each validator takes a plain dict (the LLM's normalized output) and returns
a list of human-readable problem strings. An empty list means the component
is mechanically legal.

These are structural rules checks — does the component obey the D&D 5e 2024
mechanical framework? They do NOT replace the computation DAG (evaluate_character)
which handles derived stats.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

VALID_HIT_DICE = {6, 8, 10, 12}

STRONG_SAVES = {"dexterity", "constitution", "wisdom"}
WEAK_SAVES = {"strength", "intelligence", "charisma"}
ALL_ABILITIES = STRONG_SAVES | WEAK_SAVES

VALID_ARCHETYPES = {
    "full_martial", "skill_martial", "full_caster", "half_caster",
    "pact_caster", "expert", "priest", "arcane", "warlock", "support_caster",
}

VALID_SPELLCASTING_TYPES = {"none", "full_caster", "half_caster", "pact_caster"}

VALID_CREATURE_TYPES = {
    "Aberration", "Beast", "Celestial", "Construct", "Dragon",
    "Elemental", "Fey", "Fiend", "Giant", "Humanoid",
    "Monstrosity", "Ooze", "Plant", "Undead",
}

VALID_SIZES = {"Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"}

# Speeds D&D 5e 2024 PHB species typically stay within (ft)
MAX_WALK_SPEED = 50
MAX_FLY_SPEED = 60
MAX_SWIM_SPEED = 60
MAX_CLIMB_SPEED = 40
MAX_BURROW_SPEED = 30

# ---------------------------------------------------------------------------
# Class validator
# ---------------------------------------------------------------------------


def validate_class_homebrew(class_data: dict[str, Any]) -> list[str]:
    """Validate a homebrew class against 5e 2024 structural rules."""
    problems: list[str] = []

    # --- Hit die ---
    hit_die = class_data.get("hit_die")
    if hit_die is None:
        problems.append("Missing hit_die")
    elif not isinstance(hit_die, int) or hit_die not in VALID_HIT_DICE:
        problems.append(f"Invalid hit_die: {hit_die} (must be one of {sorted(VALID_HIT_DICE)})")

    # --- Saving throw proficiencies ---
    saves: list[str] = class_data.get("saving_throw_proficiencies") or class_data.get("saving_throws") or []
    if len(saves) != 2:
        problems.append(f"Must have exactly 2 saving throw proficiencies, got {len(saves)}: {saves}")
    else:
        if not isinstance(saves, list):
            problems.append(f"saving_throw_proficiencies must be a list, got {type(saves).__name__}")
        else:
            unknown = [s for s in saves if s not in ALL_ABILITIES]
            if unknown:
                problems.append(f"Unknown ability in saving throws: {unknown}")
            if not (set(saves) & STRONG_SAVES and set(saves) & WEAK_SAVES):
                problems.append(
                    f"Must have one strong ({sorted(STRONG_SAVES)}) and one weak "
                    f"({sorted(WEAK_SAVES)}) save proficiency, got {saves}"
                )

    # --- Archetype ---
    archetype = class_data.get("archetype", "")
    if archetype and archetype not in VALID_ARCHETYPES:
        problems.append(
            f"Invalid archetype: '{archetype}' "
            f"(must be one of {sorted(VALID_ARCHETYPES)})"
        )

    # --- Spellcasting consistency ---
    spellcasting_type = class_data.get("spellcasting_type", "none")
    if spellcasting_type not in VALID_SPELLCASTING_TYPES:
        problems.append(
            f"Invalid spellcasting_type: '{spellcasting_type}' "
            f"(must be one of {sorted(VALID_SPELLCASTING_TYPES)})"
        )
    spellcasting_ability = class_data.get("spellcasting_ability")
    if spellcasting_type != "none":
        if not spellcasting_ability:
            problems.append(
                f"Spellcasting class (type={spellcasting_type}) is missing spellcasting_ability"
            )
        elif spellcasting_ability not in ALL_ABILITIES:
            problems.append(f"Invalid spellcasting_ability: '{spellcasting_ability}'")
    else:
        # Non-spellcaster shouldn't have a spellcasting ability set
        if spellcasting_ability and spellcasting_ability in ALL_ABILITIES:
            problems.append(
                f"Non-spellcaster has spellcasting_ability='{spellcasting_ability}' set"
            )

    # --- Progression ---
    progression: list[dict] = (
        class_data.get("progression")
        or class_data.get("progression_table")
        or []
    )
    if progression:
        seen_levels: set[int] = set()
        for feature in progression:
            if not isinstance(feature, dict):
                problems.append(f"Progression feature is not a dict: {feature}")
                continue
            level = feature.get("level")
            if not isinstance(level, int):
                problems.append(
                    f"Feature '{feature.get('name', '?')}' has non-integer level: {level}"
                )
                continue
            if not (1 <= level <= 20):
                problems.append(
                    f"Feature '{feature.get('name', '?')}' has level {level} (must be 1-20)"
                )
            if level in seen_levels:
                problems.append(
                    f"Multiple features at level {level}: {feature.get('name', '?')}"
                )
            seen_levels.add(level)

    return problems


# ---------------------------------------------------------------------------
# Species validator
# ---------------------------------------------------------------------------


def validate_species_homebrew(species_data: dict[str, Any]) -> list[str]:
    """Validate a homebrew species against 5e 2024 structural rules."""
    problems: list[str] = []

    # --- Size ---
    size = species_data.get("size", "")
    if size and size.title() not in VALID_SIZES:
        problems.append(f"Invalid size: '{size}' (must be one of {sorted(VALID_SIZES)})")

    # --- Creature type ---
    creature_type = species_data.get("creature_type", "")
    if creature_type and creature_type.title() not in VALID_CREATURE_TYPES:
        problems.append(
            f"Invalid creature_type: '{creature_type}' "
            f"(must be one of {sorted(VALID_CREATURE_TYPES)})"
        )

    # --- Speed ---
    speed = species_data.get("speed")
    if isinstance(speed, dict):
        walk = speed.get("walk", speed.get("base", 0))
        if isinstance(walk, int) and walk > MAX_WALK_SPEED:
            problems.append(
                f"Walk speed {walk}ft exceeds typical max {MAX_WALK_SPEED}ft for species"
            )
        for speed_type, limit in [
            ("fly", MAX_FLY_SPEED), ("swim", MAX_SWIM_SPEED),
            ("climb", MAX_CLIMB_SPEED), ("burrow", MAX_BURROW_SPEED),
        ]:
            val = speed.get(speed_type)
            if isinstance(val, int) and val > limit:
                problems.append(
                    f"{speed_type.title()} speed {val}ft exceeds typical max {limit}ft for species"
                )

    # --- Innate spellcasting sanity ---
    innate = species_data.get("innate_spellcasting")
    if isinstance(innate, dict):
        spells = innate.get("spells", [])
        if isinstance(spells, list):
            max_spell_level = max((s.get("level", 0) for s in spells if isinstance(s, dict)), default=0)
            if max_spell_level > 5:
                problems.append(
                    f"Innate spellcasting includes level {max_spell_level} spell — "
                    f"species innate spells rarely exceed 3rd level"
                )

    # --- Traits ---
    traits = species_data.get("traits", [])
    if isinstance(traits, list):
        for trait in traits:
            if not isinstance(trait, dict):
                problems.append(f"Species trait is not a dict: {trait}")
                continue
            name = trait.get("name", "?")
            if not isinstance(name, str) or not name.strip():
                problems.append(f"Species trait missing name")

    return problems


# ---------------------------------------------------------------------------
# Subclass validator
# ---------------------------------------------------------------------------


def validate_subclass_homebrew(subclass_data: dict[str, Any]) -> list[str]:
    """Validate a homebrew subclass against 5e 2024 structural rules."""
    problems: list[str] = []

    # --- Archetype ---
    archetype = subclass_data.get("subclass_archetype", subclass_data.get("archetype", ""))
    if archetype and archetype not in {
        "damage_dealer", "tank_protector", "support", "control", "healer",
        "full_martial", "skill_martial", "half_caster", "full_caster", "pact_caster",
        "expert", "priest", "arcane", "warlock", "support_caster",
    }:
        problems.append(f"Invalid subclass_archetype: '{archetype}'")

    # --- Features ---
    features: list[dict] = subclass_data.get("features", [])
    if isinstance(features, list):
        subclass_levels: set[int] = set()
        for feature in features:
            if not isinstance(feature, dict):
                problems.append(f"Subclass feature is not a dict: {feature}")
                continue
            level = feature.get("level")
            if not isinstance(level, int):
                problems.append(
                    f"Feature '{feature.get('name', '?')}' has non-integer level: {level}"
                )
                continue
            if not (1 <= level <= 20):
                problems.append(
                    f"Feature '{feature.get('name', '?')}' has level {level} (must be 1-20)"
                )
            # Standard 2024 subclass feature levels are 3, 6, 10, 14, 17
            if level in subclass_levels:
                problems.append(
                    f"Multiple features at level {level}: {feature.get('name', '?')}"
                )
            subclass_levels.add(level)
        if len(features) < 2:
            problems.append(
                f"Subclass has only {len(features)} feature(s) — "
                f"standard 2024 subclasses have 4-5 features"
            )

    # --- Domain spells (optional) ---
    domain_spells = subclass_data.get("domain_spells", [])
    if isinstance(domain_spells, list):
        for entry in domain_spells:
            if not isinstance(entry, dict):
                problems.append(f"Domain spell entry is not a dict: {entry}")
                continue
            spell_level = entry.get("spell_level", entry.get("level"))
            if isinstance(spell_level, int) and not (1 <= spell_level <= 9):
                problems.append(f"Domain spell has invalid level: {spell_level}")

    return problems


# ---------------------------------------------------------------------------
# Background validator
# ---------------------------------------------------------------------------


def validate_background_homebrew(background_data: dict[str, Any]) -> list[str]:
    """Validate a homebrew background against 5e 2024 structural rules."""
    problems: list[str] = []

    # --- Skill proficiencies (exactly 2) ---
    skills: list[str] = background_data.get("skill_proficiencies", [])
    if not isinstance(skills, list):
        problems.append(
            f"skill_proficiencies must be a list, got {type(skills).__name__}"
        )
    elif len(skills) != 2:
        problems.append(
            f"Background must have exactly 2 skill proficiencies, got {len(skills)}: {skills}"
        )

    # --- Ability score increases ---
    increases = background_data.get("ability_score_increases", {})
    if isinstance(increases, dict):
        total = sum(v for v in increases.values() if isinstance(v, int))
        if total > 3:
            problems.append(
                f"Ability score increases total {total} exceeds 2024 background max of +3: {increases}"
            )
        unknown = [k for k in increases if k not in ALL_ABILITIES]
        if unknown:
            problems.append(f"Unknown ability in score increases: {unknown}")

    # --- Origin feat ---
    origin_feat = background_data.get("origin_feat", "")
    if not origin_feat or not isinstance(origin_feat, str) or not origin_feat.strip():
        problems.append("Background is missing origin_feat")

    return problems


# ---------------------------------------------------------------------------
# Aggregate validator
# ---------------------------------------------------------------------------

VALIDATORS: dict[str, Any] = {
    "class": validate_class_homebrew,
    "species": validate_species_homebrew,
    "subclass": validate_subclass_homebrew,
    "background": validate_background_homebrew,
}


def validate_homebrew(
    component_type: str, component_data: dict[str, Any]
) -> list[str]:
    """Route to the appropriate validator."""
    validator = VALIDATORS.get(component_type)
    if validator is None:
        return [f"Unknown component type: {component_type}"]
    return validator(component_data)
