# Changelog

All notable changes to dndwright are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project aims to follow
[Semantic Versioning](https://semver.org/).

**Public API** = the names exported in `dndwright.__all__` (pinned by
`tests/test_api_contract.py`). While the version is `0.x`, minor versions may make
breaking changes; these will always be noted here.

## [Unreleased]

## [0.25.0] — 2026-06-13

### Added
- **Power-budget validator.** `validate_power_budget(species_data, class_data,
  subclass_data, level)` returns budget overage problems (species traits,
  class+subclass features per level, combined species-vs-learned split). Baselines
  derived from dndwright's own SRD 5.2.1 content: 9 species (5 trait max, 3
  high-impact max) and 12 classes (cumulative feature budgets by level). High-impact
  traits (flight, innate casting, resistance, breath weapon) weighted heavier.
  Superman+Batman double-stacking caught at low levels. Exported in `dndwright.__all__`.
- 17 new unit tests for power-budget coverage (balanced vs over-budget vs edge cases).

### Changed
- `__all__` expanded: +1 name (`validate_power_budget`).

## [0.24.1] — 2026-06-13

### Documentation
- Homebrew validators added to README feature table.

## [0.24.0] — 2026-06-13

### Added
- **Homebrew validation module.** New `rules/homebrew_validator.py` with
  `validate_class_homebrew()`, `validate_species_homebrew()`,
  `validate_subclass_homebrew()`, and `validate_background_homebrew()` — each
  returns a list of human-readable rule-violation strings (empty = legal).
  Structural checks per SRD 5.2.1: hit-die legality (d6/d8/d10/d12),
  saving-throw proficiency pairs (one strong + one weak), archetype and
  spellcasting-type validity, feature-level ranges (1–20, no duplicates),
  species speed limits, background skill counts, and more.
- `validate_homebrew(component_type, data)` router and `HOMEBREW_VALIDATORS`
  lookup dict. All new names exported in `dndwright.__all__`.
- 30+ unit tests for all validators, covering legal components (empty
  return), illegal components (each check catches), and the aggregate
  router.

### Changed
- `__all__` expanded: +7 names (`validate_class_homebrew`,
  `validate_species_homebrew`, `validate_subclass_homebrew`,
  `validate_background_homebrew`, `validate_homebrew`, `HOMEBREW_VALIDATORS`).
- `tests/test_api_contract.py` `EXPECTED_PUBLIC` and `EXPECTED_SIGNATURES`
  updated for the new exports.

## [0.23.2] — 2026-06-06

### Documentation
- **Two new README/PyPI diagrams.** `assets/compose.svg` shows lego-style components snapping
  onto the ruleset — typed `set`/`add`/`union` contributions that keep the target node's id, so
  one snap-in recomputes the whole downstream subtree. `assets/theme-scaling.svg` shows one
  computation graph re-skinned per setting via `ThemeScalingLayer`: the same `plate` node emerges
  as AC 18 (traditional / modern, re-flavored) or AC 19 (sci-fi / steampunk) through
  `input_overrides`, `lookup_overrides`, and display-only `flavor_renames`.
- **New README sections** — "Composable — snap mini-graphs onto the ruleset" and "Re-skin for
  any setting — theme scaling" (theme scaling was previously undocumented in the README), plus a
  `apply_theme_scaling` / `ThemeScalingLayer` row in the feature table. Docs-only; no code change.

## [0.23.1] — 2026-06-06

### Fixed
- **Critical damage preserves dice modifiers** — `DiceEngine.roll_damage(expr, is_critical=True)`
  doubled die counts by rebuilding the expression as bare `XdY`, silently dropping per-group
  `keep`/`drop`/`reroll`/`exploding` flags. A crit on `1d6!+2` now stays exploding (`2d6!+2`)
  instead of becoming a plain `2d6+2`. As part of the fix, `str(DiceGroup)` now serialises
  reroll-once as `ro` (was `r`), so the spec round-trips through `parse_expression`.
- **Species damage immunities mis-categorised** — `_build_species_traits` tagged damage
  immunities with `category: "resistance"` (condition immunities were already correct); they
  are now `category: "immunity"`.

### Changed
- **`compose()` fails loudly on contradictory contributions** — a target that receives both a
  `union` (set-valued) and an `add`/`set` (numeric) contribution now raises `ValueError` instead
  of silently dropping the numeric ones.

### Performance
- **Topological sort** uses a binary heap (`heapq`) instead of re-sorting the ready-queue every
  iteration — same deterministic order, `O(V·log V + E)` instead of `O(V²·log V)`. (Result is
  still cached per ruleset, so this only matters the first time a large graph is evaluated.)

### Internal
- `cli._read_json` closes the file it opens (was leaked); `cli` content lookup calls
  `categories()` once instead of twice.
- `assembler.assemble_inputs` copies the ability-score dict once up front rather than on each
  increase.

## [0.23.0] — 2026-06-05

### Added
- **`evaluate_character(..., scaling=...)`** — `evaluate_character`, `compute_key_stats`, and
  `compute_stat_diff` now take an optional `scaling: ThemeScalingLayer` keyword. When given,
  the sheet (or key-stat snapshot / before-after diff) is computed against the theme-scaled
  ruleset via `apply_theme_scaling`, so a campaign's setting (sci-fi, modern warfare, …) shapes
  the character's mechanical values. `scaling=None` (default) reproduces the stock 5e behaviour
  exactly — existing callers are unaffected. New `tests/test_character_theme_scaling.py`.

## [0.22.0] — 2026-06-05

