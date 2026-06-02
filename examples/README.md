# Examples

Runnable scripts for the main dndwright workflows. From the repo root:

```bash
pip install -e .
python examples/quickstart.py
```

| Script | Shows |
|--------|-------|
| [`quickstart.py`](quickstart.py) | One call: character dict → computed sheet (plus `strict=True`). |
| [`multiclass.py`](multiclass.py) | Fighter 5 / Wizard 3 via the typed lower-level engine. |
| [`stat_diff.py`](stat_diff.py) | Which key stats change on level-up (`compute_stat_diff`). |
| [`custom_operation.py`](custom_operation.py) | Extend the DSL with `register_operation` + a custom `Ruleset`. |
| [`export_graph.py`](export_graph.py) | Render the computation DAG as Mermaid / Graphviz DOT. |
| [`dice.py`](dice.py) | Roll 5e dice (expressions, advantage, attacks/saves, crit damage, stat arrays). |
| [`combat.py`](combat.py) | Resolve a combat round with pure rules: damage, temp HP, death saves, healing. |
| [`initiative.py`](initiative.py) | Roll initiative, order combatants (DEX tie-break), walk the turn tracker. |
| [`conditions.py`](conditions.py) | Inspect condition effects/flags, tick durations, resolve save-ends. |

See also the `dndwright` CLI (`dndwright eval`, `graph`, `content`, `validate`).
