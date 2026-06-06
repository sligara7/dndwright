"""Theme scaling — fold a ThemeScalingLayer's mechanical overrides onto a ruleset.

``apply_theme_scaling`` re-baselines input ``default_value``s and deep-merges lookup
tables, so the same computation graph yields setting-appropriate values. It is pure
(the base ruleset is untouched) and composes with ``compose``.
"""

import pytest

from dndwright import (
    DND_5E_2024_RULESET,
    ThemeScalingLayer,
    apply_theme_scaling,
    character_data_to_inputs,
    compose,
    evaluate,
    get_theme_scaling,
    modifier,
)

R = DND_5E_2024_RULESET


def _inputs(strength=14, level=5):
    return character_data_to_inputs(
        ability_scores={"strength": strength, "dexterity": 12, "constitution": 14,
                        "intelligence": 10, "wisdom": 11, "charisma": 8},
        class_data={"class_name": "fighter"}, subclass_data=None,
        species_data={"name": "Human", "speed": 30}, background_data=None, level=level,
    )


class TestLookupOverrides:
    def test_merge_changes_downstream_value(self):
        # Bump plate's base AC; the armor_class node reads armor_base_ac via the lookup op,
        # so the same inputs yield an AC higher by exactly the override delta.
        base_plate = R.lookup_tables["armor_base_ac"]["plate"]
        layer = ThemeScalingLayer(
            theme="t", lookup_overrides={"armor_base_ac": {"plate": base_plate + 4}}
        )
        scaled = apply_theme_scaling(R, layer)
        ins = {**_inputs(), "armor_type": "plate"}
        assert evaluate(scaled, ins)["armor_class"] == evaluate(R, ins)["armor_class"] + 4

    def test_unnamed_keys_are_preserved(self):
        # Overriding one key must not drop the rest of the table.
        layer = ThemeScalingLayer(theme="t", lookup_overrides={"armor_base_ac": {"plate": 22}})
        merged = apply_theme_scaling(R, layer).lookup_tables["armor_base_ac"]
        assert merged["plate"] == 22
        assert merged["leather"] == R.lookup_tables["armor_base_ac"]["leather"]

    def test_creates_a_brand_new_table(self):
        layer = ThemeScalingLayer(theme="t", lookup_overrides={"jetpack_speed": {"mk1": 120}})
        assert apply_theme_scaling(R, layer).lookup_tables["jetpack_speed"] == {"mk1": 120}
        assert "jetpack_speed" not in R.lookup_tables  # base untouched


class TestInputOverrides:
    def test_rebaselines_default_used_when_no_input(self):
        layer = ThemeScalingLayer(theme="t", input_overrides={"speed_base": 60})
        scaled = apply_theme_scaling(R, layer)
        assert evaluate(scaled, {})["speed_base"] == 60
        assert evaluate(R, {})["speed_base"] == 30  # base default untouched

    def test_explicit_input_still_wins_over_theme_default(self):
        layer = ThemeScalingLayer(theme="t", input_overrides={"speed_base": 60})
        scaled = apply_theme_scaling(R, layer)
        assert evaluate(scaled, {"speed_base": 25})["speed_base"] == 25

    def test_unknown_node_raises(self):
        layer = ThemeScalingLayer(theme="t", input_overrides={"no_such_node": 1})
        with pytest.raises(KeyError):
            apply_theme_scaling(R, layer)


class TestPurityAndComposition:
    def test_base_ruleset_is_not_mutated(self):
        before = R.model_dump()
        apply_theme_scaling(
            R,
            ThemeScalingLayer(
                theme="t",
                input_overrides={"speed_base": 99},
                lookup_overrides={"armor_base_ac": {"plate": 99}},
            ),
        )
        assert R.model_dump() == before

    def test_composes_with_components(self):
        # Theme-scale, then snap a character component on top — both return a Ruleset.
        scaled = apply_theme_scaling(
            R, ThemeScalingLayer(theme="t", input_overrides={"speed_base": 40})
        )
        composed = compose(scaled, modifier("g", target="strength_score", amount=19, mode="set"))
        out = evaluate(composed, _inputs(strength=10))
        assert out["strength_score"] == 19  # component still applies
        # speed_base re-baseline survives composition when no explicit speed given
        assert evaluate(composed, {})["speed_base"] == 40


class TestPredefinedLayers:
    def test_modern_warfare_applies_and_merges_ranges(self):
        layer = get_theme_scaling("modern_warfare")
        scaled = apply_theme_scaling(R, layer)
        assert scaled.lookup_tables["weapon_ranges"]["longbow"] == 600

    def test_every_predefined_layer_applies_cleanly(self):
        from dndwright import PREDEFINED_THEME_SCALING

        for layer in PREDEFINED_THEME_SCALING.values():
            scaled = apply_theme_scaling(R, layer)
            assert evaluate(scaled, _inputs())["armor_class"] is not None
