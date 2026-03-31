"""
tests/test_weather_scorer.py
Tests for the ASHRAE 55 / ISO 11092 CLO weather scorer.
Run: pytest tests/test_weather_scorer.py -v
"""

import pytest
from tests.conftest import _make_item
from engine.models import Category


class TestWeatherScorer:

    def test_heavy_outfit_scores_high_in_cold(self):
        """top + bottom + outwear (high CLO) should score well at 8°C."""
        from engine.weather_scorer import score_outfit_weather
        items = [
            _make_item(1, Category.TOP),
            _make_item(2, Category.BOTTOM),
            _make_item(3, Category.OUTWEAR),
            _make_item(4, Category.SHOES),
        ]
        score = score_outfit_weather(items, temp_celsius=8.0)
        assert score >= 0.70, f"Heavy outfit should score >= 0.70 at 8°C, got {score}"

    def test_light_outfit_scores_low_in_cold(self):
        """top + bottom (low CLO) should score poorly at 5°C."""
        from engine.weather_scorer import score_outfit_weather
        items = [
            _make_item(1, Category.TOP),
            _make_item(2, Category.BOTTOM),
            _make_item(3, Category.SHOES),
        ]
        score = score_outfit_weather(items, temp_celsius=5.0)
        assert score <= 0.60, f"Light outfit should score <= 0.60 at 5°C, got {score}"

    def test_light_outfit_scores_high_in_heat(self):
        """top + bottom (low CLO) should score well at Lahore summer temperature (42°C)."""
        from engine.weather_scorer import score_outfit_weather
        items = [
            _make_item(1, Category.TOP),
            _make_item(2, Category.BOTTOM),
            _make_item(3, Category.SHOES),
        ]
        score = score_outfit_weather(items, temp_celsius=42.0)
        assert score >= 0.70, f"Light outfit should score >= 0.70 at 42°C, got {score}"

    def test_heavy_outfit_scores_low_in_heat(self):
        """top + bottom + outwear should score poorly at 42°C."""
        from engine.weather_scorer import score_outfit_weather
        items = [
            _make_item(1, Category.TOP),
            _make_item(2, Category.BOTTOM),
            _make_item(3, Category.OUTWEAR),
            _make_item(4, Category.SHOES),
        ]
        score = score_outfit_weather(items, temp_celsius=42.0)
        assert score <= 0.50, f"Heavy outfit should score <= 0.50 at 42°C, got {score}"

    def test_perfect_fit_returns_1_0(self):
        """An outfit whose total CLO is exactly inside the comfort zone returns 1.0."""
        from engine.weather_scorer import score_outfit_weather, CLO_VALUES, get_target_clo_range
        # At 25°C, target range is 0.45–0.80
        # top (0.25) + bottom (0.24) + shoes (0.03) = 0.52 → inside range
        items = [
            _make_item(1, Category.TOP),
            _make_item(2, Category.BOTTOM),
            _make_item(3, Category.SHOES),
        ]
        total_clo = sum(CLO_VALUES[item.category] for item in items)
        clo_min, clo_max = get_target_clo_range(25.0)
        assert clo_min <= total_clo <= clo_max, \
            f"Test assumption wrong: {total_clo} not in [{clo_min}, {clo_max}]"

        score = score_outfit_weather(items, temp_celsius=25.0)
        assert score == 1.0

    def test_score_is_between_0_and_1(self):
        """Score must always be in [0, 1] for any temperature."""
        from engine.weather_scorer import score_outfit_weather
        items = [_make_item(1, Category.DRESS), _make_item(2, Category.SHOES)]
        for temp in [-10, 0, 15, 25, 35, 45]:
            score = score_outfit_weather(items, temp_celsius=float(temp))
            assert 0.0 <= score <= 1.0, f"Score out of range at {temp}°C: {score}"
