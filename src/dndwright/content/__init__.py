"""Bundled starter content + a generator for original homebrew.

    from dndwright.content import load_content, categories
    load_content("creatures")   # list of creature dicts (bundled samples)
    categories()                # ["classes", "conditions", "creatures", "feats", ...]

The bundled ``classes`` / ``species`` / ``creatures`` are original homebrew (no
official content); ``magic_items`` / ``conditions`` / ``feats`` are SRD 5.2
(CC-BY) — see NOTICE. Many ``magic_items`` and ``feats`` carry a ``component``
(see :func:`dndwright.component_from_content`) that snaps onto a character graph.
Grow the library with :func:`generate_library` (you supply the LLM).
"""

from __future__ import annotations

import importlib.resources
import json

from .generate import (
    JsonLLM,
    generate_classes,
    generate_creatures,
    generate_library,
    generate_species,
)

# category -> (filename, top-level array key)
_CONTENT = {
    "classes": ("classes.json", "classes"),
    "species": ("species.json", "species"),
    "creatures": ("creatures.json", "creatures"),
    "magic_items": ("magic_items.json", "magic_items"),
    "conditions": ("conditions.json", "conditions"),
    "feats": ("feats.json", "feats"),
}


def categories() -> list[str]:
    """The bundled content categories."""
    return sorted(_CONTENT)


def load_content(category: str) -> list[dict]:
    """Load the bundled starter content for ``category`` as a list of dicts."""
    if category not in _CONTENT:
        raise ValueError(f"unknown category {category!r}; choose from {categories()}")
    filename, key = _CONTENT[category]
    text = (importlib.resources.files("dndwright.content") / filename).read_text(encoding="utf-8")
    return json.loads(text).get(key, [])


__all__ = [
    "load_content",
    "categories",
    "generate_library",
    "generate_classes",
    "generate_species",
    "generate_creatures",
    "JsonLLM",
]
