<h1 align="center">dndwright</h1>

<p align="center">
  <em>A domain-neutral D&amp;D 5e (2024) rules &amp; character-sheet computation engine —
  formulas as data, not code.</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/dndwright/"><img alt="PyPI" src="https://img.shields.io/pypi/v/dndwright.svg"></a>
  <a href="https://pypi.org/project/dndwright/"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/dndwright.svg"></a>
  <a href="https://github.com/sligara7/dndwright/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/sligara7/dndwright/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/sligara7/dndwright/blob/main/LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-blue.svg"></a>
  <img alt="Typed" src="https://img.shields.io/badge/typing-PEP%20561-blue.svg">
</p>

<p align="center">
  <img alt="dndwright computation graph: ability scores, level, class and equipment flow through ability modifiers and proficiency bonus to saves, skills, spell DC/attack, spell slots, HP, AC and initiative" width="760" src="https://raw.githubusercontent.com/sligara7/dndwright/main/assets/computation-graph.svg">
</p>

A character sheet is modelled as a **directed acyclic computation graph** — nodes are values,
edges are dependencies, and formulas are *data* (a JSON-serialisable DSL), not code. Pure
Python (`pydantic` + stdlib), no application or framework coupling: map your own character
data in, read computed stats out.

> ⚠️ **Early development (alpha).** The API is still moving and may change between minor
> versions while at `0.x`. Usable today — pin a version if you depend on it.

## Install

```bash
pip install git+https://github.com/sligara7/dndwright.git
# or, for local development:
pip install -e ".[dev]"
```

## Quickstart

```python
from dndwright import evaluate_character

sheet = evaluate_character({
    "ability_scores": {"strength": 8, "dexterity": 14, "constitution": 14,
                       "intelligence": 18, "wisdom": 12, "charisma": 10},
    "class_data": {"class_name": "wizard"},
    "species_data": {"name": "Human", "speed": 30},
    "level": 5,
})

sheet["proficiency_bonus"]    # 3
sheet["ability_modifiers"]    # {"intelligence": 4, "dexterity": 2, ...}
sheet["spellcasting_type"]    # "full_caster"
# ...plus armor_class, hit_points, hit_dice, initiative, saves, features, ...
```

Lower level — assemble typed inputs and evaluate against the ruleset:

```python
from dndwright import DND_5E_2024_RULESET, assemble_character_inputs, evaluate, apply_modifiers
from dndwright.rules.components import ClassMechanics

inputs   = assemble_character_inputs(class_mechanics=..., ability_scores={...}, level=5)
computed = apply_modifiers(evaluate(DND_5E_2024_RULESET, inputs), inputs)
```

## Command line

Installing the package also installs a `dndwright` command (no Python required):

```bash
dndwright eval character.json          # character JSON → computed sheet (or '-' for stdin)
dndwright graph --format mermaid        # export the computation DAG (mermaid|dot)
dndwright content magic_items           # dump bundled content (omit category to list)
dndwright validate ruleset.json         # check a ruleset (built-in if omitted)
```

## Rolling dice

A self-contained, typed dice engine (`dndwright.dice`) — deterministic by default:

```python
from dndwright.dice import DiceEngine

eng = DiceEngine(seed=42)               # reproducible (stdlib RNG)
eng.roll("4d6kh3").total                # keep highest 3 of 4
eng.roll("1d20", advantage=True)        # -> ExpressionResult
eng.roll_attack(modifier=5, target_ac=15).is_hit
eng.roll_damage("2d8", is_critical=True)  # crit doubles the dice

# unpredictable production rolls (no NumPy dependency):
import secrets
DiceEngine(rng=secrets.SystemRandom())
```

## Combat rules

Pure, persistence-free 5e combat (`dndwright.combat`) — state is a frozen value object,
every op is `(state, input) → (new_state, explanation)`:

```python
from dndwright.combat import CombatantState, apply_damage, roll_death_save
from dndwright.dice import DiceEngine

s = CombatantState(current_hp=8, max_hp=20, temp_hp=3)
s, applied = apply_damage(s, 10)            # temp HP absorbs first, overkill tracked
s, save = roll_death_save(s, DiceEngine(seed=1))   # nat 20 → 1 HP; 3 fails → dead
s.is_stable, s.is_dead, s.hp_percentage
```

Your app owns persistence: load a row → call these → write the new state back. The rules
never see a database.

## Why a computation graph?

Derived character values form a dependency DAG: ability scores → modifiers → proficiency →
save DCs / spell slots / AC / HP. dndwright represents that DAG explicitly and stores the
formulas as **data** (`FormulaSpec`: an op + args), so the rules are inspectable, testable,
and serialisable — not buried in imperative code. `DND_5E_2024_RULESET` is a 135-node graph.

## What's inside

| Component | What it does |
|-----------|--------------|
| `evaluate_character` | One call: character data dict → fully computed sheet. |
| `DND_5E_2024_RULESET` | The 135-node 5e-2024 computation DAG (formulas as data). |
| `evaluate` / `assemble_character_inputs` / `apply_modifiers` | The lower-level engine. |
| `Ruleset` / `ComputationNode` / `FormulaSpec` / `NodeType` | The DAG schema. |
| `validate_ruleset` / `assert_valid_ruleset` | Static integrity check for a ruleset (unknown ops, cycles, dangling refs) — catch authoring errors before evaluation. |
| `to_mermaid` / `to_dot` | Render the computation DAG as Mermaid or Graphviz DOT — *see* the dependency graph. |
| `dndwright.dice` | Typed dice engine: parse/roll 5e expressions, attacks, saves, damage, stat arrays. |
| `dndwright.combat` | Pure combat rules over a frozen `CombatantState`: damage, temp HP, healing, death saves. |
| `dndwright.combat.initiative` | Pure initiative: roll, order (DEX tie-break), advance/rewind turns. |
| `dndwright.rules.components` | Typed inputs (`ClassMechanics`, `SpeciesMechanics`, …). |
| `dndwright.rules.lookup_tables` | SRD-derived rules tables (hit dice, spell slots, AC, saves). |

## API stability

The public API is exactly `dndwright.__all__`, pinned by `tests/test_api_contract.py`.
Versioning follows [SemVer](https://semver.org/); at `0.x` minor versions may break, with
every change recorded in `CHANGELOG.md`. Maintainers: the release process is documented in
[`RELEASING.md`](RELEASING.md).

## Credits & license

MIT licensed (see `LICENSE`). The rules tables encode game *mechanics* derived from the
**D&D System Reference Document 5.2** (© Wizards of the Coast, **CC-BY-4.0**); see `NOTICE`.
Not affiliated with or endorsed by Wizards of the Coast. Contains no PHB/DMG/MM content.
