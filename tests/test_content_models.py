"""Every bundled content asset must validate against its canonical model.

This is the dndwright-side conformance gate: it proves the exported content
models (the structure contract downstream services conform to) exactly match the
shipped SRD assets. A new field in an asset, or a model that drifts from the
assets, fails here.
"""

import pytest

import dndwright
from dndwright.content.models import CONTENT_MODELS


@pytest.mark.parametrize("category", sorted(CONTENT_MODELS))
def test_every_asset_validates_against_its_model(category):
    model = CONTENT_MODELS[category]
    items = dndwright.load_content(category)
    assert items, f"no bundled content for {category!r}"
    for item in items:
        # Raises pydantic.ValidationError (failing the test) on any drift.
        model.model_validate(item)


def test_content_models_cover_every_category():
    # The model map must cover exactly the bundled categories — no gaps, no extras.
    assert set(CONTENT_MODELS) == set(dndwright.categories())


def test_models_are_strict():
    # extra="forbid" is what makes this a contract: an undeclared field must fail.
    with pytest.raises(Exception):
        dndwright.Creature.model_validate(
            {**dndwright.load_content("creatures")[0], "totally_unknown_field": 1}
        )
