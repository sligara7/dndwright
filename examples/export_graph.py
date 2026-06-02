"""Render the 135-node computation DAG as Mermaid or Graphviz DOT.

    python examples/export_graph.py                # Mermaid to stdout
    python examples/export_graph.py | dot -Tsvg    # (with --dot) → SVG via Graphviz

Or use the CLI: ``dndwright graph --format dot``.
"""

import sys

from dndwright import DND_5E_2024_RULESET, to_dot, to_mermaid

if "--dot" in sys.argv:
    print(to_dot(DND_5E_2024_RULESET))
else:
    # Just the first lines — the full graph is large (135 nodes).
    text = to_mermaid(DND_5E_2024_RULESET)
    print("\n".join(text.splitlines()[:12]))
    print("...")
    print(f"\n({len(DND_5E_2024_RULESET.nodes)} nodes total — "
          "pipe `dndwright graph --format dot | dot -Tsvg` for the full picture)")
