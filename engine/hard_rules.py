"""
engine/hard_rules.py
Gate 1 — Hard fashion rules that block structurally invalid outfit combinations.

Two tiers of rules:
  Tier A — Category-level rules (always active, enforceable with 6-category Model 1).
  Tier B — Sub-category rules (active when CLIP sub-category labels are present).
           When sub_category is None, Tier B rules are silently skipped.

Tier B rules are based on established fashion incompatibilities that transcend
cultural boundaries (blazer + joggers is incongruous in Western AND South Asian
fashion contexts).
"""

from __future__ import annotations

from engine.models import WardrobeItem, Category, Formality


# ─── Tier B: Sub-category blocked pairs ───────────────────────────────────────
# Active only when both items have sub_category set (by CLIP tagger).
# Uses "{category}:{sub_category}" keys.
# frozenset: order-independent pair matching.

BLOCKED_SUBCATEGORY_PAIRS: frozenset[frozenset] = frozenset({
    frozenset({"outwear:blazer",    "bottom:leggings"}),   # blazer + leggings
    frozenset({"outwear:blazer",    "shoes:sneakers"}),    # blazer + sneakers (unless smart-casual intent)
    frozenset({"outwear:sherwani",  "bottom:jeans"}),      # sherwani + jeans
    frozenset({"outwear:sherwani",  "shoes:sneakers"}),    # sherwani + sneakers
    frozenset({"top:formal_shirt",  "bottom:shorts"}),     # dress shirt + shorts
    frozenset({"top:hoodie",        "bottom:dress_trousers"}),  # hoodie + formal trousers
    frozenset({"top:hoodie",        "shoes:formal_shoes"}),     # hoodie + Oxford shoes
    frozenset({"top:hoodie",        "shoes:heels"}),       # hoodie + heels
    frozenset({"shoes:heels",       "bottom:leggings"}),   # heels + leggings
    frozenset({"shoes:chappal",     "outwear:blazer"}),    # chappal + blazer
    frozenset({"shoes:chappal",     "outwear:sherwani"}),  # chappal + sherwani (formal mismatch)
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
      5. Formal and casual items cannot coexist (items tagged "both" are exempt).

    Tier B — Sub-category rules (enforced only when CLIP labels are present):
      6. Blocked pairs from BLOCKED_SUBCATEGORY_PAIRS (e.g. blazer+sneakers,
         sherwani+jeans, dress_shirt+shorts, hoodie+formal_trousers).
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

    # Rule 5: formal and casual items cannot be mixed
    # Items tagged "both" are neutral and excluded from this check
    strict_formalities = {
        item.formality for item in outfit_items
        if item.formality != Formality.BOTH
    }
    if Formality.CASUAL in strict_formalities and Formality.FORMAL in strict_formalities:
        return False

    # ── Tier B rules (sub-category, requires CLIP labels) ─────────────────────

    # Build sub-category keys only for items that have CLIP labels
    sub_keys = [_sub_category_key(item) for item in outfit_items]
    labeled  = [k for k in sub_keys if k is not None]

    # Rule 6: blocked sub-category pairs
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
