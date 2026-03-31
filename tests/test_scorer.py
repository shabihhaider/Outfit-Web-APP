"""
tests/test_scorer.py
Tests for Gate 3 weighted scorer — especially symmetric Model 2 scoring.
Run: pytest tests/test_scorer.py -v

Note: These tests use a mock Model 2 that returns a fixed score,
so they test the scoring logic without requiring the real .h5 file.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock

from tests.conftest import _make_item
from engine.models import Category, OutfitTemplate


def _mock_model2(fixed_score: float = 0.75) -> MagicMock:
    """Return a mock Keras model that always predicts fixed_score."""
    model = MagicMock()
    model.predict.return_value = np.array([[fixed_score]])
    return model


class TestSymmetricScoring:

    def test_pair_score_is_symmetric(self, top_item, bottom_item):
        """score(A, B) must equal score(B, A) after symmetric averaging."""
        from engine.scorer import _score_pair_symmetric

        # Use an asymmetric mock: returns 0.8 for first call, 0.6 for second
        model = MagicMock()
        model.predict.side_effect = [
            np.array([[0.8]]),  # score(A, B)
            np.array([[0.6]]),  # score(B, A)
        ]

        score_ab = _score_pair_symmetric(top_item, bottom_item, model)

        model.predict.side_effect = [
            np.array([[0.6]]),  # score(B, A) — reversed order
            np.array([[0.8]]),  # score(A, B)
        ]
        score_ba = _score_pair_symmetric(bottom_item, top_item, model)

        assert abs(score_ab - score_ba) < 1e-6, \
            f"Asymmetric result: {score_ab} vs {score_ba}"

    def test_pair_score_averages_both_directions(self, top_item, bottom_item):
        """Verify the average is (0.8 + 0.6) / 2 = 0.70."""
        from engine.scorer import _score_pair_symmetric
        model = MagicMock()
        model.predict.side_effect = [
            np.array([[0.8]]),
            np.array([[0.6]]),
        ]
        score = _score_pair_symmetric(top_item, bottom_item, model)
        assert abs(score - 0.70) < 1e-6

    def test_predict_called_twice_per_pair(self, top_item, bottom_item):
        """Symmetric scoring must call model.predict exactly twice."""
        from engine.scorer import _score_pair_symmetric
        model = _mock_model2(0.75)
        _score_pair_symmetric(top_item, bottom_item, model)
        assert model.predict.call_count == 2


class TestWeightedScoring:

    def test_final_score_uses_correct_weights(
        self, top_item, bottom_item, shoes_item
    ):
        """final = model2×0.45 + color×0.25 + weather×0.15 + cohesion×0.15."""
        from engine.scorer import score_outfit
        from unittest.mock import patch

        model = _mock_model2(0.80)  # model2_score will be 0.80

        with patch("engine.scorer.score_outfit_color", return_value=0.60), \
             patch("engine.scorer.score_outfit_weather", return_value=0.50), \
             patch("engine.scorer.score_outfit_cohesion", return_value=0.70):
            result = score_outfit(
                outfit=[top_item, bottom_item, shoes_item],
                model2=model,
                temp_celsius=25.0,
            )

        expected = 0.80 * 0.45 + 0.60 * 0.25 + 0.50 * 0.15 + 0.70 * 0.15
        assert abs(result.final_score - expected) < 1e-4

    def test_high_confidence_assigned_correctly(
        self, top_item, bottom_item, shoes_item
    ):
        from engine.scorer import score_outfit
        from engine.models import Confidence
        from unittest.mock import patch

        model = _mock_model2(0.90)
        with patch("engine.scorer.score_outfit_color", return_value=0.90), \
             patch("engine.scorer.score_outfit_weather", return_value=0.90):
            result = score_outfit([top_item, bottom_item, shoes_item], model, 25.0)

        assert result.confidence == Confidence.HIGH

    def test_low_confidence_assigned_when_scores_poor(
        self, top_item, bottom_item, shoes_item
    ):
        from engine.scorer import score_outfit
        from engine.models import Confidence
        from unittest.mock import patch

        model = _mock_model2(0.20)
        with patch("engine.scorer.score_outfit_color", return_value=0.20), \
             patch("engine.scorer.score_outfit_weather", return_value=0.20):
            result = score_outfit([top_item, bottom_item, shoes_item], model, 25.0)

        assert result.confidence == Confidence.LOW
