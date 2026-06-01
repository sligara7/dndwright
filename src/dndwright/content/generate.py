"""Generate original homebrew D&D content via a caller-provided LLM.

dndwright is LLM-agnostic: you pass a ``complete_json(prompt, system) -> dict``
callable that wraps *your* LLM (OpenAI, Anthropic, OpenRouter, a local model, …)
and returns the parsed JSON object. The prompts steer toward **original homebrew**
— novel names and mechanics, never official content — so the output is yours.

    from dndwright.content import generate_library

    def my_llm(prompt: str, system: str | None = None) -> dict:
        # call your model in JSON mode, return the parsed dict
        ...

    library = generate_library(my_llm, classes=6, species=6, creatures=12)
    # -> {"classes": [...], "species": [...], "creatures": [...]}

Output matches the bundled-content schema (and the dndwright Class/Species/Creature
ontology), so you can drop it straight into your own graph or library.
"""

from __future__ import annotations

from typing import Any, Callable

# (prompt, system) -> parsed JSON object. Sync; wrap an async client if needed.
JsonLLM = Callable[[str, "str | None"], dict[str, Any]]

SYSTEM = (
    "You are a tabletop RPG homebrew designer. You invent ORIGINAL fantasy game "
    "content — wholly novel names and mechanics. You NEVER reproduce official "
    "Dungeons & Dragons content (no Fighter/Wizard/Rogue, no Elf/Dwarf/Orc, no "
    "Goblin/Beholder/Dragon, etc.). You answer only with the requested JSON."
)

_CLASSES_PROMPT = """Invent {n} ORIGINAL homebrew character classes for a 5e-style fantasy game — wholly novel concepts, not reskins of official classes. For each, output exactly:
{{"name": "<original class name>", "mechanics": {{"hit_die": "d6|d8|d10|d12", "primary_ability": "STR|DEX|CON|INT|WIS|CHA", "saving_throws": ["<ability>", "<ability>"], "spellcasting_type": "none|full|half|pact", "key_features": ["<3-5 signature features, each a short phrase>"]}}, "narrative": {{"description": "<2-3 sentence concept>", "role": "<party role>", "flavor": "<evocative one-liner>"}}}}
Respond with JSON: {{"classes": [ ... {n} items ... ]}}. Original names only — invent them."""

_SPECIES_PROMPT = """Invent {n} ORIGINAL homebrew playable ancestries/species for a 5e-style fantasy game — wholly novel, not elves/dwarves/orcs/halflings/etc. For each, output exactly:
{{"name": "<original species name>", "mechanics": {{"size": "Small|Medium", "speed": 30, "ability_bonuses": "<e.g. +2 to one, +1 to another, or 'flexible +2/+1'>", "traits": ["<3-4 species traits, short phrases>"]}}, "narrative": {{"description": "<2-3 sentence concept>", "flavor": "<one-liner>"}}}}
Respond with JSON: {{"species": [ ... {n} items ... ]}}. Original names only — invent them."""

_CREATURES_PROMPT = """Invent {n} ORIGINAL homebrew creatures for a 5e-style fantasy game — wholly novel, not goblins/dragons/beholders/owlbears/etc. Spread challenge ratings from 1/8 up to about 8. For each, output exactly:
{{"name": "<original creature name>", "size": "Tiny|Small|Medium|Large|Huge|Gargantuan", "creature_type": "aberration|beast|celestial|construct|dragon|elemental|fey|fiend|giant|humanoid|monstrosity|ooze|plant|undead", "alignment": "<e.g. chaotic evil>", "cr": "<1/8|1/4|1/2|1|2|3|...>", "hp": <integer>, "ac": <integer>, "speed": "<e.g. '30 ft.' or '30 ft., fly 60 ft.'>", "stat_block": {{"abilities": {{"str": <int>, "dex": <int>, "con": <int>, "int": <int>, "wis": <int>, "cha": <int>}}, "actions": ["<2-4 actions, short phrases>"], "traits": ["<0-3 trait phrases>"]}}}}
Respond with JSON: {{"creatures": [ ... {n} items ... ]}}. Original names only — invent them.{avoid}"""


def _gen(llm: JsonLLM, prompt: str, key: str) -> list[dict]:
    result = llm(prompt, SYSTEM)
    items = result.get(key, []) if isinstance(result, dict) else []
    return [i for i in items if isinstance(i, dict)]


def generate_classes(llm: JsonLLM, n: int = 6) -> list[dict]:
    """Generate ``n`` original homebrew classes."""
    return _gen(llm, _CLASSES_PROMPT.format(n=n), "classes")


def generate_species(llm: JsonLLM, n: int = 6) -> list[dict]:
    """Generate ``n`` original homebrew species."""
    return _gen(llm, _SPECIES_PROMPT.format(n=n), "species")


def generate_creatures(llm: JsonLLM, n: int = 6) -> list[dict]:
    """Generate ``n`` original homebrew creatures (in batches, avoiding repeats)."""
    creatures: list[dict] = []
    remaining = n
    while remaining > 0:
        batch = min(6, remaining)
        avoid = ""
        if creatures:
            names = ", ".join(c.get("name", "") for c in creatures)
            avoid = f" Do NOT repeat any of these already-made creatures: {names}."
        creatures += _gen(llm, _CREATURES_PROMPT.format(n=batch, avoid=avoid), "creatures")
        remaining -= batch
    return creatures


def generate_library(
    llm: JsonLLM, classes: int = 6, species: int = 6, creatures: int = 12
) -> dict[str, list[dict]]:
    """Generate a full starter library: classes + species + creatures."""
    return {
        "classes": generate_classes(llm, classes),
        "species": generate_species(llm, species),
        "creatures": generate_creatures(llm, creatures),
    }
