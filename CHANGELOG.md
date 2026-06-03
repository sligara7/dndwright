# Changelog

All notable changes to dndwright are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project aims to follow
[Semantic Versioning](https://semver.org/).

**Public API** = the names exported in `dndwright.__all__` (pinned by
`tests/test_api_contract.py`). While the version is `0.x`, minor versions may make
breaking changes; these will always be noted here.

## [Unreleased]

## [0.18.0] — 2026-06-03

### Added
- **The 4 SRD backgrounds** as a new bundled content category (`load_content("backgrounds")`):
  Acolyte, Criminal, Sage, Soldier — each with its three ability scores (player-allocated per
  the 2024 rule), the Origin **feat** it grants (which resolves to a bundled feat in
  `load_content("feats")` — a test pins this), two skill proficiencies, a tool proficiency, and
  starting equipment. Completes character origins (species + backgrounds). SRD 5.2 (CC-BY).

## [0.17.0] — 2026-06-03

### Added
- **The 12 SRD classes** as bundled content (`load_content("classes")`): Barbarian, Bard,
  Cleric, Druid, Fighter, Monk, Paladin, Ranger, Rogue, Sorcerer, Warlock, Wizard — each with
  core traits (hit die, primary ability, saving throws, skill/weapon/armor proficiencies,
  starting equipment, spellcasting type + ability), the level 1–20 **feature progression**, and
  the SRD subclass. `hit_die`/`saving_throws`/`spellcasting` mirror the rules lookup tables (a
  test pins the agreement); a caster's spell list is derivable from `load_content("spells")`.
  Replaces the former homebrew sample classes; SRD 5.2 (CC-BY) — only `creatures` remains
  homebrew. NOTICE updated.

## [0.16.0] — 2026-06-03

### Added
- **The full SRD spell catalog** — all **339** SRD 5.2 spells (cantrips through level 9) as
  bundled content (`load_content("spells")`): name, level, school, casting time, range,
  components, duration, class lists, and the full description. The biggest content gap, now a
  complete reference. Data-only for now — mechanical `component` specs (spells that snap onto
  the character graph, e.g. *Mage Armor*, *Shield of Faith*, *Bless*) are a follow-up. SRD 5.2
  (CC-BY) — see NOTICE.

## [0.15.0] — 2026-06-03

### Added
- **The 9 SRD species** as bundled content (`load_content("species")`): Dragonborn, Dwarf,
  Elf, Gnome, Goliath, Halfling, Human, Orc, Tiefling — with size, speed, senses, traits, and
  a `component` for the graph-mappable bits: **Dwarf** (poison resistance + Dwarven Toughness
  `hp_max += level`), **Goliath** (speed 35 via `override`), and **Dragonborn** / **Tiefling**
  (a chosen damage resistance, a `{placeholder}` filled from `choices`). Replaces the former
  homebrew sample species; SRD 5.2 (CC-BY) — see NOTICE.
- **`{placeholder}` substitution now recurses into list `amount`s** in `component_from_content`,
  so a `union` resistance type can be chosen (`"amount": ["{ancestry}"]` +
  `choices={"ancestry": "fire"}`) — not just scalar targets/args.

### Changed
- The bundled `species` catalog is now SRD-derived (was homebrew); `classes` and `creatures`
  remain homebrew sample content. NOTICE updated to attribute each.

## [0.14.0] — 2026-06-03

### Added
- **`override` contribution mode** for `compose` — *replaces* a target's base value (last wins),
  then add/set/union stack on top. Unlike `set` (which is `max`, so it can't lower a value below
  the input default), `override` makes an authoritative value hold even below the default — e.g.
  a creature stat block's "STR **is** 8", not "STR becomes at least 8". `set` STR 6 → 10 (clamped);
  `override` STR 6 → 6.
- **`clean_damage_types(values)`** (in `dndwright.combat`) — the single source of truth for
  normalising damage-type strings (lower-case, de-dupe, drop anything not in `DAMAGE_TYPES`).
  `combatant_defenses` now delegates to it; external callers building resistance contributions
  should use it too rather than re-implementing the filter.

## [0.13.0] — 2026-06-02

### Added
- **Portable Component (de)serialisation** — `component_to_dict(component)` /
  `component_from_dict(data)` (+ `COMPONENT_SCHEMA_VERSION`): stable public wrappers over
  pydantic that stamp a schema version, so a `Component` can be persisted as data (a DB column,
  a graph-node property) and rebuilt later. The seam external graph stores use to keep
  components as first-class graph content.
- **Damage-defence channels on the ruleset** — `DND_5E_2024_RULESET` now bundles three empty
  `union` nodes `resistances` / `immunities` / `vulnerabilities` (ids exported as
  `RESISTANCES_NODE` / `IMMUNITIES_NODE` / `VULNERABILITIES_NODE` / `DAMAGE_CHANNELS`). A
  component (a Ring of Resistance, a species trait) contributes damage types via a `union`
  contribution, and the evaluated sheet exposes the composed sets (empty `()` by default — no
  existence-branching needed). Node count 135 → 138.
- **`combatant_defenses(computed)`** (in `dndwright.combat`) — pulls those channels out of an
  evaluated graph into the exact kwargs `CombatantState` wants (lower-cased, intersected with
  `DAMAGE_TYPES` so narrative junk is dropped), closing the loop to `apply_damage(..., damage_type=...)`.

## [0.12.0] — 2026-06-02

### Added
- **Gated (conditional) contributions** — a `component` modifier may carry a `condition`
  (a `{op, args}` expression over host nodes) so the contribution applies *only while the
  condition holds*, otherwise contributing the off-identity (`0`, or `()` for union). The
  bonus then tracks host state: compose once and it re-evaluates as the character changes,
  no re-compose. Bundled examples: the **Defense** fighting style (+1 AC while wearing armor)
  and **Bracers of Defense** (+2 AC while unarmored *and* shieldless — a compound gate).
- `component_from_content` now compiles a modifier's value/condition as a recursive
  expression tree — nested `{op, args}` are flattened into the component's sub-graph — so an
  arbitrarily complex gate (e.g. `all_true(eq(armor_type, "none"), not(has_shield))`) is just
  data.
- New formula ops `ne` (not-equal) and `all_true` (logical AND over its args) for writing
  gate conditions.

## [0.11.0] — 2026-06-02

### Added
- **SRD feats as bundled content + composable components.** New `feats` content category:
  all 16 SRD 5.2.1 feats (Origin / General / Fighting Style / Epic Boon) with category,
  prerequisite, repeatable flag and description. The graph-mappable ones carry a `component`:
  **Alert** (Initiative += proficiency bonus), **Grappler** and **Ability Score Improvement**
  (+score). Feats drove two `component_from_content` extensions, both pure data:
  - **dynamic sources** — a modifier may give a `formula` (`{op, args}` over *host* nodes)
    instead of a constant `amount`, so an effect can scale (Alert tracks proficiency bonus).
  - **`{placeholder}` choices** — a `target`/arg may contain a placeholder filled from a
    `choices=` argument, so "increase an ability score of *your choice*" is a template you
    realise at compose time (`component_from_content(asi, choices={"ability": "strength"})`).

### Changed
- `Component.metadata` from `component_from_content` now carries `category` (alongside
  `rarity`/`attunement_required`) instead of a fixed `source` key, since it serves both items
  and feats.

## [0.10.0] — 2026-06-02

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

[Unreleased]: https://github.com/sligara7/dndwright/compare/v0.18.0...HEAD
[0.18.0]: https://github.com/sligara7/dndwright/compare/v0.17.0...v0.18.0
[0.17.0]: https://github.com/sligara7/dndwright/compare/v0.16.0...v0.17.0
[0.16.0]: https://github.com/sligara7/dndwright/compare/v0.15.0...v0.16.0
[0.15.0]: https://github.com/sligara7/dndwright/compare/v0.14.0...v0.15.0
[0.14.0]: https://github.com/sligara7/dndwright/compare/v0.13.0...v0.14.0
[0.13.0]: https://github.com/sligara7/dndwright/compare/v0.12.0...v0.13.0
[0.12.0]: https://github.com/sligara7/dndwright/compare/v0.11.0...v0.12.0
[0.11.0]: https://github.com/sligara7/dndwright/compare/v0.10.0...v0.11.0
[0.10.0]: https://github.com/sligara7/dndwright/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/sligara7/dndwright/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/sligara7/dndwright/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/sligara7/dndwright/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/sligara7/dndwright/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/sligara7/dndwright/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/sligara7/dndwright/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/sligara7/dndwright/compare/v0.3.0...v0.4.0
[0.1.0]: https://github.com/sligara7/dndwright/releases/tag/v0.1.0
