"""
Script 04 — Merge Datasets (Polyvore Only)
=============================================
Takes the labeled Polyvore data (train_labeled.json) and creates
the final_dataset.json ready for model training.

Manual wedding data has been removed from the project.
All wedding outfits now come from Polyvore keyword labeling only.

Run AFTER Scripts 01 and 02.

Usage:
    python 04_merge_datasets.py

Output:
    datasets/processed/final_dataset.json
"""

import json
import os
import random
from collections import Counter

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
POLYVORE_LABELED = "datasets/processed/train_labeled.json"
OUTPUT_DIR       = "datasets/processed/"
FINAL_OUTPUT     = os.path.join(OUTPUT_DIR, "final_dataset.json")
SHUFFLE          = True
RANDOM_SEED      = 42


def load(filepath, label):
    if not os.path.exists(filepath):
        print(f"  ⚠ Not found: {label} ({filepath})")
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"  [OK] Loaded {label}: {len(data):,} outfits")
    return data


def is_valid(outfit, index):
    for field in ["outfit_id", "occasion", "items"]:
        if field not in outfit:
            return False
    if outfit["occasion"] not in ("casual", "formal", "wedding"):
        return False
    if not outfit["items"]:
        return False
    return True


def remove_dupes(outfits):
    seen  = set()
    clean = []
    dupes = 0
    for o in outfits:
        oid = o.get("outfit_id", "")
        if oid in seen:
            dupes += 1
            continue
        seen.add(oid)
        clean.append(o)
    if dupes:
        print(f"  Removed {dupes:,} duplicates")
    return clean


def print_summary(outfits):
    counts  = Counter(o.get("occasion") for o in outfits)
    sources = Counter(o.get("source") for o in outfits)
    total   = len(outfits)

    print(f"\n{'='*55}")
    print("  FINAL DATASET SUMMARY")
    print(f"{'='*55}")
    print(f"  Total outfits: {total:,}")

    print(f"\n  By occasion:")
    for occ in ["casual", "formal", "wedding"]:
        count = counts.get(occ, 0)
        pct   = (count / total * 100) if total else 0
        print(f"    {occ:<10} {count:>6,}  ({pct:5.1f}%)")

    print(f"\n  By source:")
    for src, count in sorted(sources.items()):
        pct = (count / total * 100) if total else 0
        print(f"    {src:<12} {count:>6,}  ({pct:5.1f}%)")

    item_counts = [len(o.get("items", [])) for o in outfits]
    avg = sum(item_counts) / len(item_counts) if item_counts else 0
    print(f"\n  Avg items per outfit: {avg:.1f}")
    print(f"  Min items:            {min(item_counts) if item_counts else 0}")
    print(f"  Max items:            {max(item_counts) if item_counts else 0}")
    print(f"{'='*55}")


def main():
    print("\n" + "="*55)
    print("  Script 04 — Merge Datasets (Polyvore Only)")
    print("="*55)

    print("\nLoading files...")
    polyvore = load(POLYVORE_LABELED, "Polyvore labeled")

    if not polyvore:
        print("ERROR: Polyvore labeled file missing. Run Script 01 first.")
        return

    # Validate
    print("\nValidating...")
    valid = [o for i, o in enumerate(polyvore) if is_valid(o, i)]
    invalid = len(polyvore) - len(valid)

    if invalid:
        print(f"  Dropped {invalid} invalid outfits")

    print(f"\n  Valid outfits: {len(valid):,}")

    # Remove duplicates
    valid = remove_dupes(valid)

    # Shuffle
    if SHUFFLE:
        random.seed(RANDOM_SEED)
        random.shuffle(valid)
        print(f"  Shuffled (seed={RANDOM_SEED})")

    print_summary(valid)

    # Save
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(FINAL_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(valid, f, indent=2, ensure_ascii=False)

    print(f"\n  [OK] Saved -> {FINAL_OUTPUT}")
    print("\n" + "="*55)
    print("  Script 04 COMPLETE")
    print("  Next → run 05_verify_final_dataset.py")
    print("="*55 + "\n")


if __name__ == "__main__":
    main()
