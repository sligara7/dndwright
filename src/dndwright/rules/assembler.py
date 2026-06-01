"""Character assembler — combines component mechanics into graph inputs.

Takes ClassMechanics + SpeciesMechanics + BackgroundMechanics + SubclassMechanics
(+ equipped items, feats) and produces the flat input dict for the evaluator.

The assembler is the ONLY place where component mechanics get translated
into computation graph node values. No other code should manually set
graph inputs.

Usage:
    from rules.assembler import assemble_character_inputs
    from rules.evaluator import evaluate
    from rules.dnd_5e_2024 import DND_5E_2024_RULESET

    inputs = assemble_character_inputs(
        class_mechanics=class_mech,
        species_mechanics=species_mech,
        background_mechanics=bg_mech,
        ability_scores={"strength": 16, ...},
        level=5,
    )
    computed = evaluate(DND_5E_2024_RULESET, inputs)
"""

from __future__ import annotations

from typing import Any

from .components import (
    ArmorMechanics,
    BackgroundMechanics,
    ClassMechanics,
    CreatureMechanics,
    FeatMechanics,
    NodeModifier,
    SpeciesMechanics,
    SubclassMechanics,
)
from .lookup_tables import (
    SKILL_ABILITY_MAP,
)


def assemble_character_inputs(
    class_mechanics: ClassMechanics,
    species_mechanics: SpeciesMechanics | None = None,
    subclass_mechanics: SubclassMechanics | None = None,
    background_mechanics: BackgroundMechanics | None = None,
    ability_scores: dict[str, int] | None = None,
    level: int = 1,
    class_name: str = "",
    # Multiclass support
    additional_classes: dict[str, ClassMechanics] | None = None,
    additional_class_levels: dict[str, int] | None = None,
    # Equipment
    equipped_armor: ArmorMechanics | None = None,
    has_shield: bool = False,
    # Feats
    feats: list[FeatMechanics] | None = None,
) -> dict[str, Any]:
    """Assemble all component mechanics into a flat graph input dict.

    This is the single point of truth for translating D&D component
    choices into computation graph inputs.

    Returns:
        Dict keyed by computation node IDs, ready for evaluate().
    """
    inputs: dict[str, Any] = {}
    scores = ability_scores or {
        "strength": 10, "dexterity": 10, "constitution": 10,
        "intelligence": 10, "wisdom": 10, "charisma": 10,
    }

    # ------------------------------------------------------------------
    # 1. Background ability score increases (applied BEFORE setting scores)
    # ------------------------------------------------------------------
    if background_mechanics:
        for ability, increase in background_mechanics.ability_score_increases.items():
            if ability in scores:
                scores = dict(scores)  # copy to avoid mutating original
                scores[ability] = scores[ability] + increase

    # ------------------------------------------------------------------
    # 2. Feat ability score increases
    # ------------------------------------------------------------------
    if feats:
        for feat in feats:
            for ability, increase in feat.grants_ability_increase.items():
                if ability in scores:
                    scores = dict(scores)
                    scores[ability] = scores[ability] + increase

    # ------------------------------------------------------------------
    # 3. Ability scores → graph inputs
    # ------------------------------------------------------------------
    for ability in ("strength", "dexterity", "constitution",
                    "intelligence", "wisdom", "charisma"):
        inputs[f"{ability}_score"] = scores.get(ability, 10)

    # ------------------------------------------------------------------
    # 4. Level and class structure
    # ------------------------------------------------------------------
    cn = class_name.lower()
    inputs["character_level"] = level
    inputs["primary_class"] = cn

    # Build class_levels and class_hit_dice for multiclass
    class_levels: dict[str, int] = {}
    class_hit_dice: dict[str, int] = {}
    class_spellcasting_types: dict[str, str] = {}

    if additional_classes and additional_class_levels:
        # Multiclass — primary class gets remaining levels
        other_levels = sum(additional_class_levels.values())
        class_levels[cn] = max(level - other_levels, 1)
        class_hit_dice[cn] = class_mechanics.hit_die
        class_spellcasting_types[cn] = class_mechanics.spellcasting_type
        for other_name, other_mech in additional_classes.items():
            other_cn = other_name.lower()
            class_levels[other_cn] = additional_class_levels.get(other_name, 1)
            class_hit_dice[other_cn] = other_mech.hit_die
            class_spellcasting_types[other_cn] = other_mech.spellcasting_type
    else:
        # Single class
        class_levels[cn] = level
        class_hit_dice[cn] = class_mechanics.hit_die
        class_spellcasting_types[cn] = class_mechanics.spellcasting_type

    inputs["class_levels"] = class_levels
    inputs["class_hit_dice"] = class_hit_dice
    inputs["class_spellcasting_types"] = class_spellcasting_types

    # ------------------------------------------------------------------
    # 5. Spellcasting
    # ------------------------------------------------------------------
    inputs["spellcasting_type"] = class_mechanics.spellcasting_type

    # ------------------------------------------------------------------
    # 6. Speed (from species)
    # ------------------------------------------------------------------
    if species_mechanics:
        inputs["speed_base"] = species_mechanics.speed.walk
    else:
        inputs["speed_base"] = 30

    # ------------------------------------------------------------------
    # 7. Equipment → AC inputs
    # ------------------------------------------------------------------
    if equipped_armor:
        inputs["armor_type"] = equipped_armor.armor_type
        inputs["armor_magic_bonus"] = equipped_armor.magic_bonus
    else:
        inputs["armor_type"] = "none"
        inputs["armor_magic_bonus"] = 0
    inputs["has_shield"] = has_shield

    # ------------------------------------------------------------------
    # 8. Saving throw proficiencies
    # ------------------------------------------------------------------
    save_profs: set[str] = set(class_mechanics.saving_throw_proficiencies)
    # Subclass might grant additional saves (rare but possible)
    if subclass_mechanics:
        for feat_mech in subclass_mechanics.features:
            for prof in feat_mech.grants_proficiency:
                if prof in ("strength", "dexterity", "constitution",
                            "intelligence", "wisdom", "charisma"):
                    save_profs.add(prof)

    for ability in ("strength", "dexterity", "constitution",
                    "intelligence", "wisdom", "charisma"):
        inputs[f"save.{ability}.proficient"] = ability in save_profs

    # ------------------------------------------------------------------
    # 9. Skill proficiencies (aggregated from all sources)
    # ------------------------------------------------------------------
    skill_profs: set[str] = set()
    expertise_skills: set[str] = set()

    # From class
    # Note: class provides OPTIONS, not all of them. The user picks
    # skill_proficiency_count from skill_proficiency_options.
    # For the assembler, we accept a pre-selected set. If not provided,
    # we use whatever the class offers (for backwards compat).
    for skill in class_mechanics.skill_proficiency_options:
        skill_profs.add(skill.lower().replace(" ", "_"))

    # From background
    if background_mechanics:
        for skill in background_mechanics.skill_proficiencies:
            skill_profs.add(skill.lower().replace(" ", "_"))

    # From species
    if species_mechanics:
        for skill in species_mechanics.skill_proficiencies:
            skill_profs.add(skill.lower().replace(" ", "_"))

    # From subclass
    if subclass_mechanics:
        for prof in subclass_mechanics.bonus_proficiencies:
            normalized = prof.lower().replace(" ", "_")
            if normalized in SKILL_ABILITY_MAP:
                skill_profs.add(normalized)

        # Features can grant proficiency or expertise
        for feat_mech in subclass_mechanics.features:
            if feat_mech.level <= level:
                for prof in feat_mech.grants_proficiency:
                    normalized = prof.lower().replace(" ", "_")
                    if normalized in SKILL_ABILITY_MAP:
                        skill_profs.add(normalized)
                for exp in feat_mech.grants_expertise:
                    expertise_skills.add(exp.lower().replace(" ", "_"))

    # From class features at current level
    for feat_mech in class_mechanics.progression:
        if feat_mech.level <= level:
            for prof in feat_mech.grants_proficiency:
                normalized = prof.lower().replace(" ", "_")
                if normalized in SKILL_ABILITY_MAP:
                    skill_profs.add(normalized)
            for exp in feat_mech.grants_expertise:
                expertise_skills.add(exp.lower().replace(" ", "_"))

    # From feats
    if feats:
        for feat in feats:
            for prof in feat.grants_proficiency:
                normalized = prof.lower().replace(" ", "_")
                if normalized in SKILL_ABILITY_MAP:
                    skill_profs.add(normalized)

    for skill in SKILL_ABILITY_MAP:
        inputs[f"skill.{skill}.proficient"] = skill in skill_profs
        inputs[f"skill.{skill}.expertise"] = skill in expertise_skills

    # ------------------------------------------------------------------
    # 10. Collect NodeModifiers from all components
    # ------------------------------------------------------------------
    modifiers = _collect_modifiers(
        class_mechanics=class_mechanics,
        species_mechanics=species_mechanics,
        subclass_mechanics=subclass_mechanics,
        feats=feats,
        level=level,
    )
    # Store modifiers for post-evaluation application
    inputs["_node_modifiers"] = modifiers

    return inputs


