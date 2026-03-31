"""
Script 02 — Check Label Quality
================================
Prints random samples from each occasion so you can visually
verify the auto-labeling from Script 01 is correct.

Run AFTER Script 01.

Usage:
    python 02_check_label_quality.py

What to do:
    Read each printed outfit name and check if the label makes sense.
    If more than 3/15 samples look wrong → update keywords in Script 01
    and re-run Script 01, then run this script again.
"""

import json
import os
import random
from collections import Counter

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
LABELED_FILE   = "datasets/processed/train_labeled.json"
SAMPLES_EACH   = 15


def load_data(filepath):
    if not os.path.exists(filepath):
        print(f"ERROR: {filepath} not found. Run Script 01 first.")
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def show_distribution(outfits):
    counts = Counter(o.get("occasion") for o in outfits)
    total  = len(outfits)

    print(f"\n{'='*55}")
    print("  LABEL DISTRIBUTION")
    print(f"{'='*55}")
    print(f"  Total outfits: {total:,}\n")

    for occ in ["casual", "formal", "wedding"]:
        count = counts.get(occ, 0)
        pct   = (count / total * 100) if total else 0
        bar   = "█" * int(pct / 2)
        print(f"  {occ:<10} {count:>6,}  ({pct:5.1f}%)  {bar}")
    print(f"{'='*55}")


def show_samples(outfits, occasion, n=15):
    filtered = [o for o in outfits if o.get("occasion") == occasion]

    print(f"\n{'='*55}")
    print(f"  {occasion.upper()} — {len(filtered):,} total outfits")
    print(f"  Showing {min(n, len(filtered))} random samples")
    print(f"{'='*55}")

    if not filtered:
        print(f"  NO outfits found for {occasion}.")
        print(f"  Add more {occasion} keywords to Script 01 and re-run.")
        return

    samples = random.sample(filtered, min(n, len(filtered)))

    for i, outfit in enumerate(samples, 1):
        name  = outfit.get("name", "(no name)")
        items = outfit.get("items", [])
        cats  = [item.get("category", "?") for item in items]
        print(f"  {i:2}. \"{name}\"")
        print(f"      label: {occasion}  |  items: {cats}")
        print(f"      {'─'*48}")


def check_item_categories(outfits):
    print(f"\n{'='*55}")
    print("  ITEM CATEGORY DISTRIBUTION")
    print(f"{'='*55}")

    all_cats = []
    for o in outfits:
        for item in o.get("items", []):
            all_cats.append(item.get("category", "unknown"))

    counts = Counter(all_cats)
    total  = len(all_cats)

    for cat, count in sorted(counts.items(), key=lambda x: -x[1]):
        pct = (count / total * 100) if total else 0
        print(f"  {cat:<12} {count:>7,}  ({pct:5.1f}%)")

    # Warn if shoes or outwear missing
    if counts.get("shoes", 0) == 0:
        print("\n  ⚠ WARNING: Zero shoe items found in labeled data.")
        print("  This may mean Polyvore item category IDs are not mapping correctly.")
        print("  Check Script 00 output for actual category IDs.")

    if counts.get("outwear", 0) == 0:
        print("\n  ⚠ WARNING: Zero outwear items found.")


def main():
    print("\n" + "="*55)
    print("  Script 02 — Check Label Quality")
    print("="*55)

    outfits = load_data(LABELED_FILE)
    if not outfits:
        return

    random.seed(99)  # fixed seed so you get same samples each run

    show_distribution(outfits)
    show_samples(outfits, "casual",  SAMPLES_EACH)
    show_samples(outfits, "formal",  SAMPLES_EACH)
    show_samples(outfits, "wedding", SAMPLES_EACH)
    check_item_categories(outfits)

    print(f"\n{'='*55}")
    print("  HOW TO DECIDE IF QUALITY IS GOOD:")
    print(f"{'='*55}")
    print("  ✓ If most names clearly match their label → proceed to Script 04")
    print("  ✗ If many names look wrong → open Script 01,")
    print("    update keyword lists, re-run Script 01, then re-run this")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
