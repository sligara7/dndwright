"""Component mechanical and narrative schemas.

Each D&D character component (class, species, subclass, background) has:
  - A Mechanics model: the independent variables the LLM must decide.
    These feed directly into the computation graph as input overrides.
  - A Narrative model: flavor, lore, descriptions.
    These go to the knowledge graph (Neo4j), not the computation graph.

The LLM generates both, but they're cleanly separated. The computation
graph only ever sees Mechanics. The knowledge graph only ever sees Narrative.

Creature/monster stat blocks follow the same split.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# =============================================================================
# Shared types
# =============================================================================

AbilityName = Literal[
    "strength", "dexterity", "constitution",
    "intelligence", "wisdom", "charisma",
]

SpellcastingType = Literal[
    "none", "full_caster", "half_caster", "pact_caster",
]

DieSize = Literal[6, 8, 10, 12]

CreatureSize = Literal["Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"]


# =============================================================================
# Resource Mechanic (class-specific resource like Ki, Rage, Sorcery Points)
# =============================================================================


class ResourceMechanic(BaseModel):
    """A class's unique resource pool. Mechanical definition only."""

    starting_amount: int = Field(ge=0, description="Amount at level 1")
    max_amount: int = Field(ge=0, description="Amount at level 20")
    recovery: Literal["short_rest", "long_rest"] = "short_rest"
    scaling: str = Field(
        default="",
        description="Brief rule for how it scales, e.g. 'equal to class level'",
    )


class ResourceNarrative(BaseModel):
    """Narrative flavor for a class resource."""

    name: str = Field(description="Thematic name, e.g. 'Harmonics', 'Force Points'")
    usage_description: str = Field(
        description="What spending 1 point feels like narratively"
    )


# =============================================================================
# CLASS
# =============================================================================


class ClassMechanics(BaseModel):
    """Independent mechanical values for a character class.

    These are the ONLY values the LLM needs to decide for a class.
    Everything else (HP, proficiency bonus, save bonuses, spell save DC)
    is computed by the graph from these inputs.
    """

    hit_die: DieSize
    saving_throw_proficiencies: list[AbilityName] = Field(min_length=2, max_length=2)
    armor_proficiencies: list[str] = Field(default_factory=list)
    weapon_proficiencies: list[str] = Field(default_factory=list)
    skill_proficiency_options: list[str] = Field(default_factory=list)
    skill_proficiency_count: int = Field(default=2, ge=1, le=5)
    spellcasting_type: SpellcastingType = "none"
    spellcasting_ability: AbilityName | None = None
    resource_mechanic: ResourceMechanic | None = None
    archetype: str = Field(
        description="full_martial, skill_martial, primal_martial, "
        "half_caster, full_caster, pact_caster, support_caster"
    )

    # Level-gated features (mechanical effects only)
    progression: list[LevelFeatureMechanics] = Field(default_factory=list)


class LevelFeatureMechanics(BaseModel):
    """Mechanical effect of a class feature at a specific level.

    Only tracks what mechanically changes. The name and flavor text
    live in LevelFeatureNarrative.
    """

    level: int = Field(ge=1, le=20)
    feature_id: str = Field(description="Stable ID for this feature, e.g. 'extra_attack'")
    grants_proficiency: list[str] = Field(default_factory=list)
    grants_resistance: list[str] = Field(default_factory=list)
    grants_expertise: list[str] = Field(default_factory=list)
    modifies_node: list[NodeModifier] = Field(
        default_factory=list,
        description="Direct overrides to computation graph nodes",
    )


class NodeModifier(BaseModel):
    """A modifier that a feature/item/feat applies to a graph node.

    This is how mini-graphs plug into the main character graph.
    Example: Alert feat → NodeModifier(target_node="initiative", op="add", value=5)
    """

    target_node: str = Field(description="ID of the graph node to modify")
    op: Literal["add", "set", "max", "min", "multiply"] = "add"
    value: int | float | bool | str = Field(description="The modifier value")
    condition: str | None = Field(
        default=None,
        description="Optional condition, e.g. 'level >= 5'",
    )


