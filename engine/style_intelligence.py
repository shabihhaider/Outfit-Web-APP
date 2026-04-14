"""
engine/style_intelligence.py
Gate 3 component — Knowledge-based fashion intelligence.

Instead of hard-coded colors, this module uses professional 'Fashion Pairings'
inspired by the Polyvore dataset (which was created by real-world bloggers
and fashion magazines).

It leverages the 'sub_category' labels (e.g., 'kurta', 'polo_shirt', 'jeans')
to identify classic, high-end looks.
"""

# Stylistic Synergy Matrix
# High-fidelity combinations derived from Polyvore stylist data.
# Format: { (Subcat1, Subcat2): Bonus }
SYNERGY_BONUSES = {
    # ── Classic Men's/Formal Looks ──────────────────────────────────────────
    frozenset({"top:formal_shirt", "bottom:dress_trousers"}): 0.50,  # The Suit Standard
    frozenset({"top:formal_shirt", "outwear:blazer"}): 0.45,
    frozenset({"bottom:dress_trousers", "outwear:blazer"}): 0.45,
    frozenset({"top:formal_shirt", "shoes:formal_shoes"}): 0.40,

    # ── Smart Casual / Professional ──────────────────────────────────────────
    frozenset({"top:polo_shirt", "bottom:chinos"}): 0.45,  # The Polo Classic
    frozenset({"top:blouse", "bottom:skirt"}): 0.40,
    frozenset({"top:blouse", "bottom:dress_trousers"}): 0.40,
    frozenset({"shoes:loafers", "bottom:chinos"}): 0.35,

    # ── High-End Casual (Denim Master) ───────────────────────────────────────
    frozenset({"top:formal_shirt", "bottom:jeans"}): 0.50,  # THE White Shirt + Blue Jeans logic (Dynamic)
    frozenset({"top:polo_shirt", "bottom:jeans"}): 0.35,
    frozenset({"top:casual_tshirt", "bottom:jeans"}): 0.25,

    # ── Pakistani / South Asian Heritage (Master Level) ─────────────────────
    frozenset({"top:kurta", "bottom:shalwar"}): 0.50,  # Traditional Unity
    frozenset({"top:kameez", "bottom:shalwar"}): 0.50,
    frozenset({"top:kurta", "shoes:chappal"}): 0.40,
    frozenset({"outwear:sherwani", "bottom:shalwar"}): 0.50,

    # ── Fusion (South Asian + Western mix) ────────────────────────────────
    frozenset({"top:kurta", "bottom:jeans"}): 0.30,
    frozenset({"top:kurta", "bottom:chinos"}): 0.30,
    frozenset({"top:kameez", "bottom:jeans"}): 0.25,

    # ── Smart Casual / Modern (Global) ────────────────────────────────────
    frozenset({"outwear:blazer", "bottom:jeans"}): 0.35,
    frozenset({"outwear:blazer", "bottom:chinos"}): 0.40,
    frozenset({"outwear:blazer", "top:casual_tshirt"}): 0.30,  # Modern smart casual
    frozenset({"top:casual_tshirt", "bottom:shorts"}): 0.30,   # Summer casual

    # ── Athleisure ────────────────────────────────────────────────────────
    frozenset({"top:hoodie", "bottom:jeans"}): 0.30,
}


def score_outfit_intelligence(items) -> float:
    """
    Computes a 'Stylistic Intelligence' score (0 to 1).
    Heavily rewards combinations that follow established fashion knowledge
    from magazines, blogs, and stylist datasets.
    """
    total_bonus = 0.0

    # Build a list of "{category}:{sub_category}" keys
    item_keys = []
    for item in items:
        sub_cat = getattr(item, "sub_category", None)
        if sub_cat:
            cat = item.category.value if hasattr(item.category, "value") else str(item.category)
            item_keys.append(f"{cat}:{sub_cat}")

    # If no items have sub-categories (CLIP didn't run), intelligence is neutral
    if not item_keys:
        return 0.5

    # Check all pairs for established stylistic synergies
    for i in range(len(item_keys)):
        for j in range(i + 1, len(item_keys)):
            pair = frozenset({item_keys[i], item_keys[j]})
            bonus = SYNERGY_BONUSES.get(pair, 0.0)
            total_bonus += bonus

    # Normalize and clamp:
    # Starts at a base of 0.5. A single classic pairing (e.g. Polo+Jeans)
    # will push it to 0.85+. Multiple synergies hit 1.0.
    return min(1.0, 0.5 + total_bonus)
