"""Render a :class:`Ruleset`'s computation graph as Mermaid or Graphviz DOT.

Makes the "formulas as data / inspectable DAG" pitch tangible — drop the output in
docs, a README, or a Graphviz/Mermaid renderer to *see* the dependency graph.

    from dndwright import DND_5E_2024_RULESET, to_mermaid, to_dot
    print(to_mermaid(DND_5E_2024_RULESET))   # paste into a Mermaid renderer
    print(to_dot(DND_5E_2024_RULESET))       # pipe to `dot -Tsvg`

Edges point from a dependency to the node that consumes it (evaluation order). With
``cluster=True`` (default) nodes are grouped into subgraphs by ``node.group``.
"""

from __future__ import annotations

from .evaluator import _get_dependencies
from .schema import Ruleset

# Mermaid bracket pairs per node type → a recognisable shape for each kind of node.
_MERMAID_SHAPE = {
    "input": ("([", "])"),    # stadium — provided values
    "formula": ("[", "]"),    # rectangle — computed
    "lookup": ("[(", ")]"),   # cylinder — table lookup
    "aggregate": ("{{", "}}"),  # hexagon — combines many
    "output": (">", "]"),     # asymmetric — terminal display
}

_DOT_SHAPE = {
    "input": "stadium",
    "formula": "box",
    "lookup": "cylinder",
    "aggregate": "hexagon",
    "output": "note",
}


def _safe_ids(ruleset: Ruleset) -> dict[str, str]:
    """Map each node id to a renderer-safe token (ids may contain dots/dashes)."""
    return {nid: f"n{i}" for i, nid in enumerate(ruleset.nodes)}


# Characters that break Mermaid label/shape parsing → HTML numeric char refs.
# '#' must be escaped first since the replacements introduce '#'.
_MERMAID_ESC = {"#": 35, '"': 34, "[": 91, "]": 93, "(": 40, ")": 41,
                "{": 123, "}": 125, "<": 60, ">": 62}


def _mermaid_text(s: str) -> str:
    """Escape arbitrary text for use inside a Mermaid quoted label."""
    s = s.replace("#", "#35;")
    for ch, code in _MERMAID_ESC.items():
        if ch == "#":
            continue
        s = s.replace(ch, f"#{code};")
    return s


def _dot_text(s: str) -> str:
    """Escape arbitrary text for a Graphviz DOT double-quoted string."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")


def _edges(ruleset: Ruleset) -> list[tuple[str, str]]:
    """(dependency_id, dependent_id) pairs, sorted for deterministic output."""
    nodes = ruleset.nodes
    out: list[tuple[str, str]] = []
    for nid, node in nodes.items():
        for dep in _get_dependencies(node, nodes):
            out.append((dep, nid))
    return sorted(out)


def _grouped(ruleset: Ruleset) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for nid, node in ruleset.nodes.items():
        groups.setdefault(node.group or "", []).append(nid)
    return groups


def to_mermaid(ruleset: Ruleset, *, direction: str = "TD", cluster: bool = True) -> str:
    """Render ``ruleset`` as a Mermaid ``graph`` definition.

    Args:
        direction: Mermaid flow direction (``"TD"``, ``"LR"``, …).
        cluster: group nodes into subgraphs by ``node.group``.
    """
    sid = _safe_ids(ruleset)
    nodes = ruleset.nodes
    lines = [f"graph {direction}"]

    def _decl(nid: str) -> str:
        node = nodes[nid]
        open_b, close_b = _MERMAID_SHAPE.get(node.node_type.value, ("[", "]"))
        label = _mermaid_text(node.label or nid)
        return f'    {sid[nid]}{open_b}"{label}"{close_b}'

    if cluster:
        # A subgraph needs a safe id; the group name becomes its quoted title, so
        # group names with spaces/special chars don't produce invalid Mermaid.
        for i, (group, members) in enumerate(sorted(_grouped(ruleset).items())):
            title = _mermaid_text(group or "ungrouped")
            lines.append(f'  subgraph sg{i}["{title}"]')
            for nid in sorted(members):
                lines.append(_decl(nid))
            lines.append("  end")
    else:
        for nid in sorted(nodes):
            lines.append(_decl(nid))

    for dep, nid in _edges(ruleset):
        lines.append(f"    {sid[dep]} --> {sid[nid]}")

    return "\n".join(lines)


def to_dot(ruleset: Ruleset, *, cluster: bool = True) -> str:
    """Render ``ruleset`` as a Graphviz DOT ``digraph`` (pipe to ``dot -Tsvg``).

    Args:
        cluster: group nodes into ``cluster_*`` subgraphs by ``node.group``.
    """
    nodes = ruleset.nodes
    lines = ["digraph ruleset {", "  rankdir=TB;", '  node [fontname="sans-serif"];']

    def _decl(nid: str) -> str:
        node = nodes[nid]
        shape = _DOT_SHAPE.get(node.node_type.value, "box")
        label = _dot_text(node.label or nid)
        return f'  "{_dot_text(nid)}" [label="{label}", shape={shape}];'

    if cluster:
        for i, (group, members) in enumerate(sorted(_grouped(ruleset).items())):
            title = group or "ungrouped"
            lines.append(f"  subgraph cluster_{i} {{")
            lines.append(f'    label="{title}";')
            for nid in sorted(members):
                lines.append("  " + _decl(nid))
            lines.append("  }")
    else:
        for nid in sorted(nodes):
            lines.append(_decl(nid))

    for dep, nid in _edges(ruleset):
        lines.append(f'  "{_dot_text(dep)}" -> "{_dot_text(nid)}";')

    lines.append("}")
    return "\n".join(lines)
