"""
tests/test_hard_rules.py
Tests for Gate 1 — hard fashion rules.
Run: pytest tests/test_hard_rules.py -v

These tests define the expected behavior BEFORE the implementation is written.
If passes_hard_rules() is not yet implemented, all tests here will fail — that is correct.
Write hard_rules.py until all tests pass.
"""

import pytest

# Uncomment when hard_rules.py is implemented:
# from engine.hard_rules import passes_hard_rules


class TestHardRules:

    def test_top_bottom_shoes_is_valid(self, top_item, bottom_item, shoes_item):
        from engine.hard_rules import passes_hard_rules
        assert passes_hard_rules([top_item, bottom_item, shoes_item]) is True

    def test_dress_shoes_is_valid(self, dress_item, shoes_item):
        from engine.hard_rules import passes_hard_rules
        assert passes_hard_rules([dress_item, shoes_item]) is True

    def test_jumpsuit_shoes_is_valid(self, jumpsuit_item, shoes_item):
        from engine.hard_rules import passes_hard_rules
        assert passes_hard_rules([jumpsuit_item, shoes_item]) is True

    def test_dress_with_top_is_rejected(self, dress_item, top_item, shoes_item):
        from engine.hard_rules import passes_hard_rules
        assert passes_hard_rules([dress_item, top_item, shoes_item]) is False

    def test_dress_with_bottom_is_rejected(self, dress_item, bottom_item, shoes_item):
        from engine.hard_rules import passes_hard_rules
        assert passes_hard_rules([dress_item, bottom_item, shoes_item]) is False

    def test_jumpsuit_with_top_is_rejected(self, jumpsuit_item, top_item, shoes_item):
        from engine.hard_rules import passes_hard_rules
        assert passes_hard_rules([jumpsuit_item, top_item, shoes_item]) is False

    def test_jumpsuit_with_bottom_is_rejected(self, jumpsuit_item, bottom_item, shoes_item):
        from engine.hard_rules import passes_hard_rules
        assert passes_hard_rules([jumpsuit_item, bottom_item, shoes_item]) is False

    def test_dress_with_jumpsuit_is_rejected(self, dress_item, jumpsuit_item, shoes_item):
        from engine.hard_rules import passes_hard_rules
        assert passes_hard_rules([dress_item, jumpsuit_item, shoes_item]) is False

    def test_duplicate_category_is_rejected(self, top_item, bottom_item, shoes_item):
        from engine.hard_rules import passes_hard_rules
        # Two shoes — same category appears twice
        import copy
        shoes2 = copy.deepcopy(shoes_item)
        shoes2 = shoes2.model_copy(update={"item_id": 99})
        assert passes_hard_rules([top_item, bottom_item, shoes_item, shoes2]) is False

    def test_top_bottom_outwear_shoes_is_valid(
        self, top_item, bottom_item, outwear_item, shoes_item
    ):
        from engine.hard_rules import passes_hard_rules
        assert passes_hard_rules([top_item, bottom_item, outwear_item, shoes_item]) is True

    def test_dress_outwear_shoes_is_valid(self, dress_item, outwear_item, shoes_item):
        from engine.hard_rules import passes_hard_rules
        assert passes_hard_rules([dress_item, outwear_item, shoes_item]) is True

    # ─── Rule 5: formality mixing ──────────────────────────────────────────────

    def test_mixed_formal_casual_rejected(self, casual_item, formal_item, shoes_item):
        """An outfit with one casual and one formal item must be rejected."""
        from engine.hard_rules import passes_hard_rules
        # casual_item and formal_item are both Category.TOP — but Rule 4 (duplicates)
        # would trigger first. Use different categories for a clean Rule 5 test.
        from engine.models import Category, Formality
        from tests.conftest import _make_item
        formal_bottom = _make_item(20, Category.BOTTOM, formality=Formality.FORMAL, seed=20)
        assert passes_hard_rules([casual_item, formal_bottom, shoes_item]) is False

    def test_casual_with_both_is_valid(self, casual_item, shoes_item):
        """Casual + 'both' items are allowed — 'both' is neutral."""
        from engine.hard_rules import passes_hard_rules
        from engine.models import Category, Formality
        from tests.conftest import _make_item
        both_bottom = _make_item(21, Category.BOTTOM, formality=Formality.BOTH, seed=21)
        assert passes_hard_rules([casual_item, both_bottom, shoes_item]) is True

    def test_formal_with_both_is_valid(self, formal_item, shoes_item):
        """Formal + 'both' items are allowed — 'both' is neutral."""
        from engine.hard_rules import passes_hard_rules
        from engine.models import Category, Formality
        from tests.conftest import _make_item
        both_bottom = _make_item(22, Category.BOTTOM, formality=Formality.BOTH, seed=22)
        assert passes_hard_rules([formal_item, both_bottom, shoes_item]) is True

    def test_all_casual_is_valid(self, casual_item, shoes_item):
        """All-casual outfit is fine."""
        from engine.hard_rules import passes_hard_rules
        from engine.models import Category, Formality
        from tests.conftest import _make_item
        casual_bottom = _make_item(23, Category.BOTTOM, formality=Formality.CASUAL, seed=23)
        assert passes_hard_rules([casual_item, casual_bottom, shoes_item]) is True
