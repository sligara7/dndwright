"""Canonical Pydantic models for dndwright's bundled D&D 5e (2024) content.

dndwright is the single source of truth for D&D 5e content *structure*. Until now
that structure lived implicitly in the JSON assets + imperative test assertions;
these models make it an explicit, exported, strict contract. Every bundled asset
validates against its model (see ``tests/test_content_models.py``), and downstream
consumers (e.g. generation_plus's homebrew generators) conform to / subclass these
models so generated content is structurally identical to official SRD content.

The models are ``extra="forbid"`` — a new field in an asset must be declared here,
which keeps the contract honest. The mechanical ``component`` field (the rules
modifier list compiled by :func:`dndwright.component_from_content`) is typed as a
list of :class:`Modifier`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Standard 5e ability keys used in creature ``abilities``/``saving_throws`` maps.
ABILITY_KEYS = ("str", "dex", "con", "int", "wis", "cha")


class _Strict(BaseModel):
    """Base: reject unknown fields so asset drift surfaces immediately."""

    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- #
# Shared mechanics
# --------------------------------------------------------------------------- #
class Modifier(_Strict):
    """One entry of a content item's ``component`` list — the raw modifier spec
    that :func:`dndwright.component_from_content` compiles. Either ``amount``
    (constant) or ``formula`` (computed) carries the value; ``condition`` gates it."""

    target: str
    mode: str = "add"  # add | set | union | override
    amount: Any | None = None  # int | str | list (may be templated "{choice}")
    formula: dict[str, Any] | None = None  # {op, args}
    condition: dict[str, Any] | None = None  # {op, args}


# --------------------------------------------------------------------------- #
# Creatures (monsters / NPCs)
# --------------------------------------------------------------------------- #
class DamageRoll(_Strict):
    avg: int
    dice: str
    type: str


class CreatureAction(_Strict):
    name: str
    text: str
    attack_type: str | None = None  # melee | ranged
    attack_bonus: int | None = None
    reach: str | None = None
    range: str | None = None
    damage: list[DamageRoll] | None = None
    save_ability: str | None = None
    save_dc: int | None = None
    uses: str | None = None
    recharge: str | None = None


class CreatureTrait(_Strict):
    name: str
    text: str
    uses: str | None = None


class LegendaryAction(_Strict):
    name: str
    text: str
    save_ability: str | None = None
    save_dc: int | None = None
    damage: list[DamageRoll] | None = None


class Creature(_Strict):
    """A monster / NPC stat block (``load_content("creatures")``)."""

    name: str
    size: str
    creature_type: str
    creature_subtype: str | None = None
    alignment: str
    ac: int
    initiative: int
    hp: int
    hp_formula: str
    speed: dict[str, int | bool]  # walk/fly/swim/climb/burrow -> ft; hover -> bool
    abilities: dict[str, int]  # str/dex/con/int/wis/cha -> raw score
    saving_throws: dict[str, int] | None = None  # ability -> modifier
    skills: dict[str, int] | None = None  # skill name -> bonus
    senses: dict[str, int]  # darkvision/passive_perception/... -> ft or value
    languages: list[str]
    cr: str
    cr_numeric: float
    xp: int
    xp_lair: int | None = None
    proficiency_bonus: int
    damage_resistances: list[str] | None = None
    damage_immunities: list[str] | None = None
    damage_vulnerabilities: list[str] | None = None
    condition_immunities: list[str] | None = None
    gear: list[str] | None = None
    swarm: bool | None = None
    traits: list[CreatureTrait] | None = None
    actions: list[CreatureAction] | None = None
    bonus_actions: list[CreatureAction] | None = None
    reactions: list[CreatureAction] | None = None
    legendary_actions: list[LegendaryAction] | None = None
    legendary_actions_intro: str | None = None


# --------------------------------------------------------------------------- #
# Classes
# --------------------------------------------------------------------------- #
class ClassFeature(_Strict):
    level: int
    name: str
    description: str


class Spellcasting(_Strict):
    type: str  # full | half | pact | third | ...
    ability: str
    spell_list_size: Any | None = None


class CharClass(_Strict):
    """A character class (``load_content("classes")``)."""

    name: str
    description: str
    hit_die: str  # d6 | d8 | d10 | d12
    primary_ability: str
    saving_throws: list[str]
    skill_proficiencies: str
    weapon_proficiencies: str
    armor_training: str
    tool_proficiencies: str
    starting_equipment: str
    spellcasting: Spellcasting | None = None
    subclass: str
    subclass_level: int
    features: list[ClassFeature]
    subclass_features: list[ClassFeature]


# --------------------------------------------------------------------------- #
# Species
# --------------------------------------------------------------------------- #
class SpeciesTrait(_Strict):
    name: str
    description: str


class Species(_Strict):
    """A playable species/ancestry (``load_content("species")``)."""

    name: str
    creature_type: str
    size: str
    speed: int  # base walking speed in ft
    senses: dict[str, int] | None = None
    traits: list[SpeciesTrait]
    description: str
    component: list[Modifier] = Field(default_factory=list)
    choices: dict[str, Any] | None = None


# --------------------------------------------------------------------------- #
# Spells / Magic items / Backgrounds / Feats / Weapons / Armor / Conditions
# --------------------------------------------------------------------------- #
class Spell(_Strict):
    name: str
    level: int  # 0 = cantrip
    school: str
    casting_time: str
    range: str
    components: str  # "V, S, M (...)"
    duration: str
    classes: list[str]
    description: str
    component: list[Modifier] | None = None


class MagicItem(_Strict):
    name: str
    category: str
    rarity: str
    attunement_required: bool
    type_line: str
    description: str
    component: list[Modifier] | None = None


class Background(_Strict):
    name: str
    ability_scores: list[str]
    feat: str
    skill_proficiencies: list[str]
    tool_proficiency: str
    equipment: str
    ability_score_rule: str
    choices: dict[str, Any]
    component: list[Modifier]


class Feat(_Strict):
    name: str
    category: str
    prerequisite: str | None = None
    repeatable: bool
    description: str
    component: list[Modifier] | None = None
    choices: dict[str, Any] | None = None


class Weapon(_Strict):
    name: str
    category: str  # Simple | Martial
    kind: str  # Melee | Ranged
    damage: str
    damage_dice: str
    damage_type: str
    properties: list[str]
    mastery: str
    weight: str
    cost: str


class Armor(_Strict):
    name: str
    category: str  # Light | Medium | Heavy | Shield
    base_ac: int | None = None
    ac_bonus: int | None = None  # shields
    adds_dex: bool
    dex_cap: int | str | None = None
    strength_requirement: int | None = None
    stealth_disadvantage: bool
    weight: str
    cost: str


class Condition(_Strict):
    name: str
    display_name: str
    description: str
    effects: list[str] | None = None
    mechanics: dict[str, Any]
    implies: list[str]
    grants_immunity_to: list[str]
    levels: dict[str, Any] | None = None


# Category name (as used by ``load_content``) -> model.
CONTENT_MODELS: dict[str, type[BaseModel]] = {
    "classes": CharClass,
    "species": Species,
    "creatures": Creature,
    "spells": Spell,
    "magic_items": MagicItem,
    "backgrounds": Background,
    "feats": Feat,
    "weapons": Weapon,
    "armor": Armor,
    "conditions": Condition,
}
