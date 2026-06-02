"""Graph export — Mermaid / DOT renderings are well-formed and complete."""

from dndwright import (
    DND_5E_2024_RULESET,
    ComputationNode,
    FormulaSpec,
    NodeType,
    Ruleset,
    to_dot,
    to_mermaid,
)

R = DND_5E_2024_RULESET


def _small() -> Ruleset:
    nodes = {
        "score": ComputationNode(id="score", node_type=NodeType.INPUT, label="Score",
                                 group="ability_scores"),
        "mod": ComputationNode(id="mod", node_type=NodeType.FORMULA, label="Modifier",
                               group="ability_scores",
                               formula=FormulaSpec(op="ability_mod", args=["score"])),
    }
    return Ruleset(id="t", name="test", nodes=nodes)


class TestMermaid:
    def test_header_and_node_count(self):
        out = to_mermaid(R)
        assert out.startswith("graph TD")
        # every node is declared exactly once (one safe id `nN` per node)
        for i in range(len(R.nodes)):
            assert f"n{i}" in out

    def test_direction_is_configurable(self):
        assert to_mermaid(R, direction="LR").startswith("graph LR")

    def test_edge_uses_safe_ids_not_raw_dotted_ids(self):
        out = to_mermaid(_small())
        assert "n0 --> n1" in out or "n1 --> n0" in out
        # dotted/raw ids would break Mermaid — they must not appear as node tokens
        assert "score -->" not in out

    def test_clusters_render_subgraphs(self):
        out = to_mermaid(R, cluster=True)
        # subgraphs use a safe id + quoted title (so spaced group names stay valid)
        assert 'subgraph sg0["ability_scores"]' in out
        assert out.count("subgraph") == out.count("\n  end")

    def test_no_clusters(self):
        assert "subgraph" not in to_mermaid(R, cluster=False)


class TestDot:
    def test_is_a_digraph(self):
        out = to_dot(R)
        assert out.startswith("digraph ruleset {")
        assert out.rstrip().endswith("}")

    def test_dotted_ids_are_quoted(self):
        out = to_dot(R)
        # DOT tolerates dots inside quoted ids
        assert '"save.wisdom.proficient"' in out

    def test_edge_count_matches_dependencies(self):
        out = to_dot(_small())
        assert '"score" -> "mod";' in out

    def test_clusters(self):
        assert "subgraph cluster_0" in to_dot(R, cluster=True)
        assert "cluster_" not in to_dot(R, cluster=False)


def _node(label: str, group: str = "") -> Ruleset:
    return Ruleset(id="t", name="test", nodes={
        "n": ComputationNode(id="n", node_type=NodeType.INPUT, label=label, group=group),
    })


class TestMermaidEscaping:
    def test_special_chars_in_label_are_escaped(self):
        # [ ] ( ) { } " < > # must not appear raw inside the quoted label text.
        out = to_mermaid(_node('HP [max] (cur) {x} "q" <a> #1'))
        decl = next(line for line in out.splitlines() if line.strip().startswith("n0"))
        label = decl[decl.index('"') + 1:decl.rindex('"')]  # text between the quotes
        # '#' is the entity prefix (e.g. #91;), so it legitimately remains; the others must not.
        for ch in '[](){}<>"':
            assert ch not in label, f"raw {ch!r} leaked into label"
        # literal input '#' became '#35;', and each special char has its numeric entity:
        assert "#91;" in label and "#93;" in label and "#34;" in label and "#35;" in label

    def test_group_with_spaces_yields_valid_subgraph(self):
        out = to_mermaid(_node("X", group="My Group"))
        # safe id + quoted title, never a bare `subgraph My Group`
        assert 'subgraph sg0["My Group"]' in out
        assert "subgraph My Group" not in out


class TestDotEscaping:
    def test_backslash_quote_and_newline_are_escaped(self):
        out = to_dot(_node('C:\\path "q"\nline2'))
        line = next(line for line in out.splitlines() if line.strip().startswith('"n"'))
        assert '\\\\' in line          # backslash doubled
        assert '\\"' in line           # quote escaped
        assert '\\n' in line           # newline → \n literal
        assert "\n" not in line[line.index("label"):]  # no raw newline in the value

    def test_special_id_is_escaped_consistently(self):
        rs = Ruleset(id="t", name="test", nodes={
            'we"ird': ComputationNode(id='we"ird', node_type=NodeType.INPUT, label="X"),
        })
        out = to_dot(rs)
        assert '"we\\"ird"' in out      # id quoted with escaped quote
