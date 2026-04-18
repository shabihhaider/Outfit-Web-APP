"""
engine/hard_rules.py
Gate 1 — Hard fashion rules that block structurally invalid outfit combinations.

Two tiers of rules:
  Tier A — Category-level (always active): structural validity (dress/jumpsuit
           exclusivity, no duplicate categories).
  Tier B — Sub-category (active when CLIP labels present): specific pair blocks
           for genuinely incompatible items.

Cross-formality mixing (formal shirt + jeans, blazer + t-shirt) is intentionally
ALLOWED — smart casual is the most common modern dress code. Bad cross-formality
combos are caught by specific blocked pairs (e.g. hoodie + formal trousers), not
by a blanket formality rule.
"""

from __future__ import annotations

from engine.models import WardrobeItem, Category


# ─── Tier B: Sub-category blocked pairs ───────────────────────────────────────
# Active only when both items have sub_category set (by CLIP tagger).
# Uses "{category}:{sub_category}" keys.
# frozenset: order-independent pair matching.
#
# Philosophy: only hard-block combos that are UNIVERSALLY considered wrong.
# If a combo is merely "unusual" or "fashion-forward", let the scorer handle it.

BLOCKED_SUBCATEGORY_PAIRS: frozenset[frozenset] = frozenset({
    # ── Formality extremes (skipping 2+ levels) ─────────────────────────────
    frozenset({"top:hoodie",        "bottom:dress_trousers"}),  # hoodie + formal trousers
    frozenset({"top:hoodie",        "shoes:formal_shoes"}),     # hoodie + Oxford shoes
    frozenset({"top:hoodie",        "shoes:heels"}),            # hoodie + heels
    frozenset({"outwear:hoodie_jacket", "bottom:dress_trousers"}),  # zip hoodie + formal trousers
    frozenset({"outwear:hoodie_jacket", "shoes:formal_shoes"}),     # zip hoodie + formal shoes
    frozenset({"top:formal_shirt",  "bottom:shorts"}),          # dress shirt + shorts

    # ── Blazer compatibility ─────────────────────────────────────────────────
    # blazer + sneakers is ALLOWED — modern smart casual (GQ/Esquire endorsed)
    frozenset({"outwear:blazer",    "bottom:leggings"}),   # blazer + leggings

    # ── Sherwani (SA black-tie — demands formal/traditional pairing) ────────
    frozenset({"outwear:sherwani",  "bottom:jeans"}),      # sherwani + jeans
    frozenset({"outwear:sherwani",  "bottom:shorts"}),     # sherwani + shorts
    frozenset({"outwear:sherwani",  "bottom:leggings"}),   # sherwani + leggings
    frozenset({"outwear:sherwani",  "shoes:sneakers"}),    # sherwani + sneakers
    frozenset({"outwear:sherwani",  "top:casual_tshirt"}),  # tshirt under sherwani
    frozenset({"outwear:sherwani",  "top:hoodie"}),        # hoodie under sherwani

    # ── Chappal (SA casual sandal — doesn't pair with formal Western) ───────
    frozenset({"shoes:chappal",     "outwear:blazer"}),    # chappal + blazer
    frozenset({"shoes:chappal",     "outwear:sherwani"}),  # chappal + sherwani

    # ── Cross-cultural: Western casual + Eastern traditional bottom ──────────
    frozenset({"top:polo_shirt",    "bottom:shalwar"}),    # polo + shalwar
    frozenset({"top:casual_tshirt", "bottom:shalwar"}),    # tshirt + shalwar
    frozenset({"top:hoodie",        "bottom:shalwar"}),    # hoodie + shalwar
    frozenset({"outwear:hoodie_jacket", "bottom:shalwar"}),  # zip hoodie + shalwar
})


def _sub_category_key(item: WardrobeItem) -> str | None:
    """
    Return "{category}:{sub_category}" if sub_category is set, else None.
    sub_category is stored on WardrobeItem as an optional attribute set by the
    Flask layer from WardrobeItemDB.sub_category (CLIP-tagged value).
    """
    sub_cat = getattr(item, "sub_category", None)
    if not sub_cat:
        return None
    cat = item.category.value if hasattr(item.category, "value") else str(item.category)
    return f"{cat}:{sub_cat}"


def passes_hard_rules(outfit_items: list[WardrobeItem]) -> bool:
    """
    Returns True if the outfit is structurally valid under all active Gate 1 rules.

    Tier A — Category-level rules (always enforced):
      1. A dress cannot coexist with a top or bottom.
      2. A jumpsuit cannot coexist with a top or bottom.
      3. A dress and a jumpsuit cannot coexist.
      4. No two items may share the same category.

    Tier B — Sub-category rules (enforced only when CLIP labels are present):
      5. Blocked pairs from BLOCKED_SUBCATEGORY_PAIRS (e.g. hoodie+dress_trousers,
         sherwani+jeans, dress_shirt+shorts).

    Note: Cross-formality mixing (formal + casual items) is intentionally allowed.
    Smart casual (formal shirt + jeans, blazer + t-shirt) is the most common modern
    dress code. Genuinely bad cross-formality combos are caught by specific blocked
    pairs in Tier B, not by a blanket formality rule.
    """
    categories = [item.category for item in outfit_items]

    # ── Tier A rules ──────────────────────────────────────────────────────────

    # Rule 1: dress cannot be worn with top or bottom
    if Category.DRESS in categories and (
        Category.TOP in categories or Category.BOTTOM in categories
    ):
        return False

    # Rule 2: jumpsuit cannot be worn with top or bottom
    if Category.JUMPSUIT in categories and (
        Category.TOP in categories or Category.BOTTOM in categories
    ):
        return False

    # Rule 3: dress and jumpsuit cannot coexist
    if Category.DRESS in categories and Category.JUMPSUIT in categories:
        return False

    # Rule 4: no duplicate categories
    if len(categories) != len(set(categories)):
        return False

    # ── Tier B rules (sub-category, requires CLIP labels) ─────────────────────

    # Build sub-category keys only for items that have CLIP labels
    sub_keys = [_sub_category_key(item) for item in outfit_items]
    labeled  = [k for k in sub_keys if k is not None]

    # Rule 5: blocked sub-category pairs
    # Only applied when BOTH items in a pair have sub-category labels
    if len(labeled) >= 2:
        for i in range(len(labeled)):
            for j in range(i + 1, len(labeled)):
                if labeled[i] is None or labeled[j] is None:
                    continue
                pair = frozenset({labeled[i], labeled[j]})
                if pair in BLOCKED_SUBCATEGORY_PAIRS:
                    return False

    return True
