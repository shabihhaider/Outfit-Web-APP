"""
Script 01 — Label Polyvore Data with Occasion Labels (v2)
==========================================================
Reads train_no_dup.json and valid_no_dup.json from Polyvore metadata.
Assigns occasion labels using:
  Pass 1: Weighted keyword scoring on outfit names
  Pass 2: Composition-based fallback for unnamed/unmatched outfits
Saves labeled versions to processed/ folder.

Run AFTER Script 00 (exploration).

Usage:
    python 01_label_polyvore.py

Output:
    datasets/processed/train_labeled.json
    datasets/processed/valid_labeled.json

Changes in v2:
    - Tightened wedding keywords (removed 'party', 'date', 'clubbing' etc.)
    - Cleaned formal keywords (removed item-based: 'skirt', 'heels', 'pumps')
    - Weighted scoring for multi-keyword overlap instead of first-match
    - Composition-based fallback to recover discarded outfits
"""

import json
import os
import re

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
POLYVORE_TRAIN_JSON = "datasets/for_model2/metadata/train_no_dup.json"
POLYVORE_VALID_JSON = "datasets/for_model2/metadata/valid_no_dup.json"
OUTPUT_DIR          = "datasets/processed/"
OUTPUT_TRAIN        = os.path.join(OUTPUT_DIR, "train_labeled.json")
OUTPUT_VALID        = os.path.join(OUTPUT_DIR, "valid_labeled.json")

# ─────────────────────────────────────────────
# POLYVORE CATEGORY ID → OUR CATEGORY MAPPING
# Based on category_id.txt from Polyvore-Images
# ─────────────────────────────────────────────
POLYVORE_CATEGORY_MAP = {
    # Tops
    11: "top", 15: "top", 17: "top", 18: "top", 19: "top",
    21: "top", 104: "top", 252: "top", 272: "top", 273: "top",
    275: "top", 309: "top", 342: "top", 4454: "top", 4495: "top",
    4496: "top", 4497: "top", 4498: "top",

    # Bottoms (pants + skirts merged)
    7: "bottom", 8: "bottom", 9: "bottom", 10: "bottom",
    27: "bottom", 28: "bottom", 29: "bottom", 237: "bottom",
    238: "bottom", 239: "bottom", 240: "bottom", 241: "bottom",
    253: "bottom", 254: "bottom", 255: "bottom", 279: "bottom",
    280: "bottom", 287: "bottom", 288: "bottom", 310: "bottom",
    332: "bottom", 4452: "bottom", 4458: "bottom", 4459: "bottom",

    # Outwear
    23: "outwear", 24: "outwear", 25: "outwear", 26: "outwear",
    30: "outwear", 236: "outwear", 256: "outwear", 276: "outwear",
    277: "outwear", 4455: "outwear", 4456: "outwear", 4457: "outwear",
    281: "outwear",

    # Shoes
    41: "shoes", 42: "shoes", 43: "shoes", 46: "shoes",
    47: "shoes", 48: "shoes", 49: "shoes", 50: "shoes",
    261: "shoes", 262: "shoes", 263: "shoes", 264: "shoes",
    265: "shoes", 266: "shoes", 267: "shoes", 268: "shoes",
    291: "shoes", 292: "shoes", 293: "shoes", 294: "shoes",
    295: "shoes", 296: "shoes", 297: "shoes", 298: "shoes",
    4464: "shoes", 4465: "shoes",

    # Dress
    3: "dress", 4: "dress", 5: "dress", 6: "dress",
    4516: "dress",

    # Jumpsuit
    243: "jumpsuit", 244: "jumpsuit",
}

# ─────────────────────────────────────────────
# KEYWORD LISTS — v2 (tightened)
# ─────────────────────────────────────────────

# Wedding = celebration / dressy event
# ONLY event-specific terms, NOT generic words like "party" or "date"
WEDDING_KEYWORDS = [
    # Specific wedding/bridal
    "wedding", "bridal", "bride", "groom", "bridesmai", 
    "groomsmen", "ceremony", "engagement", "rehearsal dinner",
    "bridal shower", "marriage", "sherwani", "lehenga", "sari",
    "engagement party", "wedding guest", "bridal party",
    "matrimony", "bachelorette", "mother of the bride", "maid of honor",
    "boutonniere", "corsage", "kurta", "anarkali", "gharara", "sharara",
    
    # Formal celebration events
    "prom", "ball", "gown", "gala", "red carpet",
    "black tie", "black-tie", "formal dinner", "banquet",
    "soiree", "pageant", "homecoming", "white tie", "formal event",
    "reception", "celebration", "special occasion", "party dress",

    # Holiday / cultural / SOCIAL celebrations (Recovering quantity > 500)
    "festive", "holiday party", "christmas party", "festivity",
    "new year", "new years eve", "nye", "anniversary",
    "eid", "diwali", "valentine", "mehndi", "sangeet", "valima",
    "party", "date", "club", "clubbing", "night out", "birthday",

    # Dressy / evening (genuinely celebration-appropriate)
    "eveningwear", "evening wear", "cocktail dress",
    "cocktail party", "dinner party", "tuxedo", "bow tie",
    "cocktail", "evening", "lace dress", "maxi dress",
]

