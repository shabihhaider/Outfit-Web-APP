"""
tests/test_occasion_filter.py
Tests for Gate 2 — occasion filter.
Run: pytest tests/test_occasion_filter.py -v
"""

import pytest

from engine.models import Category, Formality, Gender, Occasion
from tests.conftest import _make_item


class TestOccasionFilter:

    def test_casual_occasion_keeps_all_items(self, casual_item, formal_item, top_item):
        from engine.occasion_filter import filter_by_occasion
        items = [casual_item, formal_item, top_item]
        result = filter_by_occasion(items, Occasion.CASUAL)
        assert len(result) == 3  # casual allows everything

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

    # ── New occasions ──────────────────────────────────────────────────────────

    def test_smart_casual_accepts_all_formalities(self):
        from engine.occasion_filter import filter_by_occasion
        casual_item  = _make_item(30, Category.TOP, formality=Formality.CASUAL)
        formal_item  = _make_item(31, Category.TOP, formality=Formality.FORMAL)
        both_item    = _make_item(32, Category.TOP, formality=Formality.BOTH)
        result = filter_by_occasion([casual_item, formal_item, both_item], Occasion.SMART_CASUAL)
        assert len(result) == 3

    def test_party_excludes_formal_only_items(self):
        from engine.occasion_filter import filter_by_occasion
        formal_item = _make_item(40, Category.TOP, formality=Formality.FORMAL)
        casual_item = _make_item(41, Category.TOP, formality=Formality.CASUAL)
        both_item   = _make_item(42, Category.TOP, formality=Formality.BOTH)
        result = filter_by_occasion([formal_item, casual_item, both_item], Occasion.PARTY)
        assert formal_item not in result
        assert casual_item in result
        assert both_item in result

    def test_athletic_accepts_only_casual(self):
        from engine.occasion_filter import filter_by_occasion
        casual_item = _make_item(50, Category.TOP, formality=Formality.CASUAL)
        formal_item = _make_item(51, Category.TOP, formality=Formality.FORMAL)
        both_item   = _make_item(52, Category.TOP, formality=Formality.BOTH)
        result = filter_by_occasion([casual_item, formal_item, both_item], Occasion.ATHLETIC)
        assert result == [casual_item]

    def test_athletic_rejects_formal_items(self):
        from engine.occasion_filter import filter_by_occasion
        formal_item = _make_item(60, Category.TOP, formality=Formality.FORMAL)
        result = filter_by_occasion([formal_item], Occasion.ATHLETIC)
        assert result == []

    def test_date_night_accepts_all_formalities(self):
        from engine.occasion_filter import filter_by_occasion
        casual_item = _make_item(70, Category.TOP, formality=Formality.CASUAL)
        formal_item = _make_item(71, Category.TOP, formality=Formality.FORMAL)
        both_item   = _make_item(72, Category.TOP, formality=Formality.BOTH)
        result = filter_by_occasion([casual_item, formal_item, both_item], Occasion.DATE_NIGHT)
        assert len(result) == 3

    def test_all_six_occasions_present_in_rules(self):
        from engine.occasion_filter import OCCASION_RULES
        expected = {"casual", "formal", "smart_casual", "party", "athletic", "date_night"}
        assert expected == set(OCCASION_RULES.keys())