class ClassNarrative(BaseModel):
    """Narrative/flavor content for a character class."""

    class_name: str
    description: str = Field(description="1-2 paragraph class fantasy")
    resource_narrative: ResourceNarrative | None = None
    progression_flavor: list[LevelFeatureNarrative] = Field(default_factory=list)
    signature_spell_lore: list[SpellNarrative] = Field(default_factory=list)


class LevelFeatureNarrative(BaseModel):
    """Name and flavor text for a class feature."""

    level: int = Field(ge=1, le=20)
    feature_id: str
    name: str
    description: str = Field(description="Narrative description of what this looks like")


class SpellNarrative(BaseModel):
    """Narrative content for a signature spell."""

    spell_id: str = Field(description="Stable ID matching a spell mechanics entry")
    themed_name: str
    lore: str = Field(description="1-2 paragraphs connecting spell to class identity")
    manifestation: str = Field(description="Visual description of casting")
    symbolism: list[str] = Field(default_factory=list)


class ClassGenerationOutput(BaseModel):
    """Complete LLM output for class generation — mechanics + narrative split."""

    mechanics: ClassMechanics
    narrative: ClassNarrative


# =============================================================================
# SPECIES
# =============================================================================


class SpeciesMechanics(BaseModel):
    """Independent mechanical values for a character species."""

    size: Literal["Small", "Medium"] = "Medium"
    creature_type: str = "Humanoid"
    speed: SpeciesSpeed = Field(default_factory=lambda: SpeciesSpeed())
    darkvision: int | None = Field(default=None, description="Darkvision range in feet")
    resistances: list[str] = Field(default_factory=list)
    damage_immunities: list[str] = Field(default_factory=list)
    condition_immunities: list[str] = Field(default_factory=list)
    skill_proficiencies: list[str] = Field(default_factory=list)
    tool_proficiencies: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=lambda: ["Common"])
    natural_weapons: list[NaturalWeaponMechanics] = Field(default_factory=list)
    traits: list[SpeciesTraitMechanics] = Field(default_factory=list)
    innate_spellcasting: InnateSpellcasting | None = None
    rest_type: Literal["standard", "trance", "sentry"] = "standard"


class SpeciesSpeed(BaseModel):
    """Movement speeds for a species."""

    walk: int = 30
    fly: int | None = None
    swim: int | None = None
    climb: int | None = None
    burrow: int | None = None


class NaturalWeaponMechanics(BaseModel):
    """Mechanical definition of a natural weapon."""

    weapon_id: str
    damage: str = Field(description="Damage dice, e.g. '1d6'")
    damage_type: str = "slashing"
    properties: list[str] = Field(default_factory=list)


class SpeciesTraitMechanics(BaseModel):
    """Mechanical effect of a species trait."""

    trait_id: str = Field(description="Stable ID, e.g. 'relentless_endurance'")
    action_type: Literal["passive", "action", "bonus_action", "reaction"] | None = None
    modifies_node: list[NodeModifier] = Field(default_factory=list)
    grants_proficiency: list[str] = Field(default_factory=list)
    grants_resistance: list[str] = Field(default_factory=list)
    uses_per_rest: int | None = Field(
        default=None, description="Uses before needing a rest"
    )
    recovery: Literal["short_rest", "long_rest"] | None = None


class InnateSpellcasting(BaseModel):
    """Innate spellcasting from species (not class)."""

    ability: AbilityName
    spells: list[InnateSpellMechanics] = Field(default_factory=list)


class InnateSpellMechanics(BaseModel):
    """Mechanical definition of an innate spell."""

    spell_id: str
    base_spell: str = Field(description="Official D&D spell name or 'custom'")
    level: int = Field(ge=0, le=9)
    uses_per_day: int | None = Field(
        default=None, description="None = at will (cantrips)"
    )


class SpeciesNarrative(BaseModel):
    """Narrative/flavor content for a species."""

    species_name: str
    description: str = Field(description="1-2 paragraphs on origin and nature")
    lifespan_description: str = ""
    trait_flavor: list[SpeciesTraitNarrative] = Field(default_factory=list)
    natural_weapon_flavor: list[NaturalWeaponNarrative] = Field(default_factory=list)
    innate_spell_lore: list[SpellNarrative] = Field(default_factory=list)
    lineages: list[LineageNarrative] = Field(default_factory=list)