def apply_modifiers(
    computed: dict[str, Any],
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """Apply NodeModifiers to computed values after graph evaluation.

    Some features/feats/traits add flat bonuses to computed values
    (e.g., Alert feat adds +5 to initiative). These are applied AFTER
    the base graph evaluation.

    Returns a new dict with modifiers applied.
    """
    modifiers: list[NodeModifier] = inputs.get("_node_modifiers", [])
    if not modifiers:
        return computed

    result = dict(computed)
    for mod in modifiers:
        if mod.target_node not in result:
            continue

        current = result[mod.target_node]
        if current is None:
            continue

        if mod.op == "add" and isinstance(current, (int, float)):
            result[mod.target_node] = current + mod.value
        elif mod.op == "set":
            result[mod.target_node] = mod.value
        elif mod.op == "max" and isinstance(current, (int, float)):
            result[mod.target_node] = max(current, mod.value)
        elif mod.op == "min" and isinstance(current, (int, float)):
            result[mod.target_node] = min(current, mod.value)
        elif mod.op == "multiply" and isinstance(current, (int, float)):
            result[mod.target_node] = current * mod.value

    return result


def _collect_modifiers(
    class_mechanics: ClassMechanics,
    species_mechanics: SpeciesMechanics | None,
    subclass_mechanics: SubclassMechanics | None,
    feats: list[FeatMechanics] | None,
    level: int,
) -> list[NodeModifier]:
    """Collect all NodeModifiers from all components, filtered by level."""
    modifiers: list[NodeModifier] = []

    # Class features at or below current level
    for feat_mech in class_mechanics.progression:
        if feat_mech.level <= level:
            modifiers.extend(feat_mech.modifies_node)

    # Species traits (always active)
    if species_mechanics:
        for trait in species_mechanics.traits:
            modifiers.extend(trait.modifies_node)

    # Subclass features at or below current level
    if subclass_mechanics:
        for feat_mech in subclass_mechanics.features:
            if feat_mech.level <= level:
                modifiers.extend(feat_mech.modifies_node)

    # Feats (always active once taken)
    if feats:
        for feat in feats:
            modifiers.extend(feat.modifies_node)

    return modifiers


def assemble_creature_inputs(
    mechanics: CreatureMechanics,
) -> dict[str, Any]:
    """Assemble creature mechanics into graph inputs for a creature ruleset.

    Creatures use a different graph than characters (CR-based proficiency,
    size-based hit dice, no class levels).
    """

    inputs: dict[str, Any] = {}

    # Ability scores
    for ability in ("strength", "dexterity", "constitution",
                    "intelligence", "wisdom", "charisma"):
        inputs[f"{ability}_score"] = mechanics.ability_scores.get(ability, 10)

    # CR and size
    inputs["cr"] = mechanics.cr
    inputs["cr_numeric"] = mechanics.cr_numeric
    inputs["size"] = mechanics.size
    inputs["creature_type"] = mechanics.creature_type
    inputs["hp_dice_count"] = mechanics.hp_dice_count

    # AC (for creatures, AC is an independent value — includes natural armor)
    inputs["ac"] = mechanics.ac
    inputs["ac_type"] = mechanics.ac_type

    # Speed
    inputs["speed_walk"] = mechanics.speed.walk
    inputs["speed_fly"] = mechanics.speed.fly
    inputs["speed_swim"] = mechanics.speed.swim
    inputs["speed_climb"] = mechanics.speed.climb
    inputs["speed_burrow"] = mechanics.speed.burrow

    # Save proficiencies
    for ability in ("strength", "dexterity", "constitution",
                    "intelligence", "wisdom", "charisma"):
        inputs[f"save.{ability}.proficient"] = (
            ability in mechanics.saving_throw_proficiencies
        )

    # Skill proficiencies
    for skill in SKILL_ABILITY_MAP:
        inputs[f"skill.{skill}.proficient"] = (
            skill in [s.lower().replace(" ", "_") for s in mechanics.skill_proficiencies]
        )

    # Boss features
    inputs["legendary_action_count"] = mechanics.legendary_action_count
    inputs["legendary_resistances"] = mechanics.legendary_resistances

    return inputs