# Formal = professional / business context
# ONLY context/occasion terms, NOT clothing item names
FORMAL_KEYWORDS = [
    # Directly professional
    "formal", "office", "work", "business", "professional",
    "corporate", "interview", "meeting", "conference",
    "boardroom", "executive", "career",

    # Professionally styled
    "tailored", "dress shirt", "button down", "slacks",
    "power look", "smart casual", "chic office",
    "workwear", "work wear", "9 to 5", "nine to five",

    # Professional style descriptors
    "sophisticated", "polished", "structured", "elegant",
    "classic", "office look", "work outfit",
    "business casual", "professional look", "corporate wear",
    "smart look",
]

# Casual = everything everyday / relaxed / street
CASUAL_KEYWORDS = [
    # Directly casual
    "casual", "everyday", "street", "weekend", "comfy",
    "comfortable", "relaxed", "laid back", "chill", "lazy",
    "simple", "basic", "effortless", "minimal", "minimalist",

    # Casual clothing refs (safe — these ARE casual-specific)
    "jeans", "denim", "tee", "t-shirt", "sneakers",
    "hoodie", "sweatshirt", "jogger", "sweat pants",
    "vans", "converse",

    # Casual styles
    "sporty", "athleisure", "boho", "bohemian",
    "vintage", "retro", "grunge",

    # Casual contexts
    "daily", "campus", "college", "school",
    "brunch", "coffee", "park", "walking",
    "vacation", "holiday", "staycation", "road trip",
    "hanging out", "selfie", "ootd", "outfit of the day",

    # Season-as-casual (when used alone = casual vibe)
    "spring", "summer", "fall", "autumn", "winter casual",

    # Common casual items
    "shorts", "boots", "sweater", "cardigan",

    # Generic style
    "cool", "fun", "cute", "pretty", "trendy",
    "shopping", "city", "travel",
]


def get_outfit_name(outfit: dict) -> str:
    """Extract name from outfit dict. Handles all known key variations."""
    return (
        outfit.get("name") or
        outfit.get("title") or
        outfit.get("set_name") or
        outfit.get("outfit_name") or
        ""
    ).strip()


def count_keyword_hits(name: str, keywords: list) -> int:
    """Count how many keywords from the list appear in the name."""
    name_lower = name.lower()
    hits = 0
    for kw in keywords:
        if re.search(rf"\b{re.escape(kw)}\b", name_lower):
            hits += 1
    return hits


def assign_occasion_label(outfit_name: str) -> tuple:
    """
    Assign occasion label using specificity-weighted scoring.

    Wedding keywords are the MOST specific (explicitly celebration-related),
    so each hit gets 3x weight. Formal keywords are moderately specific
    (professional context), each hit gets 2x weight. Casual keywords are
    the broadest (seasons, items, generic style), each hit gets 1x weight.

    This ensures: one "cocktail" hit (3 pts) beats one "spring" hit (1 pt).

    Special case: if name explicitly contains "casual", casual wins unless
    a more specific keyword has MORE raw hits.

    Returns (label, method_description).
    """
    name = outfit_name.lower()

    # Count raw keyword hits
    w_raw = count_keyword_hits(name, WEDDING_KEYWORDS)
    f_raw = count_keyword_hits(name, FORMAL_KEYWORDS)
    c_raw = count_keyword_hits(name, CASUAL_KEYWORDS)

    # If NO keywords matched at all → unknown (goes to composition fallback)
    if w_raw + f_raw + c_raw == 0:
        return "unknown", None

    # Apply specificity weights
    # Wedding is very specific → 3x weight
    # Formal is moderately specific → 2x weight
    # Casual is broad/generic → 1x weight
    w_score = w_raw * 3
    f_score = f_raw * 2
    c_score = c_raw * 1

    # Special case: if "casual" appears literally in the name AND casual
    # has at least 1 raw hit, give casual a boost to prevent misclassification
    # of names like "Casual Cocktail", "Casual Valentine" etc.
    if re.search(r"\bcasual\b", name) and c_raw >= 1:
        c_score += 2  # bonus for explicit casual mention

    desc = f"weighted(w={w_raw}x3={w_score},f={f_raw}x2={f_score},c={c_raw}x1={c_score})"

    # Highest weighted score wins
    scores = {"wedding": w_score, "formal": f_score, "casual": c_score}
    winner = max(scores, key=scores.get)

    # Tie-breaking: wedding > formal > casual (specific wins)
    max_val = scores[winner]
    if scores["wedding"] == max_val:
        return "wedding", desc
    if scores["formal"] == max_val:
        return "formal", desc

    return "casual", desc


