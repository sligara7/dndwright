# Changelog

All notable changes to dndwright are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project aims to follow
[Semantic Versioning](https://semver.org/).

**Public API** = the names exported in `dndwright.__all__` (pinned by
`tests/test_api_contract.py`). While the version is `0.x`, minor versions may make
breaking changes; these will always be noted here.

## [Unreleased]

### Added
- **Magic items as composable content** — bundled `magic_items` entries can now carry their
  mechanical effect *as data*: a `component` field (a list of `{target, amount, mode}`
  modifiers). `component_from_content(item)` expands it into a `Component` you can `compose`
  onto a character graph, so equipping an item cascades through derived stats. Curated SRD
  set bundled: Gauntlets of Ogre Power & Amulet of Health & Headband of Intellect (set an
  ability score), Cloak of Protection & Ring of Protection (+1 AC and all saves), Belt of
  Dwarvenkind (+2 CON). Items with no mechanical effect return `None`.

## [0.9.0] — 2026-06-02

### Added
- **Graph composition — the "lego" engine** (`dndwright.compose` → top-level `compose`,
  `modifier`, `Component`, `Contribution`). A `Component` is a mini-graph (a magic item, feat,
  trait) plus declarations of how it attaches; `compose(base, *components)` merges them into a
  new `Ruleset` that evaluates normally. The attach trick: a contribution's target node **keeps
  its id** and becomes an AGGREGATE of the original (moved to `{id}.__base__`) plus the
  contributions — so every downstream value recomputes automatically with no re-wiring. Snap a
  Gauntlets of Ogre Power (set STR→19) onto a character and its modifier, saves and skills
  cascade. Modes: `add` (sum), `set` (max), `union` (set channels, e.g. resistances). Pure and
  stackable. `ComputationNode` gains an optional `input_key` so a renamed INPUT still binds its
  value; new `union` formula op.

## [0.8.0] — 2026-06-02

### Added
- **Damage-type resistance / immunity / vulnerability** in `dndwright.combat`. `CombatantState`
  gains `resistances` / `immunities` / `vulnerabilities` (frozensets of damage types — plain,
  composable data), and `apply_damage(state, amount, *, damage_type=...)` now scales the hit
  by `damage_multiplier()` (0 immune / 0.5 resist rounded down / 2 vulnerable, resist+vuln
  cancel) before temp HP / HP, per 5e. `DamageApplication` reports `raw_damage` + `multiplier`.
  New public `damage_multiplier()` (data-driven, no hard-coded type lists) + `DAMAGE_TYPES`
  (the 13 SRD types). Fixes a real gap — typed damage was previously unscaled.

## [0.7.0] — 2026-06-02

### Added
- **More public accessors for downstream consumers** (finishing the storyflow-alignment
  surface): `describe_operations()` (operation name → docstring summary, a read-only view of
  the registry for building an ops reference without touching the mutable `OPERATIONS` dict),
  and the theme-scaling surface — `get_theme_scaling`, `list_predefined_themes`,
  `PREDEFINED_THEME_SCALING`, `ThemeScalingLayer` (mechanical profiles per setting theme).

## [0.6.0] — 2026-06-02

### Added
- **Public graph-introspection + table accessors.** Promoted load-bearing symbols from the
  internal `dndwright.rules.*` modules to the public top-level API so consumers stop coupling
  to internal layout: `compute_stat_diff` (before/after sheet deltas), `get_evaluation_order`,
  `get_node_dependencies`, `get_downstream_nodes`, the new `get_graph_edges(ruleset)` (a
  structured `(from, to)` edge list, so you don't hand-derive edges from `node.inputs` +
  `formula.args`), and `get_all_lookup_tables()` (the SRD reference tables — hit dice, spell
  slots, AC, rarity, XP, weapon mastery, …). All additive.

## [0.5.1] — 2026-06-02

### Docs
- Promotional graphics for the README / PyPI page: a toolkit **overview** hero (rules
  engine · dice · combat · content), a **dice** DSL showcase, and a **combat** state-machine
  diagram, alongside the existing computation-graph diagram. Docs-only release so these
  reach the PyPI project page (which renders the README frozen per version).
- `RELEASING.md`: documented that the shields.io version badge is CDN-cached (lags the real
  version) and that the PyPI README is frozen per-version (README/graphics changes only go
  live on the next release).

## [0.5.0] — 2026-06-02

### Added
- **Conditions** (`dndwright.combat.conditions`) — pure rules over the bundled SRD
  catalog: `condition_effects` (effect text + mechanical flags), `implied_conditions`,
  `is_immune`, `tick_conditions` (round/turn duration ticking), and `attempt_save`
  (save-ends). The 14 SRD conditions + exhaustion are bundled **content**
  (`load_content("conditions")`), not hard-coded enums. Frozen `ConditionEffect` /
  `ActiveCondition` / `ConditionChange` / `SaveResult` value types.
- **Initiative** (`dndwright.combat.initiative`) — pure ordering + turn tracking:
  `roll_initiative` (1d20 + modifier), `order_initiative` (total desc, DEX-modifier
  tie-break, stable), and `advance_turn` / `previous_turn` (skip inactive, wrap →
  round change). Frozen `InitiativeEntry` / `InitiativeRoll` / `TurnAdvance` value types.
- **Combat rules** (`dndwright.combat`) — pure, identity-free 5e combat over a frozen
  `CombatantState` value object (no IDs, no persistence). Operations are
  `(state, input) -> (new_state, explanation)`: `apply_damage` (temp-HP absorption,
  overkill, massive-damage instant death), `apply_healing`, `set_temp_hp` (no-stack),
  `roll_death_save` (takes a `DiceEngine`; nat 20 regains 1 HP, nat 1 = two failures,
  3 successes stabilise / 3 failures kill), `stabilize`, `reset_death_saves`, plus the
  `calculate_damage_application` helper and `DamageApplication`/`HPChange`/`DeathSaveResult`
  result types. Extracted from a working SQL-bound service; the rules layer is pure.

## [0.4.0] — 2026-06-01

### Added
- **Dice engine** (`dndwright.dice`) — `DiceEngine`: parse and roll D&D 5e dice
  expressions (`1d20+5`, `4d6kh3`, `2d6r1`, `1d6!`, advantage/disadvantage) plus
  `roll_attack`/`roll_save`/`roll_check`/`roll_damage`/`roll_initiative`/`roll_stat_array`/
  `roll_hit_dice`/`roll_death_save`. Returns a **typed, frozen result surface**
  (`ExpressionResult`, `RollResult`, `AttackRoll`, `SaveRoll`, `DamageRoll`, `DeathSave`,
  `StatArray`, `HitDiceResult`, …). Deterministic by default (`DiceEngine(seed=…)`); for
  unpredictable production rolls inject any `random.Random` (e.g.
  `DiceEngine(rng=secrets.SystemRandom())`) — no NumPy dependency. `DiceEngine` is also
  re-exported at the top level.

### Fixed
- **Dice engine hardening** — pathological groups can no longer hang the engine: rerolls
  whose set covers every die face are skipped, exploding requires `sides > 1`, and both
  loops are capped (`1d1!`, `1d2r1,2` now terminate). `reroll_once` is detected per dice
  group instead of from the whole expression, so a later `ro` group can't flip an earlier
  `r` group. Result value types are now genuinely immutable — sequence fields are tuples,
  making every result hashable and usable as a set member / dict key.
- **CLI robustness** — `dndwright eval` now reports a clean error for non-object JSON
  (was an uncaught `AttributeError`), and `dndwright validate` reports a clean error for
  valid-JSON-but-invalid rulesets (was an uncaught pydantic `ValidationError`).
- **Graph export escaping** — `to_mermaid` now escapes label special characters
  (`[](){}<>"#`) and emits subgraphs as `id["title"]`, so labels and group names with
  spaces/punctuation no longer break the diagram. `to_dot` now escapes backslashes,
  quotes, and newlines in labels and node ids.
- **Strict input validation** — `validate_character_data` now rejects non-integer float
  ability scores (e.g. `15.7`; integral floats like `15.0` are fine), reports an omitted
  `level` (previously masked by the default-to-1 normalization), and handles non-dict
  input without crashing.

### Added
- **Property-based tests** (hypothesis, dev-only) — invariants checked over wide input
  ranges: ability-modifier and proficiency-bonus formulas, PB in its published 2..6 range,
  and HP monotonic in level.
- **Examples** — runnable scripts under `examples/` (quickstart, multiclass, stat-diff,
  custom operation, graph export), exercised in CI so they can't rot.
- **Input validation** — `validate_character_data(data) -> list[str]` reports problems
  (missing/out-of-range ability scores, bad level, missing class) that would otherwise be
  silently coerced into a plausible-but-wrong sheet. `evaluate_character(data, strict=True)`
  raises `CharacterInputError` on those; default lenient behaviour is unchanged. The CLI
  gains `dndwright eval --strict`.
- **Custom operations** — `register_operation(name, fn)` extends the formula DSL without
  forking. Custom ops are recognised everywhere the registry is consulted (`evaluate`,
  `validate_ruleset`, `known_operations`). Built-in op names cannot be overwritten; the
  `Operation` callable type is exported for typing custom ops.
- **CLI** — a `dndwright` console command (stdlib only): `eval` (character JSON → sheet,
  file or stdin), `graph` (export the DAG as Mermaid/DOT), `content` (list/dump bundled
  content), `validate` (check a ruleset). Usable without writing Python.
- **Graph export** — `to_mermaid(ruleset)` and `to_dot(ruleset)` render the computation
  DAG as Mermaid or Graphviz DOT (node shapes by type, optional clustering by group),
  making the "formulas as data / inspectable DAG" design visible for docs and debugging.
- **Ruleset validation** — `validate_ruleset(ruleset) -> list[ValidationIssue]` and
  `assert_valid_ruleset(ruleset)` statically check a ruleset before evaluation, catching
  authoring mistakes (unknown op, key/`id` mismatch, missing formula, cycles) with clear
  messages instead of a deep runtime `EvaluationError`, plus warnings (INPUT-with-formula,
  unknown explicit input ref, absent lookup table). Also `known_operations()` lists every
  op a formula may use, and `ValidationIssue` / `RulesetValidationError` are exported.

### Changed
- **Faster evaluation** — the evaluator now caches each ruleset's topological order
  instead of recomputing it on every `evaluate()` call (~2.2× faster per evaluation;
  ~0.41 → ~0.18 ms for a level-5 character). Cache is keyed per ruleset instance and
  evicted on garbage collection, so custom/transient rulesets neither leak nor go stale.

### Docs
- Revamped the README landing page: centered header, status badges (PyPI version, Python
  versions, CI, license, typed), and a hero SVG of the computation graph (`assets/`).
- Added a "Command line" section and `validate_ruleset` / `to_mermaid` / `to_dot` rows.

### Packaging
- Ship a `py.typed` marker (PEP 561) so downstream type-checkers see dndwright's type
  hints. Added Python 3.10–3.13, `Typing :: Typed`, `Intended Audience :: Developers`,
  and `Topic :: Software Development :: Libraries` classifiers, plus `Changelog`/`Issues`
  project URLs. Internal: `OPERATIONS` is now typed `dict[str, Operation]`.

## [0.3.0] — 2026-06-01

### Added
- **Bundled starter content** — `load_content(category)` + `categories()`: original
  homebrew classes/species/creatures, plus 236 SRD 5.2 (CC-BY) magic items.
- **LLM-agnostic content generator** — `generate_library(llm, ...)` (and
  `generate_classes`/`species`/`creatures`): you pass a `complete_json(prompt, system)
  -> dict` callable wrapping your own LLM; prompts produce *original homebrew* (no
  official content), matching the bundled schema and component ontology.

## [0.2.0] — 2026-06-01

### Added
- **Component ontology** — `load_ontology()` → `Ontology`: a graph schema for D&D
  building blocks (Class, Species, Spell, Equipment, MagicItem, Background, Feat,
  Subclass, Creature) and how a Character connects to them (`HAS_*`, `INSTANCE_OF`,
  `HAS_STAT_BLOCK`). Typed models (`NodeTypeDef`, `EdgeTypeDef`, `PropertyDef`) with
  `edges_from`/`edges_to` helpers, parsed from the bundled `dnd.yaml`.
- Dependency: `pyyaml` (for the ontology loader).

## [0.1.0] — 2026-06-01

Initial release. The D&D 5e (2024) rules & character-computation engine, extracted
from a working application.

### Added
- `evaluate_character(data) -> dict` — one-call evaluation: character data in,
  computed sheet out (ability modifiers, proficiency, saves, spell DC/attack, HP,
  AC, initiative, …).
- The computation engine: `DND_5E_2024_RULESET` (a 135-node DAG), `evaluate`,
  `assemble_character_inputs`, `apply_modifiers`, and the `Ruleset` / `ComputationNode`
  / `FormulaSpec` / `NodeType` schema — formulas as data, not code.
- Neutral adapters: `character_data_to_inputs`, `computed_values_to_sheet`.
- Typed component models under `dndwright.rules.components`
  (`ClassMechanics`, `SpeciesMechanics`, …) and SRD-derived rules tables.

Pure (pydantic + stdlib); no application/framework coupling. Rules content derives
from the SRD 5.2 (CC-BY-4.0); see NOTICE.

[Unreleased]: https://github.com/sligara7/dndwright/compare/v0.9.0...HEAD
[0.9.0]: https://github.com/sligara7/dndwright/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/sligara7/dndwright/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/sligara7/dndwright/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/sligara7/dndwright/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/sligara7/dndwright/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/sligara7/dndwright/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/sligara7/dndwright/compare/v0.3.0...v0.4.0
[0.1.0]: https://github.com/sligara7/dndwright/releases/tag/v0.1.0
