"""
Script 00 — Explore Datasets
==============================
Run this FIRST before any other script.

This script reads your downloaded datasets and prints exactly what
is inside them — column names, sample rows, JSON structure etc.

It does NOT modify or create any files. It is purely for inspection.

This is important because Kaggle datasets sometimes have slightly
different column names or structures than expected.

Usage:
    python 00_explore_datasets.py

Read the output carefully before running Script 01.
"""

import os
import json
import csv

# ─────────────────────────────────────────────
# CONFIG — paths based on your folder structure
# ─────────────────────────────────────────────
DEEPFASHION_TRAIN_CSV    = "datasets/for_model1/deepfashion2/annotations/train.csv"
DEEPFASHION_TRAIN_IMAGES = "datasets/for_model1/deepfashion2/images/train/"

POLYVORE_TRAIN_JSON      = "datasets/for_model2/metadata/train_no_dup.json"
POLYVORE_IMAGES_TOP      = "datasets/for_model2/images/top/"
POLYVORE_IMAGES_BOTTOM   = "datasets/for_model2/images/bottom/"
POLYVORE_IMAGES_SHOES    = "datasets/for_model2/images/shoes/"

COMPATIBILITY_TRAIN_CSV  = "datasets/for_model2/compatibility/train_clean.csv"


def separator(title=""):
    print("\n" + "="*60)
    if title:
        print(f"  {title}")
        print("="*60)


def check_path_exists(path, label):
    exists = os.path.exists(path)
    status = "✓ EXISTS" if exists else "✗ NOT FOUND"
    print(f"  {status}  {label}")
    print(f"           {path}")
    return exists


