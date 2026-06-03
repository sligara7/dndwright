"""Graph composition — mini-graphs ("legos") snap onto a ruleset and cascade."""

from dndwright import (
    DND_5E_2024_RULESET,
    Component,
    Contribution,
    ComputationNode,
    FormulaSpec,
    NodeType,
    Ruleset,
    compose,
    evaluate,
    modifier,
    validate_ruleset,
)
from dndwright import character_data_to_inputs

R = DND_5E_2024_RULESET


def _inputs(strength=14, level=5):
    return character_data_to_inputs(
        ability_scores={"strength": strength, "dexterity": 12, "constitution": 14,
                        "intelligence": 10, "wisdom": 11, "charisma": 8},
        class_data={"class_name": "fighter"}, subclass_data=None,
        species_data={"name": "Human", "speed": 30}, background_data=None, level=level,
    )


class TestComposeOnRealRuleset:
    def test_set_modifier_cascades_downstream(self):
        # Gauntlets of Ogre Power: STR becomes 19 → modifier/saves/skills all recompute.
        gauntlets = modifier("gauntlets", target="strength_score", amount=19, mode="set")
        composed = compose(R, gauntlets)
        assert validate_ruleset(composed) == []
        base = evaluate(R, _inputs(strength=14))
        on = evaluate(composed, _inputs(strength=14))
        assert (base["strength_score"], on["strength_score"]) == (14, 19)
        assert (base["strength_mod"], on["strength_mod"]) == (2, 4)
        assert on["save.strength.bonus"] == base["save.strength.bonus"] + 2
        assert on["skill.athletics.bonus"] == base["skill.athletics.bonus"] + 2

    def test_set_takes_higher_only(self):
        # already STR 20 → gauntlets (set 19) don't lower it (max semantics)
        on = evaluate(compose(R, modifier("g", target="strength_score", amount=19, mode="set")),
                      _inputs(strength=20))
        assert on["strength_score"] == 20

    def test_base_untouched_after_compose(self):
        before = set(R.nodes)
        compose(R, modifier("g", target="strength_score", amount=2))
        assert set(R.nodes) == before  # pure — original ruleset unchanged

    def test_compose_is_idempotent_detach_by_recompose(self):
        # "detaching" = just don't include the component → identical to base
        on = evaluate(compose(R, modifier("g", target="strength_score", amount=4)), _inputs())
        off = evaluate(R, _inputs())
        assert on["strength_mod"] == off["strength_mod"] + 2  # +4 STR → +2 mod
        assert evaluate(compose(R), _inputs())["strength_mod"] == off["strength_mod"]  # no comps


class TestStackingAndModes:
    def _mini(self):
        # a tiny base graph: score (input) feeds mod = (score-10)//2
        nodes = {
            "score": ComputationNode(id="score", node_type=NodeType.INPUT, label="Score"),
            "mod": ComputationNode(id="mod", node_type=NodeType.FORMULA, label="Mod",
                                   formula=FormulaSpec(op="ability_mod", args=["score"])),
        }
        return Ruleset(id="t", name="t", nodes=nodes)

    def test_multiple_add_modifiers_stack(self):
        rs = self._mini()
        composed = compose(rs,
            modifier("belt", target="score", amount=2),
            modifier("tome", target="score", amount=1))
        assert validate_ruleset(composed) == []
        out = evaluate(composed, {"score": 10})
        assert out["score"] == 13 and out["mod"] == 1  # 10 + 2 + 1

    def test_add_order_independent(self):
        rs = self._mini()
        a = compose(rs, modifier("x", target="score", amount=2), modifier("y", target="score", amount=3))
        b = compose(rs, modifier("y", target="score", amount=3), modifier("x", target="score", amount=2))
        assert evaluate(a, {"score": 10})["score"] == evaluate(b, {"score": 10})["score"] == 15

    def test_add_and_set_combine(self):
        # base 10, +2 add, set 19 → max(10+2, 19) = 19
        rs = self._mini()
        composed = compose(rs,
            modifier("belt", target="score", amount=2, mode="add"),
            modifier("gauntlets", target="score", amount=19, mode="set"))
        assert evaluate(composed, {"score": 10})["score"] == 19
        # but if the add pushes above the set, the sum wins
        assert evaluate(composed, {"score": 18})["score"] == 20  # 18+2 > 19

    def test_union_mode_builds_a_set_channel(self):
        # attach resistances to a target that doesn't exist yet → created from contributions
        rs = self._mini()
        composed = compose(rs,
            modifier("cloak", target="resistances", amount=["fire"], mode="union"),
            modifier("ring", target="resistances", amount=["cold", "fire"], mode="union"))
        assert validate_ruleset(composed) == []
        out = evaluate(composed, {"score": 10})
        assert out["resistances"] == ("cold", "fire")  # union, sorted, de-duped


class TestComponentSurface:
    def test_component_is_json_serialisable(self):
        # a component is data (so items/feats can ship as content)
        comp = modifier("gauntlets", target="strength_score", amount=19, mode="set")
        dumped = comp.model_dump()
        assert dumped["id"] == "gauntlets"
        assert dumped["contributions"][0] == {"target": "strength_score", "source": "value",
                                              "mode": "set"}
        # round-trips
        assert Component.model_validate(dumped).contributions[0].target == "strength_score"

    def test_unknown_mode_raises(self):
        import pytest
        bad = Component(id="b", contributions=[Contribution(target="x", source="v", mode="bogus")],
                        nodes={"v": ComputationNode(id="v", node_type=NodeType.INPUT, label="v")})
        with pytest.raises(ValueError, match="unknown contribution mode"):
            compose(Ruleset(id="t", name="t", nodes={}), bad)

    def test_cycle_introduced_is_caught_by_validation(self):
        # a contribution whose source depends on the target → cycle; validate_ruleset flags it
        rs = Ruleset(id="t", name="t", nodes={
            "a": ComputationNode(id="a", node_type=NodeType.INPUT, label="A"),
        })
        comp = Component(id="c", nodes={
            "v": ComputationNode(id="v", node_type=NodeType.FORMULA, label="v",
                                 formula=FormulaSpec(op="add", args=["a", 1])),  # depends on target 'a'
        }, contributions=[Contribution(target="a", source="v", mode="add")])
        composed = compose(rs, comp)
        assert any(i.code == "cycle" for i in validate_ruleset(composed))