class SpeciesTraitNarrative(BaseModel):
    """Name and flavor text for a species trait."""

    trait_id: str
    name: str
    description: str


class NaturalWeaponNarrative(BaseModel):
    """Flavor for a natural weapon."""

    weapon_id: str
    name: str
    description: str


class LineageNarrative(BaseModel):
    """A species sub-lineage with narrative features."""

    name: str
    description: str
    features: list[str] = Field(default_factory=list)


class SpeciesGenerationOutput(BaseModel):
    """Complete LLM output for species generation."""

    mechanics: SpeciesMechanics
    narrative: SpeciesNarrative


# =============================================================================
# SUBCLASS
# =============================================================================


class SubclassMechanics(BaseModel):
    """Independent mechanical values for a subclass."""

    subclass_archetype: str = Field(
        description="damage_dealer, tank_protector, support, control, healer"
    )
    bonus_proficiencies: list[str] = Field(default_factory=list)
    domain_spells: list[DomainSpellLevel] = Field(default_factory=list)
    features: list[LevelFeatureMechanics] = Field(default_factory=list)


class DomainSpellLevel(BaseModel):
    """Spells granted at a specific spell level."""

    spell_level: int = Field(ge=1, le=9)
    spells: list[str] = Field(description="Spell names granted")


class SubclassNarrative(BaseModel):
    """Narrative/flavor content for a subclass."""

    subclass_name: str
    description: str
    feature_flavor: list[LevelFeatureNarrative] = Field(default_factory=list)


class SubclassGenerationOutput(BaseModel):
    """Complete LLM output for subclass generation."""

    mechanics: SubclassMechanics
    narrative: SubclassNarrative


# =============================================================================
# BACKGROUND
# =============================================================================


class BackgroundMechanics(BaseModel):
    """Independent mechanical values for a background.

    Per D&D 2024 rules: 2 skills, 1 tool, ability score increases (+2/+1),
    1 origin feat, starting equipment.
    """

    skill_proficiencies: list[str] = Field(min_length=2, max_length=2)
    tool_proficiency: str = ""
    ability_score_increases: dict[AbilityName, int] = Field(
        default_factory=dict,
        description="Ability boosts, e.g. {'strength': 2, 'constitution': 1}",
    )
    origin_feat: str = Field(description="1st-level feat name")
    equipment: list[str] = Field(default_factory=list)


class BackgroundNarrative(BaseModel):
    """Narrative/flavor content for a background."""

    background_name: str
    description: str
    feature_name: str = ""
    feature_description: str = Field(
        default="", description="Roleplay benefit description"
    )


class BackgroundGenerationOutput(BaseModel):
    """Complete LLM output for background generation."""

    mechanics: BackgroundMechanics
    narrative: BackgroundNarrative


# =============================================================================
# CREATURE / MONSTER
# =============================================================================


