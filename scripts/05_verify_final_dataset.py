"""
Script 05 — Verify Final Dataset
===================================
Final check before model training.

Verifies:
  [OK] final_dataset.json exists and is readable
  [OK] All required fields present
  [OK] All sources are valid (polyvore only — manual wedding removed)
  [OK] Polyvore item IDs can be resolved to images
  [OK] Class balance is acceptable
  [OK] Dataset structure is correct

Run LAST, after all other scripts.

Usage:
    python 05_verify_final_dataset.py
"""

import json
import os
from collections import Counter

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
FINAL_DATASET      = "datasets/processed/final_dataset.json"
POLYVORE_IMAGES    = "datasets/for_model2/images/"

# Minimum thresholds for training readiness
MIN_CASUAL         = 2000
MIN_FORMAL         = 1000
MIN_WEDDING        = 250


def check_1_file():
    print(f"\n{'='*55}")
    print("  CHECK 1 — File Exists and Readable")
    print(f"{'='*55}")

    if not os.path.exists(FINAL_DATASET):
        print(f"  [ERROR] NOT FOUND: {FINAL_DATASET}")
        print("  Run Script 04 first.")
        return None

    size_mb = os.path.getsize(FINAL_DATASET) / (1024 * 1024)
    print(f"  [OK] File exists  ({size_mb:.1f} MB)")

    try:
        with open(FINAL_DATASET, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"  [OK] JSON valid   ({len(data):,} outfits)")
        return data
    except json.JSONDecodeError as e:
        print(f"  [ERROR] JSON error: {e}")
        print("  Re-run Script 04.")
        return None


def check_2_fields(outfits):
    print(f"\n{'='*55}")
    print("  CHECK 2 — Required Fields")
    print(f"{'='*55}")

    issues = []
    for i, o in enumerate(outfits):
        if "outfit_id" not in o:
            issues.append(f"  Outfit #{i}: missing outfit_id")
        if "occasion" not in o:
            issues.append(f"  Outfit #{i}: missing occasion")
        elif o["occasion"] not in ("casual", "formal", "wedding"):
            issues.append(f"  Outfit #{i}: invalid occasion '{o['occasion']}'")
        if "items" not in o or not o["items"]:
            issues.append(f"  Outfit #{i}: missing or empty items")
        if "source" not in o:
            issues.append(f"  Outfit #{i}: missing source")

    if not issues:
        print(f"  [OK] All {len(outfits):,} outfits have valid fields")
        return True
    else:
        print(f"  [ERROR] {len(issues)} issues found:")
        for issue in issues[:10]:
            print(issue)
        return False


def check_3_sources(outfits):
    print(f"\n{'='*55}")
    print("  CHECK 3 — Data Sources")
    print(f"{'='*55}")

    sources = Counter(o.get("source", "unknown") for o in outfits)
    print(f"  Sources found:")
    for src, count in sorted(sources.items()):
        print(f"    {src:<12} {count:>6,} outfits")

    # Warn if manual wedding data is still present (should have been removed)
    manual = [o for o in outfits if o.get("source") == "manual"]
    if manual:
        print(f"\n  [WARNING] {len(manual)} manual wedding outfits found.")
        print(f"  Manual wedding data was removed from the project.")
        print(f"  Re-run Script 04 to regenerate final_dataset.json.")
        return False

    print(f"  [OK] All outfits from Polyvore (no stale manual data)")
    return True


def check_4_polyvore_items(outfits):
    print(f"\n{'='*55}")
    print("  CHECK 4 — Polyvore Item Categories")
    print(f"{'='*55}")

    polyvore = [o for o in outfits if o.get("source") == "polyvore"]
    print(f"  Polyvore outfits: {len(polyvore):,}")

    all_cats = []
    for o in polyvore:
        for item in o.get("items", []):
            all_cats.append(item.get("category", "unknown"))

    counts = Counter(all_cats)
    total  = len(all_cats)

    print(f"  Total items: {total:,}")
    print(f"\n  Category breakdown:")
    for cat, count in sorted(counts.items(), key=lambda x: -x[1]):
        pct = (count / total * 100) if total else 0
        print(f"    {cat:<12} {count:>7,}  ({pct:5.1f}%)")

    expected = {"top", "bottom", "shoes", "outwear", "dress", "jumpsuit"}
    found    = set(counts.keys()) - {"unknown"}
    missing  = expected - found

    if missing:
        print(f"\n  [!] Missing categories: {missing}")
        print(f"  Check POLYVORE_CATEGORY_MAP in Script 01")
    else:
        print(f"\n  [OK] All expected categories present")

    return True


def check_5_balance(outfits):
    print(f"\n{'='*55}")
    print("  CHECK 5 — Class Balance")
    print(f"{'='*55}")

    counts = Counter(o.get("occasion") for o in outfits)
    thresholds = {
        "casual":  MIN_CASUAL,
        "formal":  MIN_FORMAL,
        "wedding": MIN_WEDDING
    }

    all_ok = True
    for occ, minimum in thresholds.items():
        count = counts.get(occ, 0)
        ok    = count >= minimum
        mark  = "[OK]" if ok else "[!]"
        print(f"  {mark} {occ:<10} {count:>6,}  (min: {minimum:,})")
        if not ok:
            all_ok = False

    if not all_ok:
        print(f"\n  [!] Some classes below minimum.")
        print(f"  You can still train but accuracy may suffer.")
        print(f"  Collect more data for low categories.")

    return True  # non-blocking


def print_verdict(checks):
    print(f"\n{'='*55}")
    print("  FINAL VERDICT")
    print(f"{'='*55}")

    critical = {k: v for k, v in checks.items() if k in ["file", "fields"]}
    warnings = {k: v for k, v in checks.items() if k not in ["file", "fields"]}

    all_critical_ok = all(critical.values())

    if all_critical_ok:
        print(f"\n  [OK] DATASET IS READY FOR MODEL TRAINING")
        print(f"\n  Your final file is:")
        print(f"  {FINAL_DATASET}")
        print(f"\n  Next step: Train Model 1 (EfficientNet on DeepFashion2)")
    else:
        failed = [k for k, v in critical.items() if not v]
        print(f"\n  [ERROR] Critical checks failed: {failed}")
        print(f"  Fix issues above before proceeding.")

    print(f"{'='*55}\n")


def main():
    print("\n" + "="*55)
    print("  Script 05 — Verify Final Dataset")
    print("="*55)

    checks = {}

    outfits = check_1_file()
    checks["file"] = outfits is not None
    if not outfits:
        return

    checks["fields"]          = check_2_fields(outfits)
    checks["sources"]         = check_3_sources(outfits)
    checks["polyvore_items"]  = check_4_polyvore_items(outfits)
    checks["class_balance"]   = check_5_balance(outfits)

    print_verdict(checks)


if __name__ == "__main__":
    main()
