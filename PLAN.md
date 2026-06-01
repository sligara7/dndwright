# dndwright — extraction plan

A domain-neutral **D&D 5e (2024) rules engine + graph ontology + original homebrew
content**, extracted from StoryFlow the same way `mapwright` was: a public, MIT,
self-contained library that StoryFlow (and anyone else) consumes, leaving the
narrative/graph coupling behind a thin adapter.

> Sibling-library pattern: like `mapwright` (procedural maps) and
> `dynograph-foundation` (graph engine). StoryFlow becomes a proprietary platform
> on top of open libraries.

## Why this is clean to extract now
- The rules engine (`generation_plus/src/rules/`, **4,018 LOC / 11 files**) depends
  only on **pydantic + stdlib** — *zero* StoryFlow/generation_plus imports. Verified.
- StoryFlow is **design-forward**: it generates its own content, so the engine never
  needed copyrighted data. We already **removed all non-SRD official content** and
  re-seeded with original homebrew — so there is **no copyrighted data anywhere** to
  block publication.
- Game **rules/mechanics are facts, not copyrightable**; the SRD 5.2 (CC-BY-4.0)
  covers the data we keep. So the whole thing is publishable.

## Licensing posture
- **Code:** MIT.
- **Rules tables** (`lookup_tables.py` — hit dice, spell slots, armor AC, save profs):
  game mechanics/facts; derived from **SRD 5.2 (CC-BY-4.0)**. Attribute the SRD in
  `NOTICE`.
- **Seed content:** original homebrew (MIT) + the kept **SRD magic items** (CC-BY,
  attributed). No PHB/MM/DMG content.
- `NOTICE` credits the SRD 5.2 (WotC, CC-BY-4.0). No OGL needed (CC-BY path).

## What goes public (dndwright) vs stays in StoryFlow

| dndwright (public, MIT) | StoryFlow (private adapter) |
|---|---|
| **Rules/computation engine** — `src/rules/*` (schema, operations, lookup_tables, components, assembler, evaluator, dnd_5e_2024, theme_scaling, adapters, character_evaluator) | The glue that **fetches a graph `Character`**, builds the neutral input dict, calls the engine, and **caches `computed_stats`** back on the node (lives in generation_plus routers/services + the `GET /computed-stats` endpoint + hash-invalidation) |
| **Ontology** — `dnd.yaml` (node types + edges) as a versioned schema + a small loader | Seeding the ontology into dynograph + StoryFlow's narrative↔mechanical bridge (`HAS_STAT_BLOCK`, narrative props on the Character node) |
| **Original content + generator** — the homebrew classes/species/creatures + `generate_seed_content.py` + SRD magic items | Which content to seed, and any narrative enrichment |

The boundary is the same shape as `map_adapter` for mapwright: the engine takes a
**neutral character-sheet input dict** (`adapters.character_data_to_inputs`) and
returns computed values; StoryFlow owns mapping its graph `Character` ↔ that dict.

## Repo structure (mirror mapwright)
```
dndwright/
├── LICENSE                  (MIT)
├── NOTICE                   (SRD 5.2 CC-BY attribution)
├── README.md                (alpha/WIP banner)
├── CHANGELOG.md
├── pyproject.toml           (hatchling; dep: pydantic; dev: pytest, ruff)
├── .github/workflows/ci.yml (ruff + pytest, py3.10–3.13)
├── src/dndwright/
│   ├── __init__.py          (public API + __version__)
│   ├── rules/               ← lift-and-shift of src/rules/* (engine)
│   ├── ontology/
│   │   ├── dnd.yaml         ← the graph schema
│   │   └── loader.py        (parse/validate the ontology)
│   └── content/             ← original seed (classes/species/creatures) + SRD magic items
│       └── generate.py      (the seed generator, de-StoryFlow-ified)
└── tests/                   (rules engine tests + a contract test + ontology/content checks)
```

## Phased plan

### Phase 1 — the engine (highest value, zero data-licensing) · M
1. `git mv`/copy `generation_plus/src/rules/*` → `dndwright/src/dndwright/rules/`.
   Internal imports are already relative (`.lookup_tables`, `.operations`, …) → no
   changes. Confirm the only external dep is `pydantic`.
2. Package it: `pyproject.toml` (pydantic dep), `__init__.py` exporting the public API
   (`evaluate_character` / the ruleset + `character_data_to_inputs`), `__version__`.
3. **Tests:** port the existing rules tests (e.g. `generation_plus/tests/.../character_computed_stats.py`)
   to `dndwright/tests/`; assert the canonical formulas (ability mod, prof bonus, spell
   DC `8+prof+mod`, HP per level, AC) on a few fixture characters. Add an API-contract
   test (pin `dndwright.__all__`).
4. MIT LICENSE + NOTICE (SRD 5.2) + README + CHANGELOG + CI (ruff+pytest).
5. **Invariant:** `grep -rE "from \.\.|storyflow|generation_plus" src/dndwright/` → empty.

### Phase 2 — the ontology · S
- Add `dnd.yaml` + a loader that parses node types/edges (validate, expose as data).
  Useful to anyone building a D&D graph; StoryFlow keeps the dynograph-seeding glue.

### Phase 3 — original content + generator · S/M
- Bundle the original homebrew seed (classes/species/creatures) + SRD magic items, and
  a de-StoryFlow-ified `generate.py` (takes an LLM-callable, not generation_plus's
  client) so anyone can grow the library.

### Phase 4 — wire StoryFlow to consume dndwright · M
- Mirror the mapwright wiring: `generation_plus` depends on `dndwright @ git+...@vX`
  (add `git` to its Dockerfile builder if needed; allow-direct-references), delete the
  in-tree `src/rules/`, import `from dndwright.rules import …`, keep the thin
  graph-Character↔input-dict adapter + `computed-stats` caching in generation_plus.
  (Defer until the dndwright API stabilizes — mature in-tree first, like mapwright.)

## Versioning & contract
SemVer; public API = `dndwright.__all__`, pinned by a contract test. Tag `v0.1.0`
after Phase 1 (engine), bump as ontology/content land. CHANGELOG per release.

## First concrete step
Phase 1: lift `src/rules/` into `dndwright/src/dndwright/rules/`, package it (pyproject
+ MIT + NOTICE + README), port the engine tests, add CI. The engine alone — a
CC-BY-clean D&D 5e 2024 rules/computation engine — is worth publishing on its own.

## Notes
- Confirm the exact ontology file set (currently `dnd.yaml`; an earlier
  `dnd_mechanical.yaml` reference may be merged/renamed — verify at extraction).
- Create the GitHub remote for `dndwright` (repo is local-only so far); decide
  public-now vs after Phase 1 (mapwright went public early; low stakes).