class CreatureMechanics(BaseModel):
    """Independent mechanical values for a monster/creature stat block.

    The LLM decides these. The graph computes proficiency bonus (from CR),
    save bonuses, skill bonuses, effective HP, etc.
    """

    cr: str = Field(description="Challenge rating as string: '1/4', '5', '20'")
    cr_numeric: float = Field(ge=0, le=30)
    size: CreatureSize = "Medium"
    creature_type: str = "Beast"

    # Ability scores (all 6 are independent for creatures)
    ability_scores: dict[AbilityName, int] = Field(
        default_factory=lambda: {
            "strength": 10, "dexterity": 10, "constitution": 10,
            "intelligence": 10, "wisdom": 10, "charisma": 10,
        }
    )

    # Defenses
    ac: int = Field(10, ge=1, le=30, description="Armor class (includes natural armor)")
    ac_type: str | None = Field(default=None, description="'natural armor', 'plate', etc.")
    hp_dice_count: int = Field(1, ge=1, description="Number of hit dice")
    # hit die SIZE is computed from size via CREATURE_SIZE_HIT_DIE lookup

    # Movement
    speed: SpeciesSpeed = Field(default_factory=lambda: SpeciesSpeed())

    # Proficiencies (LLM picks which saves/skills are proficient)
    saving_throw_proficiencies: list[AbilityName] = Field(default_factory=list)
    skill_proficiencies: list[str] = Field(default_factory=list)

    # Defenses
    damage_vulnerabilities: list[str] = Field(default_factory=list)
    damage_resistances: list[str] = Field(default_factory=list)
    damage_immunities: list[str] = Field(default_factory=list)
    condition_immunities: list[str] = Field(default_factory=list)

    # Senses
    darkvision: int | None = None
    blindsight: int | None = None
    tremorsense: int | None = None
    truesight: int | None = None

    # Languages
    languages: list[str] = Field(default_factory=list)

    # Actions (mechanical effects)
    multiattack_count: int | None = Field(
        default=None, description="Number of attacks in multiattack"
    )
    actions: list[CreatureActionMechanics] = Field(default_factory=list)
    bonus_actions: list[CreatureActionMechanics] = Field(default_factory=list)
    reactions: list[CreatureActionMechanics] = Field(default_factory=list)
    traits: list[CreatureTraitMechanics] = Field(default_factory=list)

    # Boss features
    legendary_action_count: int = Field(default=0, ge=0, le=5)
    legendary_actions: list[LegendaryActionMechanics] = Field(default_factory=list)
    legendary_resistances: int = Field(default=0, ge=0, le=5)
    lair_actions: list[LairActionMechanics] = Field(default_factory=list)


class CreatureActionMechanics(BaseModel):
    """Mechanical definition of a creature action."""

    action_id: str
    action_type: Literal["melee", "ranged", "spell", "other"] = "melee"
    attack_bonus: int | None = Field(
        default=None,
        description="To-hit bonus. If None, no attack roll (save-based).",
    )
    reach_range: str | None = Field(default=None, description="e.g. '5 ft.' or '30/120 ft.'")
    damage: str | None = Field(default=None, description="e.g. '2d6 + 4'")
    damage_type: str | None = None
    save_dc: int | None = Field(default=None, description="Save DC if save-based")
    save_ability: AbilityName | None = None
    recharge: str | None = Field(default=None, description="e.g. '5-6'")


class CreatureTraitMechanics(BaseModel):
    """Mechanical definition of a special trait."""

    trait_id: str
    recharge: str | None = None
    modifies_node: list[NodeModifier] = Field(default_factory=list)


class LegendaryActionMechanics(BaseModel):
    """Mechanical definition of a legendary action."""

    action_id: str
    cost: int = Field(1, ge=1, le=3)


class LairActionMechanics(BaseModel):
    """Mechanical definition of a lair action."""

    action_id: str
    initiative_count: int = 20


class CreatureNarrative(BaseModel):
    """Narrative/flavor content for a creature."""

    name: str
    description: str = Field(description="Physical appearance and general nature")
    lore: str = Field(default="", description="Background/ecology")
    tactics: str = Field(default="", description="How to run in combat")
    alignment: str | None = None
    action_descriptions: list[CreatureActionNarrative] = Field(default_factory=list)
    trait_descriptions: list[CreatureTraitNarrative] = Field(default_factory=list)
    legendary_action_descriptions: list[CreatureActionNarrative] = Field(
        default_factory=list
    )
    lair_action_descriptions: list[LairActionNarrative] = Field(default_factory=list)
    regional_effects: list[str] = Field(default_factory=list)
    encounter_ideas: list[str] = Field(default_factory=list)


class CreatureActionNarrative(BaseModel):
    """Name and flavor for a creature action."""

    action_id: str
    name: str
    description: str


class CreatureTraitNarrative(BaseModel):
    """Name and flavor for a creature trait."""

    trait_id: str
    name: str
    description: str


class LairActionNarrative(BaseModel):
    """Flavor for a lair action."""

    action_id: str
    description: str


