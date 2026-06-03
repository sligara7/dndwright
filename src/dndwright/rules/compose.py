"""Graph composition — snap mini-graphs ("legos") onto a base computation graph.

A :class:`Component` is a small graph fragment (a magic item, feat, species trait, …)
plus declarations of how its outputs attach to a host :class:`Ruleset`. :func:`compose`
merges them into a new, larger ``Ruleset`` that evaluates normally — so attaching a
Gauntlets of Ogre Power that sets Strength to 19 makes every downstream value (modifier,
saves, skills, carrying capacity, …) recompute automatically.

The attach trick: a contribution's ``target`` node **keeps its id** and becomes an
AGGREGATE that combines the original (moved to ``{target}.__base__``) with the
contributions. Because the id is unchanged, every existing downstream edge is preserved —
no re-wiring — and the evaluator's normal topological recompute cascades the change.

    from dndwright import compose, modifier, DND_5E_2024_RULESET, evaluate
    gauntlets = modifier("gauntlets_of_ogre_power", target="strength_score", amount=19, mode="set")
    sheet = evaluate(compose(DND_5E_2024_RULESET, gauntlets), character_inputs)

Modes (how a contribution combines with the target's base + siblings):
  * ``add``   — summed in (numeric bonuses).
  * ``set``   — ``max`` with the base/sum (5e "your score becomes X" takes the highest).
  * ``union`` — set union (e.g. damage-resistance types contributed by several sources).

Composition is pure (the base is untouched) and order-independent for add/union/set, so
components stack like legos. Run :func:`dndwright.validate_ruleset` on the result to catch
a cycle a malformed component might introduce (e.g. a contribution that depends on its own
target).
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from .schema import ComputationNode, FormulaSpec, NodeType, Ruleset

_MODES = ("add", "set", "union")


class Contribution(BaseModel):
    """One attachment: a node inside a component feeds a node in the host graph.

    ``target`` is the host node id (the "socket"); ``source`` is the component-local node
    id whose value contributes (the "stud"); ``mode`` is how it combines (see module doc).
    """

    target: str
    source: str
    mode: str = "add"


class Component(BaseModel):
    """A mini-graph that snaps onto a host :class:`Ruleset`.

    JSON-serialisable, so an item/feat/trait's mechanical effect can live as data (e.g. a
    ``magic_items.json`` entry carrying a ``component``). ``nodes`` is the component's own
    sub-graph keyed by component-local ids (namespaced as ``{id}.{local}`` on compose);
    ``contributions`` declare how its outputs attach.
    """

    id: str
    name: str = ""
    nodes: dict[str, ComputationNode] = Field(default_factory=dict)
    contributions: list[Contribution] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def _renamespace(node: ComputationNode, new_id: str, prefix: str, local: set[str]) -> ComputationNode:
    """Copy ``node`` under ``new_id``, rewriting refs to other component-local nodes."""

    def fix(ref: Any) -> Any:
        return prefix + ref if isinstance(ref, str) and ref in local else ref

    formula = node.formula
    if formula is not None:
        formula = formula.model_copy(update={"args": [fix(a) for a in formula.args]})
    return node.model_copy(
        update={"id": new_id, "formula": formula, "inputs": [fix(i) for i in node.inputs]}
    )


def _aggregate_nodes(
    target: str, base_id: str | None, contribs: list[tuple[str, str]], proto: ComputationNode | None
) -> dict[str, ComputationNode]:
    """Build the aggregate node (id == target) + any intermediate, from contributions."""
    adds = [s for s, m in contribs if m == "add"]
    sets = [s for s, m in contribs if m == "set"]
    unions = [s for s, m in contribs if m == "union"]
    base = [base_id] if base_id is not None else []
    label = proto.label if proto is not None else target
    group = proto.group if proto is not None else ""
    layer = proto.layer if proto is not None else 0
    out: dict[str, ComputationNode] = {}

    if unions:
        formula = FormulaSpec(op="union", args=base + unions)
    elif adds and sets:
        sum_id = f"{target}.__sum__"
        out[sum_id] = ComputationNode(
            id=sum_id, node_type=NodeType.AGGREGATE, label=f"{label} (sum)", group=group,
            layer=layer, formula=FormulaSpec(op="add", args=base + adds),
        )
        formula = FormulaSpec(op="max_val", args=[sum_id] + sets)
    elif sets:
        formula = FormulaSpec(op="max_val", args=base + sets)
    else:  # adds only
        formula = FormulaSpec(op="add", args=base + adds)

    out[target] = ComputationNode(
        id=target, node_type=NodeType.AGGREGATE, label=label, group=group, layer=layer,
        formula=formula,
    )
    return out


def compose(base: Ruleset, *components: Component) -> Ruleset:
    """Attach ``components`` to ``base``, returning a new, larger :class:`Ruleset`.

    Pure: ``base`` is not modified. Component nodes are namespaced ``{component.id}.{node}``;
    each contribution turns its target into an AGGREGATE of the original value (moved to
    ``{target}.__base__``) plus the contributions, keeping the target id so downstream edges
    cascade. A contribution to a target that doesn't exist creates it from the contributions
    alone. ``evaluate()`` runs on the result unchanged.
    """
    nodes: dict[str, ComputationNode] = dict(base.nodes)
    by_target: dict[str, list[tuple[str, str]]] = {}

    for comp in components:
        prefix = f"{comp.id}."
        local = set(comp.nodes)
        for lid, node in comp.nodes.items():
            nid = prefix + lid
            nodes[nid] = _renamespace(node, nid, prefix, local)
        for c in comp.contributions:
            if c.mode not in _MODES:
                raise ValueError(f"unknown contribution mode {c.mode!r}; choose from {_MODES}")
            by_target.setdefault(c.target, []).append((prefix + c.source, c.mode))

    for target, contribs in by_target.items():
        proto = nodes.get(target)
        base_id: str | None = None
        if proto is not None:
            base_id = f"{target}.__base__"
            update: dict[str, Any] = {"id": base_id}
            if proto.node_type == NodeType.INPUT:
                # keep binding the original input value despite the rename
                update["input_key"] = proto.input_key if proto.input_key is not None else target
            nodes[base_id] = proto.model_copy(update=update)
            del nodes[target]
        nodes.update(_aggregate_nodes(target, base_id, contribs, proto))

    return base.model_copy(update={"nodes": nodes})


def modifier(
    id: str,
    *,
    target: str,
    amount: Any,
    mode: str = "add",
    name: str = "",
    description: str = "",
) -> Component:
    """Build a one-node component contributing a constant ``amount`` to ``target``.

    ``modifier("gauntlets", target="strength_score", amount=19, mode="set")`` — sets STR to
    19. For ``mode="union"`` pass ``amount`` as a list/tuple of members (e.g. damage types).
    """
    src = ComputationNode(
        id="value", node_type=NodeType.FORMULA, label=name or id,
        formula=FormulaSpec(op="const", args=[amount]), description=description,
    )
    return Component(
        id=id, name=name or id, nodes={"value": src},
        contributions=[Contribution(target=target, source="value", mode=mode)],
    )


def _slug(name: str) -> str:
    """A safe component id (no dots — those namespace component-local node ids)."""
    return re.sub(r"\W+", "_", name.strip().lower()).strip("_") or "item"


def component_from_content(item: dict[str, Any]) -> Component | None:
    """Build a :class:`Component` from a content entry's ``component`` field, or ``None``.

    Bundled content (e.g. ``magic_items.json``) carries an item's mechanical effect *as
    data*: a ``component`` list of ``{"target", "amount", "mode"}`` modifiers. This expands
    each into a constant source node and a :class:`Contribution`, so the item can snap onto a
    character graph::

        from dndwright import load_content, component_from_content, compose, evaluate
        items = {i["name"]: i for i in load_content("magic_items")}
        gauntlets = component_from_content(items["Gauntlets of Ogre Power"])
        sheet = evaluate(compose(DND_5E_2024_RULESET, gauntlets), inputs)

    Returns ``None`` for items with no ``component`` (most are narrative). The item's
    ``rarity``/``attunement_required`` are carried onto ``Component.metadata``.
    """
    spec = item.get("component")
    if not spec:
        return None
    name = item.get("name", "item")
    nodes: dict[str, ComputationNode] = {}
    contribs: list[Contribution] = []
    for i, mod in enumerate(spec):
        src = f"v{i}"
        nodes[src] = ComputationNode(
            id=src, node_type=NodeType.FORMULA, label=name,
            formula=FormulaSpec(op="const", args=[mod["amount"]]),
        )
        contribs.append(
            Contribution(target=mod["target"], source=src, mode=mod.get("mode", "add"))
        )
    return Component(
        id=_slug(name), name=name, nodes=nodes, contributions=contribs,
        metadata={
            "rarity": item.get("rarity"),
            "attunement_required": item.get("attunement_required"),
            "source": "srd_magic_item",
        },
    )
