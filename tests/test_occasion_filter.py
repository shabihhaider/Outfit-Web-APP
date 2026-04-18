"""
tests/test_occasion_filter.py
Tests for Gate 2 — occasion filter.
Run: pytest tests/test_occasion_filter.py -v
"""

import pytest

from engine.models import Category, Formality, Gender, Occasion
from tests.conftest import _make_item


class TestOccasionFilter:

    def test_casual_occasion_excludes_formal_items(self, casual_item, formal_item, top_item):
        """Casual occasion must not include strictly formal-only items."""
        from engine.occasion_filter import filter_by_occasion
        items = [casual_item, formal_item, top_item]
        result = filter_by_occasion(items, Occasion.CASUAL)
        assert formal_item not in result
        assert casual_item in result
        assert top_item in result  # top_item is Formality.BOTH — stays in

    def test_all_formal_items_casual_occasion_returns_empty(self):
        """Wardrobe of purely formal items yields no casual candidates."""
        from engine.occasion_filter import filter_by_occasion
        items = [
            _make_item(i, Category.TOP, formality=Formality.FORMAL)
            for i in range(3)
        ]
        result = filter_by_occasion(items, Occasion.CASUAL)
        assert result == []

    def test_formal_occasion_removes_casual_items(self, casual_item, formal_item):
        from engine.occasion_filter import filter_by_occasion
        items = [casual_item, formal_item]
        result = filter_by_occasion(items, Occasion.FORMAL)
        assert casual_item not in result
        assert formal_item in result


    def test_both_formality_kept_in_formal(self):
        from engine.occasion_filter import filter_by_occasion
        both_item = _make_item(20, Category.TOP, formality=Formality.BOTH)
        result = filter_by_occasion([both_item], Occasion.FORMAL)
        assert both_item in result

    def test_both_formality_kept_in_casual(self):
        from engine.occasion_filter import filter_by_occasion
        both_item = _make_item(20, Category.TOP, formality=Formality.BOTH)
        result = filter_by_occasion([both_item], Occasion.CASUAL)
        assert both_item in result

    def test_empty_wardrobe_returns_empty(self):
        from engine.occasion_filter import filter_by_occasion
        result = filter_by_occasion([], Occasion.FORMAL)
        assert result == []

    def test_all_casual_items_formal_occasion_returns_empty(self):
        from engine.occasion_filter import filter_by_occasion
        items = [
            _make_item(i, Category.TOP, formality=Formality.CASUAL)
            for i in range(3)
        ]
        result = filter_by_occasion(items, Occasion.FORMAL)
        assert result == []