class CreatureGenerationOutput(BaseModel):
    """Complete LLM output for creature/monster generation."""

    mechanics: CreatureMechanics
    narrative: CreatureNarrative


# =============================================================================
# FEAT (mini-graph)
# =============================================================================


class FeatMechanics(BaseModel):
    """Mechanical definition of a feat.

    A feat is a mini-graph: it applies NodeModifiers to the character graph.
    """

    feat_id: str
    prerequisite_level: int = Field(default=1, ge=1, le=20)
    prerequisite_ability: AbilityName | None = None
    prerequisite_ability_min: int | None = None
    grants_ability_increase: dict[AbilityName, int] = Field(
        default_factory=dict,
        description="e.g. {'dexterity': 1} for feats that give +1",
    )
    grants_proficiency: list[str] = Field(default_factory=list)
    grants_resistance: list[str] = Field(default_factory=list)
    modifies_node: list[NodeModifier] = Field(
        default_factory=list,
        description="Direct graph node modifications",
    )


class FeatNarrative(BaseModel):
    """Flavor for a feat."""

    feat_id: str
    name: str
    description: str


class FeatGenerationOutput(BaseModel):
    """Complete LLM output for feat generation."""

    mechanics: FeatMechanics
    narrative: FeatNarrative


# =============================================================================
# EQUIPMENT ITEMS (mini-graphs)
# =============================================================================


class WeaponMechanics(BaseModel):
    """Mechanical definition of a weapon."""

    weapon_id: str
    base_weapon: str = Field(description="Official weapon name, e.g. 'longsword'")
    damage: str = Field(description="Damage dice, e.g. '1d8'")
    damage_type: str = "slashing"
    properties: list[str] = Field(
        default_factory=list,
        description="e.g. ['finesse', 'light', 'versatile']",
    )
    magic_bonus: int = Field(default=0, ge=0, le=3)
    rarity: str = "common"
    requires_attunement: bool = False
    special_abilities: list[WeaponAbilityMechanics] = Field(default_factory=list)


class WeaponAbilityMechanics(BaseModel):
    """Mechanical effect of a magic weapon ability."""

    ability_id: str
    modifies_node: list[NodeModifier] = Field(default_factory=list)
    uses_per_rest: int | None = None
    recovery: Literal["short_rest", "long_rest"] | None = None


class WeaponNarrative(BaseModel):
    """Flavor for a weapon."""

    weapon_id: str
    themed_name: str
    description: str = ""
    lore: str = ""
    appearance: str = ""
    symbolism: list[str] = Field(default_factory=list)
    is_signature: bool = False


class ArmorMechanics(BaseModel):
    """Mechanical definition of an armor piece.

    The base AC and max DEX are looked up from the armor type.
    Only magic_bonus is an independent variable beyond armor_type.
    """

    armor_id: str
    armor_type: str = Field(description="e.g. 'plate', 'leather', 'chain_mail'")
    magic_bonus: int = Field(default=0, ge=0, le=3)
    rarity: str = "common"
    requires_attunement: bool = False


class ArmorNarrative(BaseModel):
    """Flavor for armor."""

    armor_id: str
    themed_name: str
    description: str = ""
    appearance: str = ""
    is_signature: bool = False


# =============================================================================
# SPELL (mini-graph for signature/innate spells)
# =============================================================================


class SpellMechanics(BaseModel):
    """Mechanical definition of a spell."""

    spell_id: str
    base_spell: str = Field(description="Official D&D spell name or 'custom'")
    level: int = Field(ge=0, le=9, description="0 = cantrip")
    school: str = ""
    casting_time: str = "1 action"
    range: str = "Self"
    components: list[str] = Field(default_factory=list, description="V, S, M")
    duration: str = "Instantaneous"
    concentration: bool = False
    damage: str | None = Field(default=None, description="Damage dice if applicable")
    damage_type: str | None = None
    save_ability: AbilityName | None = None
    is_signature: bool = False


class SpellGenerationOutput(BaseModel):
    """Complete LLM output for a spell."""

    mechanics: SpellMechanics
    narrative: SpellNarrative