def explore_deepfashion_csv():
    separator("DEEPFASHION2 — train.csv")

    if not check_path_exists(DEEPFASHION_TRAIN_CSV, "DeepFashion2 train CSV"):
        print("  Cannot explore — file not found.")
        print("  Make sure you copied train.csv to datasets/for_model1/deepfashion2/annotations/")
        return

    with open(DEEPFASHION_TRAIN_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        rows    = list(reader)

    print(f"\n  Total rows (items): {len(rows):,}")
    print(f"  Total columns:      {len(columns)}")
    print(f"\n  Column names:")
    for i, col in enumerate(columns, 1):
        print(f"    {i:2}. {col}")

    print(f"\n  First 3 rows (sample):")
    for i, row in enumerate(rows[:3], 1):
        print(f"\n  Row {i}:")
        for key, val in row.items():
            print(f"    {key:<25} = {val}")

    # Show unique category values
    if "category_name" in columns:
        categories = list(set(r["category_name"] for r in rows))
        print(f"\n  Unique category_name values ({len(categories)} total):")
        for cat in sorted(categories):
            count = sum(1 for r in rows if r["category_name"] == cat)
            print(f"    {cat:<30} {count:>6,} items")

    if "category_id" in columns:
        cat_ids = list(set(r["category_id"] for r in rows))
        print(f"\n  Unique category_id values: {sorted(cat_ids, key=lambda x: int(x) if x.isdigit() else 0)}")


def explore_deepfashion_images():
    separator("DEEPFASHION2 — Image Folder")

    if not check_path_exists(DEEPFASHION_TRAIN_IMAGES, "DeepFashion2 train images"):
        print("  Cannot explore — folder not found.")
        return

    files = [f for f in os.listdir(DEEPFASHION_TRAIN_IMAGES)
             if f.lower().endswith((".jpg", ".jpeg", ".png"))]

    print(f"\n  Total image files: {len(files):,}")
    print(f"\n  First 5 filenames:")
    for f in sorted(files)[:5]:
        print(f"    {f}")


def explore_polyvore_metadata():
    separator("POLYVORE METADATA — train_no_dup.json")

    if not check_path_exists(POLYVORE_TRAIN_JSON, "Polyvore train JSON"):
        print("  Cannot explore — file not found.")
        print("  Make sure you copied train_no_dup.json to datasets/for_model2/metadata/")
        return

    with open(POLYVORE_TRAIN_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"\n  Data type:         {type(data).__name__}")
    print(f"  Total outfits:     {len(data):,}")

    if isinstance(data, list) and len(data) > 0:
        first = data[0]
        print(f"\n  Keys in each outfit: {list(first.keys())}")

        print(f"\n  First outfit (full):")
        print(json.dumps(first, indent=4))

        print(f"\n  Second outfit (full):")
        print(json.dumps(data[1], indent=4))

        print(f"\n  Third outfit (full):")
        print(json.dumps(data[2], indent=4))

        # Check what name field looks like across many outfits
        print(f"\n  Sample outfit names (first 20):")
        for outfit in data[:20]:
            name = (outfit.get("name") or
                    outfit.get("title") or
                    outfit.get("set_name") or
                    "(no name field found)")
            print(f"    → {name}")

    elif isinstance(data, dict):
        print(f"\n  Top-level keys: {list(data.keys())}")
        print(f"\n  NOTE: This JSON is a dict not a list.")
        print(f"  Script 01 may need adjustment.")
        print(f"  First key sample:")
        first_key = list(data.keys())[0]
        print(json.dumps({first_key: data[first_key]}, indent=4))


def explore_polyvore_images():
    separator("POLYVORE IMAGES — Folder Counts")

    folders_to_check = {
        "top":      POLYVORE_IMAGES_TOP,
        "bottom":   POLYVORE_IMAGES_BOTTOM,
        "shoes":    POLYVORE_IMAGES_SHOES,
        "outwear":  "datasets/for_model2/images/outwear/",
        "dress":    "datasets/for_model2/images/dress/",
        "jumpsuit": "datasets/for_model2/images/jumpsuit/",
    }

    total = 0
    for name, path in folders_to_check.items():
        if os.path.exists(path):
            count = len([f for f in os.listdir(path)
                         if f.lower().endswith((".jpg", ".jpeg", ".png"))])
            total += count
            print(f"  ✓ {name:<12} {count:>6,} images   {path}")
        else:
            print(f"  ✗ {name:<12} NOT FOUND       {path}")

    print(f"\n  Total usable images: {total:,}")


def explore_compatibility_csv():
    separator("COMPATIBILITY CSV — train_clean.csv")

    if not check_path_exists(COMPATIBILITY_TRAIN_CSV, "Compatibility train CSV"):
        print("  Cannot explore — file not found.")
        print("  Make sure you copied train_clean.csv to datasets/for_model2/compatibility/")
        return

    with open(COMPATIBILITY_TRAIN_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        # Handle files with or without headers
        if reader.fieldnames:
            columns = reader.fieldnames
            rows    = list(reader)
            has_header = True
        else:
            rows    = list(reader)
            columns = []
            has_header = False

    print(f"\n  Has header row:    {has_header}")
    print(f"  Total rows:        {len(rows):,}")

    if has_header:
        print(f"  Columns ({len(columns)}):")
        for i, col in enumerate(columns, 1):
            print(f"    {i}. {col}")

        print(f"\n  First 3 rows:")
        for i, row in enumerate(rows[:3], 1):
            print(f"\n  Row {i}: {dict(row)}")

        # Check for label/compatibility column
        label_cols = [c for c in columns if "label" in c.lower() or
                      "compat" in c.lower() or "score" in c.lower()]
        if label_cols:
            print(f"\n  Label/compatibility columns found: {label_cols}")
            for col in label_cols:
                vals = set(r[col] for r in rows[:100])
                print(f"  Unique values in '{col}': {vals}")
    else:
        # No header — show raw rows
        print(f"\n  No header detected. Raw first 3 rows:")
        with open(COMPATIBILITY_TRAIN_CSV, "r") as f:
            for i, line in enumerate(f):
                if i >= 3:
                    break
                print(f"    Row {i+1}: {line.strip()}")


def check_all_paths():
    separator("QUICK PATH CHECK — All Required Files")

    paths = [
        (DEEPFASHION_TRAIN_CSV,    "DeepFashion2 train.csv"),
        (DEEPFASHION_TRAIN_IMAGES, "DeepFashion2 train images/"),
        (POLYVORE_TRAIN_JSON,      "Polyvore train_no_dup.json"),
        (POLYVORE_IMAGES_TOP,      "Polyvore images/top/"),
        (POLYVORE_IMAGES_BOTTOM,   "Polyvore images/bottom/"),
        (POLYVORE_IMAGES_SHOES,    "Polyvore images/shoes/"),
        (COMPATIBILITY_TRAIN_CSV,  "Compatibility train_clean.csv"),
    ]

    all_ok = True
    for path, label in paths:
        ok = check_path_exists(path, label)
        if not ok:
            all_ok = False

    print()
    if all_ok:
        print("  ✓ ALL PATHS FOUND — ready to explore")
    else:
        print("  ✗ SOME PATHS MISSING — fix folder structure before running other scripts")


def main():
    print("\n" + "="*60)
    print("  Script 00 — Explore Datasets")
    print("  This script only reads. It does NOT modify anything.")
    print("="*60)

    # First do quick check
    check_all_paths()

    # Then explore each dataset
    explore_deepfashion_csv()
    explore_deepfashion_images()
    explore_polyvore_metadata()
    explore_polyvore_images()
    explore_compatibility_csv()

    separator("EXPLORATION COMPLETE")
    print("  Read the output above carefully.")
    print("  Key things to note:")
    print("  1. Exact column names in DeepFashion2 CSV")
    print("  2. Exact JSON structure of Polyvore metadata")
    print("  3. Whether outfit names exist and what they look like")
    print("  4. Column names and label values in compatibility CSV")
    print("  5. Image counts in each Polyvore folder")
    print()
    print("  If everything looks correct → run Script 01 next")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
