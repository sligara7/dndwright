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


def _coerce_hit_die(value: Any) -> int | None:
    """Coerce a hit die to its integer faces, or ``None`` if unparseable.

    Accepts the integer form (``8``) and the canonical dice-string form
    (``"d8"``, case-insensitive) — ``CharClass.hit_die`` is typed ``str``
    ("d6".."d12") and normalized homebrew output carries the string, so the
    validator must understand both. ``bool`` is rejected (it is an ``int``
    subclass but never a valid die).
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        faces = value.strip().lower().lstrip("d")
        if faces.isdigit():
            return int(faces)
    return None


# ---------------------------------------------------------------------------
# Class validator
# ---------------------------------------------------------------------------


def validate_class_homebrew(class_data: dict[str, Any]) -> list[str]:
    """Validate a homebrew class against 5e 2024 structural rules."""
    problems: list[str] = []

    # --- Hit die ---
    # Accept both the integer form (8) and the canonical dice-string form
    # ("d8"); ``CharClass.hit_die`` is typed ``str`` and normalized homebrew
    # output carries the string, so coerce "dN" -> N before the range check.
    raw_hit_die = class_data.get("hit_die")
    hit_die = _coerce_hit_die(raw_hit_die)
    if raw_hit_die is None:
        problems.append("Missing hit_die")
    elif hit_die is None or hit_die not in VALID_HIT_DICE:
        problems.append(
            f"Invalid hit_die: {raw_hit_die!r} "
            f"(must be one of {sorted(VALID_HIT_DICE)} or 'd6'/'d8'/'d10'/'d12')"
        )

    # --- Saving throw proficiencies ---
    # Ability names are compared case-insensitively: the canonical model and the
    # normalized homebrew output capitalize them ("Strength"), while the SRD
    # ability sets here are lowercase.
    raw_saves = class_data.get("saving_throw_proficiencies") or class_data.get("saving_throws") or []
    if not isinstance(raw_saves, list):
        problems.append(f"saving_throw_proficiencies must be a list, got {type(raw_saves).__name__}")
    elif len(raw_saves) != 2:
        problems.append(f"Must have exactly 2 saving throw proficiencies, got {len(raw_saves)}: {raw_saves}")
    else:
        saves = [str(s).strip().lower() for s in raw_saves]
        unknown = [orig for orig, s in zip(raw_saves, saves) if s not in ALL_ABILITIES]
        if unknown:
            problems.append(f"Unknown ability in saving throws: {unknown}")
        elif not (set(saves) & STRONG_SAVES and set(saves) & WEAK_SAVES):
            problems.append(
                f"Must have one strong ({sorted(STRONG_SAVES)}) and one weak "
                f"({sorted(WEAK_SAVES)}) save proficiency, got {raw_saves}"
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
                problems.append("Species trait missing name")

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
# SRD power-budget baselines (derived from dndwright content)
# ---------------------------------------------------------------------------
# Derived 2026-06-13 from:
#   content/species.json — 9 SRD 5.2.1 species (3-5 traits, avg 3.6; 0-4
#     high-impact traits, median 1-2)
#   content/classes.json — 12 SRD 5.2.1 classes (baseline, subclass, &
#     subclass_features arrays; cumulative features active at each level)
#
# Methodology: for each source file, count traits / features per entity,
# record the distribution, set the budget slightly above the SRD maximum
# to allow homebrew creativity while catching obvious over-stacking (e.g. a
# character with 8 species traits + 10 class features at level 1).

# --- Species baseline -------------------------------------------------------
# SRD trait counts: Dragonborn 4, Dwarf 4, Elf 5, Gnome 3, Goliath 3,
# Halfling 4, Human 3, Orc 3, Tiefling 3.  Budget = 5 (1 above SRD max).
_SPECIES_TRAIT_MAX = 5

# High-impact trait count per SRD species (flight, innate spellcasting,
# resistance/immunity, breath weapons, darkvision, tremorsense/blindsight,
# regeneration, legendary/magic resistance):
#   Dragonborn 4, Dwarf 3, Elf 2, Gnome 1, Goliath 0, Halfling 0,
#   Human 0, Orc 1, Tiefling 3.
# Budget = 3 (1 above the SRD median of 1-2; Dragonborn at 4 is the outlier).
_SPECIES_HIGH_IMPACT_MAX = 3

# --- Class+subclass feature budget by level ----------------------------------
# Cumulative features (base + subclass) active AT a given level, across
# 12 SRD classes at key checkpoints (1/3/5/10/20).  Budget = MAX at that
# level across all 12 classes (rounded up to the nearest integer).
_CLASS_FEATURE_BUDGET: dict[int, int] = {
    1: 4,
    3: 9,
    5: 12,
    10: 18,
    20: 26,
}

# Combined species-trait + class-feature total budget (Superman+Batman guard):
# Scales with level: SRD max species traits (5) + SRD max class features at that
# level.  A typical low-level character has ~7-9 total (3-4 species + 3-4 class).
# The raw 10-stack the user called out is caught at low levels; the budget
# loosens naturally as characters gain features through normal progression.
_COMBINED_BUDGET_BASE_SPECIES = 5  # species traits always 5 max
_COMBINED_BUDGET_EXTRA = 0         # no extra leniency — individual checks have margin

# Keywords that mark a trait as "high-impact" (affects combat math, survivability,
# or action economy, as opposed to cosmetic / ribbon abilities).
_HIGH_IMPACT_KEYWORDS = [
    "breath weapon", "damage resistance", "resistance", "immunity",
    "flight", "fly speed", "innate spellcasting", "spellcasting", "cantrip",
    "regeneration", "legendary resistance", "magic resistance",
    "tremorsense", "blindsight", "darkvision",
    "advantage on", "disadvantage on", "frightened", "charmed",
    "teleport", "ethereal", "incorporeal",
]


def _count_high_impact_traits(traits: list[dict]) -> int:
    """Count how many species traits match high-impact keywords."""
    count = 0
    for trait in traits:
        if not isinstance(trait, dict):
            continue
        name = (trait.get("name") or "").lower()
        desc = (trait.get("description") or "").lower()
        combined = name + " " + desc
        if any(kw in combined for kw in _HIGH_IMPACT_KEYWORDS):
            count += 1
    return count


def _class_feature_budget_for_level(level: int) -> int:
    """Return the SRD max combined class+subclass features at *level*.

    Uses linear interpolation between the checkpoint levels (1,3,5,10,20).
    """
    # Clamp
    level = max(1, min(level, 20))
    checkpoints = sorted(_CLASS_FEATURE_BUDGET.items())
    # Exact match
    for lvl, budget in checkpoints:
        if level == lvl:
            return budget
    # Interpolate
    lower_lvl = lower_budget = 0
    upper_lvl = upper_budget = 0
    for lvl, budget in checkpoints:
        if lvl < level:
            lower_lvl, lower_budget = lvl, budget
        elif lvl > level:
            upper_lvl, upper_budget = lvl, budget
            break
    if upper_lvl == 0:
        return checkpoints[-1][1]
    frac = (level - lower_lvl) / (upper_lvl - lower_lvl)
    return int(lower_budget + frac * (upper_budget - lower_budget) + 0.5)


def _combined_budget_for_level(level: int) -> int:
    """Return the combined species+class budget for *level*."""
    return _COMBINED_BUDGET_BASE_SPECIES + _class_feature_budget_for_level(level) + _COMBINED_BUDGET_EXTRA


# ---------------------------------------------------------------------------
# Power-budget validator
# ---------------------------------------------------------------------------


def validate_power_budget(
    species_data: dict[str, Any],
    class_data: dict[str, Any],
    subclass_data: dict[str, Any] | None = None,
    level: int = 1,
) -> list[str]:
    """Validate a homebrew character's combined power budget against SRD baselines.

    Checks:
    1. Species trait count vs. SRD species budget (max 5 total, 3 high-impact).
       High-impact traits (flight, innate casting, resistance, breath weapon,
       darkvision, etc.) are weighted more heavily than cosmetic ones.
    2. Class+subclass features active at *level* vs. SRD class budget for that
       level (max observed across 12 SRD classes, interpolated).
    3. Species-vs-learned split: total traits + features must stay within one
       character's combined budget (max 10).  The ``Superman(species) +
       Batman(class)`` concept stacking a full species kit AND a full class kit
       must NOT pass.

    Baselines derived 2026-06-13 from dndwright content/species.json (9 species)
    and content/classes.json (12 classes + subclasses).

    Args:
        species_data: The species dict (``traits`` array, optional
                      ``innate_spellcasting``).
        class_data: The class dict (``features`` / ``progression`` array).
        subclass_data: Optional subclass dict (``features`` array).
        level: Character level (1-20).

    Returns:
        List of human-readable problem strings.  ``[]`` = within budget.
        No silent coerce — overages are surfaced loudly, as the generate
        path must trim or the user must choose.
    """
    problems: list[str] = []

    # --- 1. Species trait budget ------------------------------------------------
    traits: list[dict] = species_data.get("traits", []) or []
    if not isinstance(traits, list):
        traits = []

    trait_count = len(traits)
    high_impact = _count_high_impact_traits(traits)

    # Also check innate_spellcasting as a separate high-impact indicator
    innate = species_data.get("innate_spellcasting")
    if isinstance(innate, dict):
        spells = innate.get("spells", [])
        if isinstance(spells, list) and spells:
            # Flag high-level innate spells independently
            max_spell_level = max(
                (s.get("level", s.get("spell_level", 0)) for s in spells if isinstance(s, dict)),
                default=0,
            )
            if max_spell_level >= 4:
                problems.append(
                    f"Species innate spellcasting includes level-{max_spell_level} spell — "
                    f"SRD species innate spells rarely exceed 3rd level"
                )

    if trait_count > _SPECIES_TRAIT_MAX:
        over = trait_count - _SPECIES_TRAIT_MAX
        problems.append(
            f"Species has {trait_count} traits (SRD budget: {_SPECIES_TRAIT_MAX} max). "
            f"{over} trait(s) over budget"
        )

    if high_impact > _SPECIES_HIGH_IMPACT_MAX:
        over = high_impact - _SPECIES_HIGH_IMPACT_MAX
        problems.append(
            f"Species has {high_impact} high-impact traits (SRD budget: {_SPECIES_HIGH_IMPACT_MAX} max). "
            f"{over} over budget: flight, innate casting, resistance, breath weapon, darkvision, "
            f"tremorsense/blindsight counted"
        )

    # --- 2. Class+subclass feature budget at this level ------------------------
    class_features: list[dict] = (
        class_data.get("features")
        or class_data.get("progression")
        or class_data.get("progression_table")
        or []
    )
    if not isinstance(class_features, list):
        class_features = []

    features_active = [f for f in class_features if isinstance(f, dict) and (f.get("level") or 999) <= level]
    class_count = len(features_active)

    subclass_count = 0
    if subclass_data:
        sub_features: list[dict] = subclass_data.get("features", []) or []
        if isinstance(sub_features, list):
            subclass_count = len(
                [f for f in sub_features if isinstance(f, dict) and (f.get("level") or 999) <= level]
            )

    total_class_features = class_count + subclass_count
    budget_for_level = _class_feature_budget_for_level(level)

    if total_class_features > budget_for_level:
        over = total_class_features - budget_for_level
        problems.append(
            f"Class+subclass has {total_class_features} features active at level {level} "
            f"({class_count} base + {subclass_count} subclass). "
            f"SRD budget for this level: {budget_for_level} max. {over} over budget"
        )

    # --- 3. Combined species-vs-learned split (Superman+Batman guard) ---------
    combined_budget = _combined_budget_for_level(level)
    combined = trait_count + total_class_features
    if combined > combined_budget:
        problems.append(
            f"Combined power budget exceeded: {trait_count} species traits + "
            f"{total_class_features} class features = {combined} total "
            f"(budget: {combined_budget} max). "
            f"Species-kit + class-kit stacking is not allowed — trim one side"
        )

    return problems


# ---------------------------------------------------------------------------
# Aggregate validator
# ---------------------------------------------------------------------------

VALIDATORS: dict[str, Any] = {
    "class": validate_class_homebrew,
    "species": validate_species_homebrew,
    "subclass": validate_subclass_homebrew,
    "background": validate_background_homebrew,
    "power_budget": validate_power_budget,
}


def validate_homebrew(
    component_type: str, component_data: dict[str, Any]
) -> list[str]:
    """Route to the appropriate validator.

    The ``power_budget`` type accepts ``component_data`` as the full character
    payload: ``{"species_data": ..., "class_data": ..., "subclass_data": ...,
    "level": ...}``.
    """
    validator = VALIDATORS.get(component_type)
    if validator is None:
        return [f"Unknown component type: {component_type}"]
    if component_type == "power_budget":
        return validator(**component_data)
    return validator(component_data)