### Added
- **`apply_theme_scaling(ruleset, layer)`** (`dndwright`) — folds a `ThemeScalingLayer`'s
  mechanical overrides onto a ruleset so the same computation graph yields
  setting-appropriate values (modern warfare, sci-fi, steampunk, …). `lookup_overrides`
  deep-merge into the ruleset's lookup tables (creating tables/keys, preserving the rest);
  `input_overrides` re-baseline a node's `default_value` (eval precedence stays *explicit
  input > themed default > original default*, so a theme sets the world's baseline without
  clobbering a value a character explicitly carries). `flavor_renames` are display-only and
  ignored here. Pure (the base ruleset is untouched) and composes with `compose()`. Raises
  `KeyError` on an `input_overrides` id that names no node, to catch authored-layer typos.
  This makes the previously inert `ThemeScalingLayer` / `PREDEFINED_THEME_SCALING` data a
  working feature. New `tests/test_theme_scaling.py`.

## [0.21.0] — 2026-06-04

### Added
- **Exported Pydantic content models** (`dndwright.content.models`) — canonical, strict
  (`extra="forbid"`) models for all 11 content categories (`Creature`, `CharClass`,
  `Species`, `Spell`, `MagicItem`, `Background`, `Feat`, `Weapon`, `Armor`, `Condition`)
  plus nested sub-models and the `Modifier` (component) spec, formalizing the content
  structure that previously lived implicitly in the JSON assets. All 1012 bundled assets
  validate against their models. Exported via `__all__` so downstream services conform to /
  subclass these models, making generated content structurally identical to bundled SRD
  content.

## [0.20.0] — 2026-06-03

### Added
- **`weapon_attack()`** (`dndwright.combat`) — composes a weapon (from the bundled SRD
  table) with an attacker's `strength_mod`/`dexterity_mod`, `proficiency_bonus`, and any
  magic/feature bonuses into a `WeaponAttack`: the to-hit `attack_bonus` and a rollable
  `damage` expression (e.g. `"1d8 + 3"`). It applies the rules' ability selection (Ranged →
  Dex, Finesse melee → better of Str/Dex, else Str), the Versatile two-handed die, and the
  weapon's mastery (name + effect text, plus the Topple save DC). Pure — feed the result to
  `DiceEngine.roll_attack` / `roll_damage`. New `examples/weapon_attack.py`.
- **Spell `component` specs** for the curated graph-mappable spells: `load_content("spells")`
  entries for **Mage Armor** (gated +3 AC while unarmored), **Shield of Faith** (+2 AC), and
  **Shield** (+5 AC) now carry a `component` that snaps onto a character's graph via
  `component_from_content` — the same content-as-data contract magic items use. Spells needing
  graph nodes dndwright doesn't model yet (a generic attack-roll bonus, a temp-HP channel, an
  AC floor) stay reference-only.
- **Background ability increases as parameterized `component`s.** Each `load_content("backgrounds")`
  entry gains `choices` + a `component` template (`{plus_two}_score` +2, `{plus_one}_score` +1)
  filled at compose time from the background's three abilities — mirroring the Ability Score
  Improvement feat. The `+1/+1/+1` alternative spread is documented in the file metadata.
- **Class features now carry SRD prose, plus subclass progressions.** Every `load_content("classes")`
  feature gains a `description` (the full SRD feature text), and each class gains
  `subclass_features` — the SRD subclass's own level-by-level features (name + level +
  description). 232 feature descriptions across the 12 classes + subclasses, extracted from the
  SRD (font-segmented so the interleaved progression/spell-slot tables and option catalogs are
  filtered out, not folded into the prose).

### Changed
- **`load_content("creatures")` is now the full SRD 5.2 Monsters A–Z bestiary** (330 stat blocks),
  replacing the 12 homebrew sample creatures. Each entry is structured data: the six ability
  scores + saving-throw proficiencies, skills, senses (darkvision/blindsight/tremorsense/truesight
  + passive Perception), damage resistances/immunities/vulnerabilities, condition immunities,
  languages, CR/XP (incl. lair XP)/proficiency bonus, speeds, and `traits`/`actions`/`bonus_actions`/
  `reactions`/`legendary_actions` — with attack bonus, reach/range, damage (dice + type), save DC,
  and recharge parsed out of each action. SRD 5.2 (CC-BY); the homebrew-creature *generator*
  (`generate_creatures`) is unchanged. NOTICE updated (creatures is now SRD-derived).

## [0.19.0] — 2026-06-03

### Added
- **The SRD weapon + armor tables** as two new content categories. `load_content("weapons")` —
  all 38 SRD weapons (category Simple/Martial, kind Melee/Ranged, damage dice + type, properties,
  mastery, weight, cost). `load_content("armor")` — the 12 armors + Shield (category, base AC,
  dex cap, strength requirement, stealth disadvantage, weight, cost; a Shield carries `ac_bonus`).
  Both **agree with the rules lookup tables** (`weapon_mastery_map`, `armor_base_ac`) — tests pin
  zero drift. SRD 5.2 (CC-BY).

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

[Unreleased]: https://github.com/sligara7/dndwright/compare/v0.23.2...HEAD
[0.23.2]: https://github.com/sligara7/dndwright/compare/v0.23.1...v0.23.2
[0.23.1]: https://github.com/sligara7/dndwright/compare/v0.23.0...v0.23.1
[0.23.0]: https://github.com/sligara7/dndwright/compare/v0.22.0...v0.23.0
[0.22.0]: https://github.com/sligara7/dndwright/compare/v0.21.0...v0.22.0
[0.21.0]: https://github.com/sligara7/dndwright/compare/v0.20.0...v0.21.0
[0.20.0]: https://github.com/sligara7/dndwright/compare/v0.19.0...v0.20.0
[0.19.0]: https://github.com/sligara7/dndwright/compare/v0.18.0...v0.19.0
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