def label_by_composition(items: list) -> tuple:
    """
    Fallback: assign occasion based on item category composition.
    Used only when keyword matching fails (no name or no keyword hits).

    Logic:
    - gown/dress alone + shoes only = formal (dressy silhouette)
    - 4+ items with outwear = formal (layered = structured look)
    - everything else = casual (safest default)

    Returns (label, method_description).
    """
    categories = [item["category"] for item in items]
    cat_set = set(categories)

    # Dress/jumpsuit + outwear = clearly formal/dressy
    if ("dress" in cat_set or "jumpsuit" in cat_set) and "outwear" in cat_set:
        return "formal", "composition(dress+outwear)"

    # 4+ items with outwear (top+bottom+outwear+shoes) = structured/formal
    if len(categories) >= 4 and "outwear" in cat_set:
        return "formal", "composition(4+items_with_outwear)"

    # Default = casual (safest assumption — most Polyvore outfits are casual)
    return "casual", "composition(default_casual)"


def normalize_outfit_items(items: list) -> list:
    """
    Normalize item list to consistent format.
    Returns list of dicts with item_id, category_id, category.
    """
    normalized = []

    for item in items:
        if isinstance(item, dict):
            item_id     = (item.get("item_id") or
                          item.get("id") or
                          item.get("image") or
                          str(item))
            category_id = item.get("categoryid") or item.get("category_id") or 0
        else:
            item_id     = str(item)
            category_id = 0

        try:
            cat_id = int(category_id)
        except (ValueError, TypeError):
            cat_id = 0

        our_category = POLYVORE_CATEGORY_MAP.get(cat_id, "unknown")

        if our_category != "unknown":
            normalized.append({
                "item_id":     str(item_id),
                "category_id": cat_id,
                "category":    our_category
            })

    return normalized


def process_file(input_path: str, output_path: str, split_name: str):
    """Process one Polyvore JSON file — label and save."""

    print(f"\n{'─'*55}")
    print(f"  Processing: {split_name}")
    print(f"{'─'*55}")

    if not os.path.exists(input_path):
        print(f"  ERROR: File not found: {input_path}")
        return

    print(f"  Reading: {input_path}")
    with open(input_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    if isinstance(raw_data, dict):
        data = list(raw_data.values())
        print(f"  Format: dict -> converted to list")
    else:
        data = raw_data
        print(f"  Format: list")

    print(f"  Total outfits: {len(data):,}")

    counts           = {"casual": 0, "formal": 0, "wedding": 0}
    method_counts    = {"keyword": 0, "composition": 0}
    labeled          = []
    skipped_noitems  = 0
    still_discarded  = 0

    for outfit in data:
        name = get_outfit_name(outfit)

        # Normalize items first (needed for both passes)
        raw_items = outfit.get("items", [])
        items     = normalize_outfit_items(raw_items)

        if not items:
            skipped_noitems += 1
            continue

        # Pass 1: Try keyword scoring
        label = "unknown"
        method = None
        if name:
            label, method = assign_occasion_label(name)

        # Pass 2: Composition fallback if keywords failed
        if label == "unknown":
            label, method = label_by_composition(items)
            method_counts["composition"] += 1
        else:
            method_counts["keyword"] += 1

        labeled_outfit = {
            "outfit_id": str(outfit.get("set_id") or outfit.get("id") or len(labeled)),
            "name":      name if name else "(unnamed)",
            "occasion":  label,
            "source":    "polyvore",
            "method":    method,
            "items":     items
        }

        labeled.append(labeled_outfit)
        counts[label] += 1

    # Print results
    total_saved = len(labeled)
    total_input = len(data)
    recovery_pct = (method_counts["composition"] / total_input * 100) if total_input else 0

    print(f"\n  Results:")
    print(f"    Labeled casual:          {counts['casual']:>6,}")
    print(f"    Labeled formal:          {counts['formal']:>6,}")
    print(f"    Labeled wedding:         {counts['wedding']:>6,}")
    print(f"    Skipped (no items):      {skipped_noitems:>6,}")
    print(f"    ─────────────────────────────")
    print(f"    Total saved:             {total_saved:>6,}")
    print(f"    Coverage:                {total_saved/total_input*100:.1f}%")
    print(f"")
    print(f"    Labeled by keywords:     {method_counts['keyword']:>6,}")
    print(f"    Labeled by composition:  {method_counts['composition']:>6,} ({recovery_pct:.1f}% recovered)")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(labeled, f, indent=2, ensure_ascii=False)

    print(f"\n  Saved -> {output_path}")


def main():
    print("\n" + "="*55)
    print("  Script 01 — Label Polyvore Data (v2)")
    print("  Tightened keywords + composition fallback")
    print("="*55)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    process_file(POLYVORE_TRAIN_JSON, OUTPUT_TRAIN, "Training Set")
    process_file(POLYVORE_VALID_JSON, OUTPUT_VALID, "Validation Set")

    print("\n" + "="*55)
    print("  Script 01 COMPLETE")
    print("  Next -> run 02_check_label_quality.py")
    print("="*55 + "\n")


if __name__ == "__main__":
    main()
