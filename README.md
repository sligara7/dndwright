# dndwright

> ⚠️ **Early development (v0.1, alpha).** The API is still moving and may change without
> notice between minor versions. Extracted from a working application; usable today, but
> pin a tag/commit if you depend on it.

**A domain-neutral D&D 5e (2024) rules & character-sheet computation engine.** A character
sheet is modelled as a **directed acyclic computation graph** — nodes are values, edges are
dependencies, and formulas are *data* (a JSON-serialisable DSL), not code. Pure Python
(`pydantic` + stdlib), no application or framework coupling: map your own character data in,
read computed stats out.

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
| `dndwright.rules.components` | Typed inputs (`ClassMechanics`, `SpeciesMechanics`, …). |
| `dndwright.rules.lookup_tables` | SRD-derived rules tables (hit dice, spell slots, AC, saves). |

## API stability

The public API is exactly `dndwright.__all__`, pinned by `tests/test_api_contract.py`.
Versioning follows [SemVer](https://semver.org/); at `0.x` minor versions may break, with
every change recorded in `CHANGELOG.md`.

## Credits & license

MIT licensed (see `LICENSE`). The rules tables encode game *mechanics* derived from the
**D&D System Reference Document 5.2** (© Wizards of the Coast, **CC-BY-4.0**); see `NOTICE`.
Not affiliated with or endorsed by Wizards of the Coast. Contains no PHB/DMG/MM content.
