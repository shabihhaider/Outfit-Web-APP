"""
tests/test_models.py
Tests for Pydantic model validation in engine/models.py.
Run: pytest tests/test_models.py -v
"""

import pytest
from pydantic import ValidationError

from engine.models import (
    WardrobeItem, OutfitCandidate, RecommendationRequest,
    Category, Formality, Gender, Occasion, Confidence, OutfitTemplate,
    CAT_TO_IDX,
)


class TestWardrobeItemValidation:

    def test_valid_item_creates_successfully(self, top_item):
        assert top_item.category == Category.TOP
        assert len(top_item.embedding) == 1280

    def test_embedding_wrong_length_raises(self):
        with pytest.raises(ValidationError, match="1280"):
            WardrobeItem(
                item_id=1, category=Category.TOP,
                formality=Formality.BOTH, gender=Gender.UNISEX,
                embedding=[0.1] * 512,  # wrong length
                dominant_hue=0.0, dominant_sat=0.5, dominant_val=0.5,
            )

    def test_hue_out_of_range_raises(self):
        from tests.conftest import _make_embedding
        with pytest.raises(ValidationError):
            WardrobeItem(
                item_id=1, category=Category.TOP,
                formality=Formality.BOTH, gender=Gender.UNISEX,
                embedding=_make_embedding(),
                dominant_hue=400.0,  # > 360
                dominant_sat=0.5, dominant_val=0.5,
            )

    def test_saturation_out_of_range_raises(self):
        from tests.conftest import _make_embedding
        with pytest.raises(ValidationError):
            WardrobeItem(
                item_id=1, category=Category.TOP,
                formality=Formality.BOTH, gender=Gender.UNISEX,
                embedding=_make_embedding(),
                dominant_hue=0.0,
                dominant_sat=1.5,  # > 1.0
                dominant_val=0.5,
            )

    def test_embedding_array_returns_correct_shape(self, top_item):
        arr = top_item.embedding_array()
        assert arr.shape == (1280,)
        assert arr.dtype.name == "float32"

    def test_category_onehot_correct_index(self, top_item):
        vec = top_item.category_onehot()
        assert vec.shape == (5,)
        assert vec[CAT_TO_IDX[Category.TOP]] == 1.0
        assert vec.sum() == 1.0

    def test_category_onehot_bottom(self, bottom_item):
        vec = bottom_item.category_onehot()
        assert vec[CAT_TO_IDX[Category.BOTTOM]] == 1.0

    def test_invalid_category_raises(self):
        from tests.conftest import _make_embedding
        with pytest.raises(ValidationError):
            WardrobeItem(
                item_id=1, category="socks",  # not a valid Category
                formality=Formality.BOTH, gender=Gender.UNISEX,
                embedding=_make_embedding(),
                dominant_hue=0.0, dominant_sat=0.5, dominant_val=0.5,
            )


class TestCATToIDX:

    def test_all_five_categories_present(self):
        expected = {Category.BOTTOM, Category.DRESS, Category.OUTWEAR,
                    Category.SHOES, Category.TOP}
        assert set(CAT_TO_IDX.keys()) == expected

    def test_indices_are_0_to_4(self):
        assert sorted(CAT_TO_IDX.values()) == [0, 1, 2, 3, 4]

    def test_jumpsuit_not_in_cat_to_idx(self):
        # Jumpsuit is not scored pairwise with model2 directly — it's treated like dress
        assert Category.JUMPSUIT not in CAT_TO_IDX


class TestRecommendationRequest:

    def test_valid_request(self):
        req = RecommendationRequest(
            user_id=1,
            occasion=Occasion.CASUAL,
            temp_celsius=30.0,
            gender_filter=Gender.WOMEN,
        )
        assert req.top_n == 6  # default

    def test_temp_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            RecommendationRequest(
                user_id=1,
                occasion=Occasion.CASUAL,
                temp_celsius=70.0,  # > 60
                gender_filter=Gender.WOMEN,
            )

    def test_top_n_zero_raises(self):
        with pytest.raises(ValidationError):
            RecommendationRequest(
                user_id=1,
                occasion=Occasion.CASUAL,
                temp_celsius=25.0,
                gender_filter=Gender.WOMEN,
                top_n=0,
            )
