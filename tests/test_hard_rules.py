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

    # ─── Cross-formality mixing (smart casual is valid) ─────────────────────────

    def test_formal_shirt_with_casual_jeans_allowed(self, shoes_item):
        """Formal shirt + casual jeans = classic smart casual — must be allowed."""
        from engine.hard_rules import passes_hard_rules
        from engine.models import Category, Formality
        from tests.conftest import _make_item
        formal_top = _make_item(20, Category.TOP, formality=Formality.FORMAL, seed=20)
        casual_bottom = _make_item(21, Category.BOTTOM, formality=Formality.CASUAL, seed=21)
        assert passes_hard_rules([formal_top, casual_bottom, shoes_item]) is True

    def test_casual_top_with_formal_bottom_allowed(self, shoes_item):
        """Casual top + formal trousers = valid smart casual — must be allowed."""
        from engine.hard_rules import passes_hard_rules
        from engine.models import Category, Formality
        from tests.conftest import _make_item
        casual_top = _make_item(22, Category.TOP, formality=Formality.CASUAL, seed=22)
        formal_bottom = _make_item(23, Category.BOTTOM, formality=Formality.FORMAL, seed=23)
        assert passes_hard_rules([casual_top, formal_bottom, shoes_item]) is True

    def test_casual_with_both_is_valid(self, casual_item, shoes_item):
        """Casual + 'both' items are allowed."""
        from engine.hard_rules import passes_hard_rules
        from engine.models import Category, Formality
        from tests.conftest import _make_item
        both_bottom = _make_item(24, Category.BOTTOM, formality=Formality.BOTH, seed=24)
        assert passes_hard_rules([casual_item, both_bottom, shoes_item]) is True

    def test_formal_with_both_is_valid(self, formal_item, shoes_item):
        """Formal + 'both' items are allowed."""
        from engine.hard_rules import passes_hard_rules
        from engine.models import Category, Formality
        from tests.conftest import _make_item
        both_bottom = _make_item(25, Category.BOTTOM, formality=Formality.BOTH, seed=25)
        assert passes_hard_rules([formal_item, both_bottom, shoes_item]) is True

    def test_all_casual_is_valid(self, casual_item, shoes_item):
        """All-casual outfit is fine."""
        from engine.hard_rules import passes_hard_rules
        from engine.models import Category, Formality
        from tests.conftest import _make_item
        casual_bottom = _make_item(26, Category.BOTTOM, formality=Formality.CASUAL, seed=26)
        assert passes_hard_rules([casual_item, casual_bottom, shoes_item]) is True

    # ─── Tier B: cross-cultural blocked pairs ─────────────────────────────────

    def test_polo_shalwar_blocked(self, shoes_item):
        """Polo + shalwar is a cross-cultural mismatch — must be rejected."""
        from engine.hard_rules import passes_hard_rules
        from engine.models import Category, Formality
        from tests.conftest import _make_item
        polo = _make_item(30, Category.TOP, formality=Formality.CASUAL, seed=30)
        polo = polo.model_copy(update={"sub_category": "polo_shirt"})
        shalwar = _make_item(31, Category.BOTTOM, formality=Formality.BOTH, seed=31)
        shalwar = shalwar.model_copy(update={"sub_category": "shalwar"})
        assert passes_hard_rules([polo, shalwar, shoes_item]) is False

    def test_tshirt_shalwar_blocked(self, shoes_item):
        """T-shirt + shalwar is a cross-cultural mismatch — must be rejected."""
        from engine.hard_rules import passes_hard_rules
        from engine.models import Category, Formality
        from tests.conftest import _make_item
        tshirt = _make_item(32, Category.TOP, formality=Formality.CASUAL, seed=32)
        tshirt = tshirt.model_copy(update={"sub_category": "casual_tshirt"})
        shalwar = _make_item(33, Category.BOTTOM, formality=Formality.BOTH, seed=33)
        shalwar = shalwar.model_copy(update={"sub_category": "shalwar"})
        assert passes_hard_rules([tshirt, shalwar, shoes_item]) is False

    def test_hoodie_shalwar_blocked(self, shoes_item):
        """Hoodie + shalwar is a cross-cultural mismatch — must be rejected."""
        from engine.hard_rules import passes_hard_rules
        from engine.models import Category, Formality
        from tests.conftest import _make_item
        hoodie = _make_item(34, Category.TOP, formality=Formality.CASUAL, seed=34)
        hoodie = hoodie.model_copy(update={"sub_category": "hoodie"})
        shalwar = _make_item(35, Category.BOTTOM, formality=Formality.BOTH, seed=35)
        shalwar = shalwar.model_copy(update={"sub_category": "shalwar"})
        assert passes_hard_rules([hoodie, shalwar, shoes_item]) is False

    def test_sherwani_shorts_blocked(self, shoes_item):
        """Sherwani + shorts is absurd — SA black-tie with casual bottom."""
        from engine.hard_rules import passes_hard_rules
        from engine.models import Category, Formality
        from tests.conftest import _make_item
        shirt = _make_item(40, Category.TOP, formality=Formality.FORMAL, seed=40)
        sherwani = _make_item(41, Category.OUTWEAR, formality=Formality.FORMAL, seed=41)
        sherwani = sherwani.model_copy(update={"sub_category": "sherwani"})
        shorts = _make_item(42, Category.BOTTOM, formality=Formality.CASUAL, seed=42)
        shorts = shorts.model_copy(update={"sub_category": "shorts"})
        assert passes_hard_rules([shirt, sherwani, shorts, shoes_item]) is False

    def test_sherwani_tshirt_blocked(self, shoes_item):
        """T-shirt under sherwani — costume, not fashion."""
        from engine.hard_rules import passes_hard_rules
        from engine.models import Category, Formality
        from tests.conftest import _make_item
        tshirt = _make_item(43, Category.TOP, formality=Formality.CASUAL, seed=43)
        tshirt = tshirt.model_copy(update={"sub_category": "casual_tshirt"})
        sherwani = _make_item(44, Category.OUTWEAR, formality=Formality.FORMAL, seed=44)
        sherwani = sherwani.model_copy(update={"sub_category": "sherwani"})
        shalwar = _make_item(45, Category.BOTTOM, formality=Formality.BOTH, seed=45)
        assert passes_hard_rules([tshirt, sherwani, shalwar, shoes_item]) is False

    def test_blazer_sneakers_allowed(self, shoes_item):
        """Blazer + sneakers = modern smart casual — GQ/Esquire endorsed."""
        from engine.hard_rules import passes_hard_rules
        from engine.models import Category, Formality
        from tests.conftest import _make_item
        shirt = _make_item(46, Category.TOP, formality=Formality.BOTH, seed=46)
        blazer = _make_item(47, Category.OUTWEAR, formality=Formality.FORMAL, seed=47)
        blazer = blazer.model_copy(update={"sub_category": "blazer"})
        jeans = _make_item(48, Category.BOTTOM, formality=Formality.CASUAL, seed=48)
        sneakers = _make_item(49, Category.SHOES, formality=Formality.CASUAL, seed=49)
        sneakers = sneakers.model_copy(update={"sub_category": "sneakers"})
        assert passes_hard_rules([shirt, blazer, jeans, sneakers]) is True

    def test_kurta_shalwar_allowed(self, shoes_item):
        """Kurta + shalwar is a classic South Asian combo — must be allowed."""
        from engine.hard_rules import passes_hard_rules
        from engine.models import Category, Formality
        from tests.conftest import _make_item
        kurta = _make_item(36, Category.TOP, formality=Formality.BOTH, seed=36)
        kurta = kurta.model_copy(update={"sub_category": "kurta"})
        shalwar = _make_item(37, Category.BOTTOM, formality=Formality.BOTH, seed=37)
        shalwar = shalwar.model_copy(update={"sub_category": "shalwar"})
        assert passes_hard_rules([kurta, shalwar, shoes_item]) is True
