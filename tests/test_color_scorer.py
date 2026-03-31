"""
tests/test_color_scorer.py
Tests for the Itten Color Theory harmony scorer.
Run: pytest tests/test_color_scorer.py -v
"""

import pytest
from tests.conftest import _make_item
from engine.models import Category


class TestColorScorer:

    def test_complementary_hues_score_highest(self):
        """Hues ~180° apart should score close to 1.0 (complementary harmony)."""
        from engine.color_scorer import score_outfit_color
        red_top    = _make_item(1, Category.TOP,    dominant_hue=0.0,   dominant_sat=0.9)
        cyan_btm   = _make_item(2, Category.BOTTOM, dominant_hue=180.0, dominant_sat=0.9)
        result = score_outfit_color([red_top, cyan_btm])
        assert result >= 0.90, f"Complementary colors should score >= 0.90, got {result}"

    def test_analogous_hues_score_well(self):
        """Hues ~30° apart are analogous — should score >= 0.75."""
        from engine.color_scorer import score_outfit_color
        item_a = _make_item(1, Category.TOP,    dominant_hue=0.0,  dominant_sat=0.8)
        item_b = _make_item(2, Category.BOTTOM, dominant_hue=28.0, dominant_sat=0.8)
        result = score_outfit_color([item_a, item_b])
        assert result >= 0.75

    def test_monochromatic_hues_score_well(self):
        """Very similar hues (< 25° apart) are monochromatic."""
        from engine.color_scorer import score_outfit_color
        item_a = _make_item(1, Category.TOP,    dominant_hue=120.0, dominant_sat=0.9)
        item_b = _make_item(2, Category.BOTTOM, dominant_hue=130.0, dominant_sat=0.5)
        result = score_outfit_color([item_a, item_b])
        assert result >= 0.80

    def test_neutral_item_does_not_lower_score(self):
        """Neutral item (sat < 0.15) should not be scored against colored items."""
        from engine.color_scorer import score_outfit_color
        colored = _make_item(1, Category.TOP,   dominant_hue=0.0,  dominant_sat=0.9)
        neutral = _make_item(2, Category.SHOES, dominant_hue=0.0,  dominant_sat=0.05)
        # With neutral excluded, only 1 non-neutral → score should be safe (0.80)
        result = score_outfit_color([colored, neutral])
        assert result >= 0.75

    def test_all_neutral_outfit_returns_fixed_score(self):
        """All-neutral outfit (black + white + grey) should return 0.85."""
        from engine.color_scorer import score_outfit_color
        items = [
            _make_item(i, cat, dominant_sat=0.05)
            for i, cat in enumerate([Category.TOP, Category.BOTTOM, Category.SHOES])
        ]
        result = score_outfit_color(items)
        assert abs(result - 0.85) < 0.01

    def test_clashing_hues_score_low(self):
        """Hues with no recognized Itten harmony should score <= 0.50."""
        from engine.color_scorer import score_outfit_color
        # 0° and 90° — not complementary (180°), not analogous (30°), not triadic (120°)
        item_a = _make_item(1, Category.TOP,    dominant_hue=0.0,  dominant_sat=0.9)
        item_b = _make_item(2, Category.BOTTOM, dominant_hue=90.0, dominant_sat=0.9)
        result = score_outfit_color([item_a, item_b])
        assert result <= 0.55, f"Clashing colors should score <= 0.55, got {result}"
