"""D&D 5th Edition (2024) character sheet computation graph.

~80 nodes organized in layers:
  Layer 0 — Inputs (12): ability scores, level, class, equipment
  Layer 1 — Simple Derived (27): modifiers, proficiency bonus, saves
  Layer 2 — Complex Derived (35+): skills, HP, AC, spellcasting, passives

This is the built-in default ruleset. Custom rulesets (Phase 4) will
fork-and-modify this graph.
"""

from __future__ import annotations

from .lookup_tables import get_all_lookup_tables
from .schema import ComputationNode, FormulaSpec, NodeType, Ruleset

ABILITIES = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]

# Damage-defence channels. These are bundled as empty ``union`` nodes (see _build_nodes) so an
# evaluated sheet always exposes them (as ``()``), and a component — a Ring of Resistance, a
# species trait — contributes damage types into them via a ``union``-mode contribution. Feed the
# evaluated sets to a CombatantState via dndwright.combat.combatant_defenses().
RESISTANCES_NODE = "resistances"
IMMUNITIES_NODE = "immunities"
VULNERABILITIES_NODE = "vulnerabilities"
DAMAGE_CHANNELS = (RESISTANCES_NODE, IMMUNITIES_NODE, VULNERABILITIES_NODE)

SKILLS = {
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


def _build_nodes() -> dict[str, ComputationNode]:
    """Build all computation nodes for the D&D 5e 2024 ruleset."""
    nodes: dict[str, ComputationNode] = {}

    def add(node: ComputationNode) -> None:
        nodes[node.id] = node

    # =================================================================
    # Layer 0 — Input nodes
    # =================================================================
    for ability in ABILITIES:
        add(
            ComputationNode(
                id=f"{ability}_score",
                node_type=NodeType.INPUT,
                label=f"{ability.capitalize()} Score",
                layer=0,
                group="ability_scores",
                default_value=10,
                min_value=1,
                max_value=30,
                description="Ability score (1-30). Standard range 3-20, can exceed via magic.",
            )
        )

    add(
        ComputationNode(
            id="character_level",
            node_type=NodeType.INPUT,
            label="Character Level",
            layer=0,
            group="core",
            default_value=1,
            min_value=1,
            max_value=20,
            description="Total character level (sum of all class levels).",
        )
    )

    add(
        ComputationNode(
            id="class_levels",
            node_type=NodeType.INPUT,
            label="Class Levels",
            layer=0,
            group="core",
            default_value={},
            description='Dict mapping class name to level, e.g. {"bard": 5, "warlock": 3}.',
        )
    )

    add(
        ComputationNode(
            id="class_hit_dice",
            node_type=NodeType.INPUT,
            label="Class Hit Dice",
            layer=0,
            group="core",
            default_value={},
            description='Dict mapping class name to hit die size, e.g. {"bard": 8, "warlock": 8}.',
        )
    )

    add(
        ComputationNode(
            id="primary_class",
            node_type=NodeType.INPUT,
            label="Primary Class",
            layer=0,
            group="core",
            default_value="",
            description="Primary class name (lowercase). Used for save profs, spell ability.",
        )
    )

    add(
        ComputationNode(
            id="spellcasting_type",
            node_type=NodeType.INPUT,
            label="Spellcasting Type",
            layer=0,
            group="spellcasting",
            default_value="none",
            description="full_caster, half_caster, pact_caster, or none.",
        )
    )

    add(
        ComputationNode(
            id="class_spellcasting_types",
            node_type=NodeType.INPUT,
            label="Class Spellcasting Types",
            layer=0,
            group="spellcasting",
            default_value={},
            description="Per-class spellcasting types for multiclass.",
        )
    )

    add(
        ComputationNode(
            id="armor_type",
            node_type=NodeType.INPUT,
            label="Armor Type",
            layer=0,
            group="equipment",
            default_value="none",
            description="Equipped armor type (e.g., 'plate', 'leather', 'none').",
        )
    )

    add(
        ComputationNode(
            id="armor_magic_bonus",
            node_type=NodeType.INPUT,
            label="Armor Magic Bonus",
            layer=0,
            group="equipment",
            default_value=0,
            min_value=0,
            max_value=5,
        )
    )

    add(
        ComputationNode(
            id="has_shield",
            node_type=NodeType.INPUT,
            label="Has Shield",
            layer=0,
            group="equipment",
            default_value=False,
        )
    )

    add(
        ComputationNode(
            id="natural_armor_ac",
            node_type=NodeType.INPUT,
            label="Natural Armor AC",
            layer=0,
            group="equipment",
            default_value=0,
            min_value=0,
            max_value=30,
            description="Base AC from species natural armor (0 = none).",
        )
    )

    add(
        ComputationNode(
            id="speed_base",
            node_type=NodeType.INPUT,
            label="Base Speed",
            layer=0,
            group="core",
            default_value=30,
            description="Base walking speed from species.",
        )
    )

    # Saving throw proficiency inputs (per ability)
    for ability in ABILITIES:
        add(
            ComputationNode(
                id=f"save.{ability}.proficient",
                node_type=NodeType.INPUT,
                label=f"{ability.capitalize()} Save Proficiency",
                layer=0,
                group="saves",
                default_value=False,
            )
        )

    # Skill proficiency inputs
    for skill in SKILLS:
        add(
            ComputationNode(
                id=f"skill.{skill}.proficient",
                node_type=NodeType.INPUT,
                label=f"{skill.replace('_', ' ').title()} Proficiency",
                layer=0,
                group="skills",
                default_value=False,
            )
        )
        add(
            ComputationNode(
                id=f"skill.{skill}.expertise",
                node_type=NodeType.INPUT,
                label=f"{skill.replace('_', ' ').title()} Expertise",
                layer=0,
                group="skills",
                default_value=False,
            )
        )

    # =================================================================
    # Layer 1 — Simple Derived (modifiers, proficiency bonus)
    # =================================================================

    # Ability modifiers: (score - 10) // 2
    for ability in ABILITIES:
        add(
            ComputationNode(
                id=f"{ability}_mod",
                node_type=NodeType.FORMULA,
                label=f"{ability.capitalize()} Modifier",
                layer=1,
                group="ability_scores",
                formula=FormulaSpec(op="ability_mod", args=[f"{ability}_score"]),
                inputs=[f"{ability}_score"],
                description="(score - 10) // 2. PHB p.13.",
            )
        )

    # Proficiency bonus: 2 + ((level - 1) // 4)
    add(
        ComputationNode(
            id="proficiency_bonus",
            node_type=NodeType.FORMULA,
            label="Proficiency Bonus",
            layer=1,
            group="core",
            formula=FormulaSpec(op="prof_bonus", args=["character_level"]),
            inputs=["character_level"],
            min_value=2,
            max_value=6,
            description="2 + ((level - 1) // 4). PHB p.15.",
        )
    )

    # Saving throw bonuses
    for ability in ABILITIES:
        add(
            ComputationNode(
                id=f"save.{ability}.bonus",
                node_type=NodeType.FORMULA,
                label=f"{ability.capitalize()} Save Bonus",
                layer=1,
                group="saves",
                formula=FormulaSpec(
                    op="prof_add",
                    args=[f"{ability}_mod", "proficiency_bonus", f"save.{ability}.proficient"],
                ),
                inputs=[f"{ability}_mod", "proficiency_bonus", f"save.{ability}.proficient"],
            )
        )

    # Spell ability modifier (uses primary class to determine which ability)
    add(
        ComputationNode(
            id="spell_ability",
            node_type=NodeType.LOOKUP,
            label="Spellcasting Ability",
            layer=1,
            group="spellcasting",
            formula=FormulaSpec(
                op="lookup", args=["spell_ability_by_class", "primary_class", "charisma"]
            ),
            inputs=["primary_class"],
            description="Spell ability determined by class. PHB varies by class.",
        )
    )

    # =================================================================
    # Layer 2 — Complex Derived
    # =================================================================

    # Spell modifier (the modifier value for the spell ability)
    # This is a dynamic lookup — spell_ability resolves to an ability name,
    # and we need the modifier for that ability. We handle this with a
    # special operation.
    add(
        ComputationNode(
            id="spell_mod",
            node_type=NodeType.FORMULA,
            label="Spellcasting Modifier",
            layer=2,
            group="spellcasting",
            formula=FormulaSpec(
                op="spell_mod_resolve",
                args=[
                    "spell_ability",
                    "strength_mod",
                    "dexterity_mod",
                    "constitution_mod",
                    "intelligence_mod",
                    "wisdom_mod",
                    "charisma_mod",
                ],
            ),
            inputs=[
                "spell_ability",
                "strength_mod",
                "dexterity_mod",
                "constitution_mod",
                "intelligence_mod",
                "wisdom_mod",
                "charisma_mod",
            ],
            description="Modifier for the class's spellcasting ability.",
        )
    )

    # Spell save DC: 8 + prof + spell_mod
    add(
        ComputationNode(
            id="spell_save_dc",
            node_type=NodeType.FORMULA,
            label="Spell Save DC",
            layer=2,
            group="spellcasting",
            formula=FormulaSpec(op="add", args=["spell_mod", "proficiency_bonus", 8]),
            inputs=["spell_mod", "proficiency_bonus"],
            min_value=1,
            description="8 + proficiency_bonus + spellcasting_mod. PHB p.201.",
        )
    )

    # Spell attack bonus: prof + spell_mod
    add(
        ComputationNode(
            id="spell_attack",
            node_type=NodeType.FORMULA,
            label="Spell Attack Bonus",
            layer=2,
            group="spellcasting",
            formula=FormulaSpec(op="add", args=["spell_mod", "proficiency_bonus"]),
            inputs=["spell_mod", "proficiency_bonus"],
            description="proficiency_bonus + spellcasting_mod. PHB p.201.",
        )
    )

    # Spell slots
    add(
        ComputationNode(
            id="spell_slots",
            node_type=NodeType.FORMULA,
            label="Spell Slots",
            layer=2,
            group="spellcasting",
            formula=FormulaSpec(
                op="spell_slots",
                args=["spellcasting_type", "character_level", "primary_class"],
            ),
            inputs=["spellcasting_type", "character_level", "primary_class"],
            description="Spell slot progression by class type and level.",
        )
    )

    # Multiclass spell slots (used when multiple classes)
    add(
        ComputationNode(
            id="multiclass_spell_slots",
            node_type=NodeType.FORMULA,
            label="Multiclass Spell Slots",
            layer=2,
            group="spellcasting",
            formula=FormulaSpec(
                op="multiclass_spell_slots",
                args=["class_levels", "class_spellcasting_types"],
            ),
            inputs=["class_levels", "class_spellcasting_types"],
            description="Combined spell slots for multiclass characters per PHB p.164.",
        )
    )

    # HP
    add(
        ComputationNode(
            id="hp_max",
            node_type=NodeType.FORMULA,
            label="Hit Points Maximum",
            layer=2,
            group="combat",
            formula=FormulaSpec(
                op="multiclass_hp",
                args=["class_levels", "class_hit_dice", "constitution_mod"],
            ),
            inputs=["class_levels", "class_hit_dice", "constitution_mod"],
            min_value=1,
            description="L1: max die + CON. L2+: average + CON per level. Min 1/level.",
        )
    )

    # Hit dice string
    add(
        ComputationNode(
            id="hit_dice",
            node_type=NodeType.FORMULA,
            label="Hit Dice",
            layer=2,
            group="combat",
            formula=FormulaSpec(
                op="hit_dice_str",
                args=["class_levels", "class_hit_dice"],
            ),
            inputs=["class_levels", "class_hit_dice"],
            description="Hit dice display string, e.g. '5d8' or '5d8 + 3d10'.",
        )
    )

    # AC
    add(
        ComputationNode(
            id="armor_class",
            node_type=NodeType.FORMULA,
            label="Armor Class",
            layer=2,
            group="combat",
            formula=FormulaSpec(
                op="ac_with_armor",
                args=["armor_type", "dexterity_mod", "armor_magic_bonus", "has_shield", "natural_armor_ac"],
            ),
            inputs=["armor_type", "dexterity_mod", "armor_magic_bonus", "has_shield", "natural_armor_ac"],
            min_value=1,
            description="Base AC from armor + DEX (capped) + magic + shield. PHB p.14.",
        )
    )

    # Initiative: DEX modifier
    add(
        ComputationNode(
            id="initiative",
            node_type=NodeType.FORMULA,
            label="Initiative",
            layer=2,
            group="combat",
            formula=FormulaSpec(op="const", args=["dexterity_mod"]),
            inputs=["dexterity_mod"],
            description="Initiative = DEX modifier (before feats/features). PHB p.189.",
        )
    )

    # Skill bonuses (18 skills)
    for skill, ability in SKILLS.items():
        add(
            ComputationNode(
                id=f"skill.{skill}.bonus",
                node_type=NodeType.FORMULA,
                label=f"{skill.replace('_', ' ').title()} Bonus",
                layer=2,
                group="skills",
                formula=FormulaSpec(
                    op="skill_bonus",
                    args=[
                        f"{ability}_mod",
                        "proficiency_bonus",
                        f"skill.{skill}.proficient",
                        f"skill.{skill}.expertise",
                    ],
                ),
                inputs=[
                    f"{ability}_mod",
                    "proficiency_bonus",
                    f"skill.{skill}.proficient",
                    f"skill.{skill}.expertise",
                ],
                description=f"Based on {ability.upper()[:3]}. +prof/+2x prof.",
            )
        )

    # Passive scores
    for passive_skill in ("perception", "investigation", "insight"):
        add(
            ComputationNode(
                id=f"passive_{passive_skill}",
                node_type=NodeType.FORMULA,
                label=f"Passive {passive_skill.capitalize()}",
                layer=2,
                group="combat",
                formula=FormulaSpec(
                    op="passive_score",
                    args=[f"skill.{passive_skill}.bonus"],
                ),
                inputs=[f"skill.{passive_skill}.bonus"],
                description=f"10 + {passive_skill} bonus. PHB p.175.",
            )
        )

    # =================================================================
    # Output nodes (formatted strings for display)
    # =================================================================
    for ability in ABILITIES:
        add(
            ComputationNode(
                id=f"{ability}_mod_display",
                node_type=NodeType.OUTPUT,
                label=f"{ability.capitalize()} Modifier Display",
                layer=2,
                group="ability_scores",
                formula=FormulaSpec(op="format_mod", args=[f"{ability}_mod"]),
                inputs=[f"{ability}_mod"],
            )
        )

    add(
        ComputationNode(
            id="proficiency_bonus_display",
            node_type=NodeType.OUTPUT,
            label="Proficiency Bonus Display",
            layer=2,
            group="core",
            formula=FormulaSpec(op="format_mod", args=["proficiency_bonus"]),
            inputs=["proficiency_bonus"],
        )
    )

    add(
        ComputationNode(
            id="initiative_display",
            node_type=NodeType.OUTPUT,
            label="Initiative Display",
            layer=2,
            group="combat",
            formula=FormulaSpec(op="format_mod", args=["initiative"]),
            inputs=["initiative"],
        )
    )

    add(
        ComputationNode(
            id="spell_attack_display",
            node_type=NodeType.OUTPUT,
            label="Spell Attack Display",
            layer=2,
            group="spellcasting",
            formula=FormulaSpec(op="format_mod", args=["spell_attack"]),
            inputs=["spell_attack"],
        )
    )

    for ability in ABILITIES:
        add(
            ComputationNode(
                id=f"save.{ability}.display",
                node_type=NodeType.OUTPUT,
                label=f"{ability.capitalize()} Save Display",
                layer=2,
                group="saves",
                formula=FormulaSpec(op="format_mod", args=[f"save.{ability}.bonus"]),
                inputs=[f"save.{ability}.bonus"],
            )
        )

    for skill in SKILLS:
        add(
            ComputationNode(
                id=f"skill.{skill}.display",
                node_type=NodeType.OUTPUT,
                label=f"{skill.replace('_', ' ').title()} Display",
                layer=2,
                group="skills",
                formula=FormulaSpec(op="format_mod", args=[f"skill.{skill}.bonus"]),
                inputs=[f"skill.{skill}.bonus"],
            )
        )

    # =================================================================
    # Damage-defence channels — empty union aggregates, populated by
    # composed components (resistances/immunities/vulnerabilities).
    # =================================================================
    for channel, label in (
        (RESISTANCES_NODE, "Damage Resistances"),
        (IMMUNITIES_NODE, "Damage Immunities"),
        (VULNERABILITIES_NODE, "Damage Vulnerabilities"),
    ):
        add(
            ComputationNode(
                id=channel,
                node_type=NodeType.AGGREGATE,
                label=label,
                layer=2,
                group="defenses",
                formula=FormulaSpec(op="union", args=[]),
            )
        )

    return nodes


def build_dnd_5e_2024_ruleset() -> Ruleset:
    """Build the complete D&D 5e 2024 ruleset."""
    return Ruleset(
        id="dnd_5e_2024",
        name="D&D 5th Edition (2024)",
        version="1.0.0",
        nodes=_build_nodes(),
        lookup_tables=get_all_lookup_tables(),
        metadata={
            "system": "dnd",
            "edition": "5e_2024",
            "description": "D&D 5th Edition 2024 revision character sheet computation graph.",
        },
    )


# Singleton — built once, reused
DND_5E_2024_RULESET: Ruleset = build_dnd_5e_2024_ruleset()
