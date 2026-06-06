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
  * ``add``      — summed in (numeric bonuses).
  * ``set``      — ``max`` with the base/sum (5e "your score becomes X" takes the highest).
  * ``union``    — set union (e.g. damage-resistance types contributed by several sources).
  * ``override`` — *replaces* the base value (last wins), then add/set/union stack on top — for
    an authoritative value that must hold even below the input default (a creature stat block's
    "STR is 8", not "STR becomes at least 8").

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

_MODES = ("add", "set", "union", "override")

#: Bumped on any breaking change to the serialised :class:`Component` shape. Stamped into
#: :func:`component_to_dict` output so a persisted spec can be migrated on load.
COMPONENT_SCHEMA_VERSION = 1
_SCHEMA_VERSION_KEY = "_schema_version"


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
    overrides = [s for s, m in contribs if m == "override"]
    base = [base_id] if base_id is not None else []
    label = proto.label if proto is not None else target
    group = proto.group if proto is not None else ""
    layer = proto.layer if proto is not None else 0
    out: dict[str, ComputationNode] = {}

    if overrides:
        # An authoritative value *replaces* the original base (last override wins, via
        # coalesce on the reversed list) — e.g. a creature stat block's "STR is 8", which
        # must hold even below the input default. add/set/union then stack on top of it.
        if len(overrides) == 1:
            base = [overrides[0]]
        else:
            ov_id = f"{target}.__override__"
            out[ov_id] = ComputationNode(
                id=ov_id, node_type=NodeType.AGGREGATE, label=f"{label} (override)",
                group=group, layer=layer,
                formula=FormulaSpec(op="coalesce", args=list(reversed(overrides))),
            )
            base = [ov_id]

    if unions:
        if adds or sets:
            # union is for set-valued channels (resistances, languages); add/set are
            # numeric. Mixing them on one target is a modelling error — fail loudly
            # rather than silently dropping the add/set contributions.
            raise ValueError(
                f"target {target!r} mixes union with add/set contributions; "
                "a target must be either set-valued or numeric, not both"
            )
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


def component_from_content(
    item: dict[str, Any], *, choices: dict[str, str] | None = None
) -> Component | None:
    """Build a :class:`Component` from a content entry's ``component`` field, or ``None``.

    Bundled content carries an item/feat's mechanical effect *as data*: a ``component`` list
    of modifiers, each a dict with a ``target`` host node, a ``mode`` (``add``/``set``/
    ``union``), and a value given as either:

    * ``"amount"`` — a constant (e.g. Gauntlets of Ogre Power → ``strength_score`` set 19), or
    * ``"formula"`` — ``{"op", "args"}`` whose args may reference *host* nodes, for effects
      that scale (e.g. Alert → ``initiative`` += ``proficiency_bonus``).

    A modifier may also carry a ``"condition"`` — a ``{"op", "args"}`` over host nodes that
    evaluates to a bool — to make the contribution *gated*: it applies only while the
    condition holds, contributing the off-identity (``0``, or ``()`` for union) otherwise.
    So the Defense fighting style (+1 AC *while wearing armor*) is
    ``{"target": "armor_class", "amount": 1, "condition": {"op": "ne", "args": ["armor_type", "none"]}}``
    — the bonus tracks the character's armour as it changes, with no re-compose.

    A ``target``, a formula/condition arg, or a member of a list ``amount`` may contain a
    ``{placeholder}`` filled from ``choices`` — so a feat whose benefit is "increase an ability
    score of *your choice*", or a species whose resistance type is chosen (Dragonborn ancestry,
    Tiefling legacy: ``"amount": ["{ancestry}"]``), is a template::

        from dndwright import load_content, component_from_content, compose, evaluate
        feats = {f["name"]: f for f in load_content("feats")}
        asi = component_from_content(feats["Ability Score Improvement"], choices={"ability": "strength"})
        sheet = evaluate(compose(DND_5E_2024_RULESET, asi), inputs)

    Returns ``None`` for entries with no ``component`` (most are narrative). Raises
    ``KeyError`` if a ``{placeholder}`` has no matching entry in ``choices``. Item rarity /
    attunement (or feat category) are carried onto ``Component.metadata``.
    """
    spec = item.get("component")
    if not spec:
        return None
    choices = choices or {}
    name = item.get("name", "item")

    def fill(ref: Any) -> Any:
        if isinstance(ref, str):
            return ref.format(**choices) if "{" in ref else ref
        if isinstance(ref, (list, tuple)):
            # recurse so a {placeholder} inside a union amount (e.g. ["{ancestry}"]) is filled
            return type(ref)(fill(x) for x in ref)
        return ref

    nodes: dict[str, ComputationNode] = {}
    contribs: list[Contribution] = []
    counter = [0]

    def build(expr: Any) -> Any:
        """Compile an expression (literal, host-node ref, or nested ``{op, args}``) into the
        component's sub-graph, returning the arg to reference it (a value or a node id)."""
        if isinstance(expr, dict) and "op" in expr:
            nid = f"n{counter[0]}"
            counter[0] += 1
            nodes[nid] = ComputationNode(
                id=nid, node_type=NodeType.FORMULA, label=name,
                formula=FormulaSpec(op=expr["op"], args=[build(a) for a in expr["args"]]),
            )
            return nid
        return fill(expr)

    for mod in spec:
        mode = mod.get("mode", "add")
        # the value contributed while active: a formula node ref, or a literal amount
        active = build(mod["formula"]) if "formula" in mod else mod["amount"]

        if "condition" in mod:
            # gate: contribute `active` while the condition holds, else the off-identity
            off: Any = [] if mode == "union" else 0
            src = build({"op": "if_then_else",
                         "args": [mod["condition"], active, off]})
        elif "formula" in mod:
            src = active  # the formula node is the source directly
        else:
            src = build({"op": "const", "args": [active]})

        contribs.append(Contribution(target=fill(mod["target"]), source=src, mode=mode))

    cid = _slug(name)
    if choices:  # keep distinct components (e.g. ASI:str vs ASI:dex) from colliding on compose
        cid += "_" + "_".join(_slug(str(v)) for v in choices.values())
    return Component(
        id=cid, name=name, nodes=nodes, contributions=contribs,
        metadata={k: item.get(k) for k in ("rarity", "attunement_required", "category")},
    )


def component_to_dict(component: Component) -> dict[str, Any]:
    """Serialise a :class:`Component` to a plain JSON-able dict for persistence.

    A stable public wrapper over ``Component.model_dump(mode="json")`` that stamps the
    :data:`COMPONENT_SCHEMA_VERSION`, so a component stored as data (e.g. a dynograph node
    property, a JSON column) can be rebuilt later via :func:`component_from_dict` and migrated
    if the shape ever changes. Pairs with :func:`component_from_dict`.
    """
    data = component.model_dump(mode="json")
    data[_SCHEMA_VERSION_KEY] = COMPONENT_SCHEMA_VERSION
    return data


def component_from_dict(data: dict[str, Any]) -> Component:
    """Rebuild a :class:`Component` from :func:`component_to_dict` output (or a raw spec).

    Tolerant of a missing or older ``_schema_version`` (the migration seam — there is only
    version 1 today, so the key is simply stripped before validation).
    """
    if _SCHEMA_VERSION_KEY in data:
        data = {k: v for k, v in data.items() if k != _SCHEMA_VERSION_KEY}
    return Component.model_validate(data)
