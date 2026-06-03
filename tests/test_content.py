"""Tests for bundled starter content + the LLM-agnostic generator."""

import pytest

from dndwright import categories, generate_library, load_content
from dndwright.content import generate_classes, generate_creatures


class TestBundledContent:
    def test_categories(self):
        assert set(categories()) == {
            "classes", "species", "creatures", "magic_items", "conditions", "feats"
        }

    @pytest.mark.parametrize("category,min_count", [
        ("classes", 6), ("species", 6), ("creatures", 12), ("magic_items", 100),
        ("conditions", 15), ("feats", 16),
    ])
    def test_load_content(self, category, min_count):
        items = load_content(category)
        assert isinstance(items, list)
        assert len(items) >= min_count
        assert all(isinstance(i, dict) and "name" in i for i in items)

    def test_conditions_have_mechanics(self):
        for c in load_content("conditions"):
            assert "display_name" in c and "description" in c
            assert "mechanics" in c and isinstance(c["mechanics"], dict)

    def test_creatures_have_stats(self):
        for c in load_content("creatures"):
            for f in ("cr", "hp", "ac", "size", "creature_type"):
                assert f in c

    def test_unknown_category_raises(self):
        with pytest.raises(ValueError):
            load_content("dragons")


# -- a fake LLM: returns canned content based on which array the prompt asks for --

class FakeLLM:
    def __init__(self):
        self.calls = 0

    def __call__(self, prompt, system=None):
        self.calls += 1
        assert system  # generator always passes a system prompt
        if '"classes"' in prompt:
            return {"classes": [{"name": "Aetherbinder"}, {"name": "Glasswright"}, "junk-not-a-dict"]}
        if '"species"' in prompt:
            return {"species": [{"name": "Cindral"}]}
        if '"creatures"' in prompt:
            return {"creatures": [{"name": f"Beast{self.calls}"}]}
        return {}


class TestGenerator:
    def test_generate_classes_filters_non_dicts(self):
        out = generate_classes(FakeLLM(), n=3)
        assert [c["name"] for c in out] == ["Aetherbinder", "Glasswright"]  # "junk" dropped

    def test_generate_creatures_batches(self):
        llm = FakeLLM()
        out = generate_creatures(llm, n=12)  # batches of 6 -> 2 calls
        assert llm.calls == 2
        assert len(out) == 2  # one per batch from the fake

    def test_generate_library_shape(self):
        lib = generate_library(FakeLLM(), classes=2, species=2, creatures=6)
        assert set(lib) == {"classes", "species", "creatures"}
        assert lib["classes"] and lib["species"] and lib["creatures"]

    def test_generator_is_llm_agnostic(self):
        # No network / SDK import needed — just a callable.
        calls = []
        lib = generate_library(lambda p, s=None: (calls.append(1), {"classes": [{"name": "X"}]})[1],
                               classes=1, species=1, creatures=1)
        assert lib["classes"] == [{"name": "X"}]
        assert calls  # our plain lambda was invoked
