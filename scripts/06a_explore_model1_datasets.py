"""
Script 06a — Explore Model 1 Datasets
=====================================
Crucial exploration script to safely determine the exact structure,
CSV column names, and unique label values for all 11 datasets in `for_model1/`.
Run this to gather facts before writing the actual data preparation script.
"""

import os
import csv
import json
from collections import Counter

BASE_DIR = r"e:\Final\datasets\for_model1"

def print_header(title):
    print(f"\n{'='*70}")
    print(f"  {title.upper()}")
    print(f"{'='*70}")

def explore_csv(filepath, name):
    if not os.path.exists(filepath):
        print(f"  [!] Missing CSV: {filepath}")
        return
    
    print(f"\n--- {name} ---")
    print(f"Path: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
            print(f"Columns: {', '.join(header)}")
            rows = []
            for _ in range(3):
                try:
                    rows.append(next(reader))
                except StopIteration:
                    break
            print("Sample Rows:")
            for row in rows:
                print(f"  {row}")
        except StopIteration:
            print("  [!] Empty CSV")

def explore_json(filepath, name):
    if not os.path.exists(filepath):
        print(f"  [!] Missing JSON: {filepath}")
        return
    
    print(f"\n--- {name} ---")
    print(f"Path: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            # Fallback to JSONL
            f.seek(0)
            data = [json.loads(line) for line in f if line.strip()]
            
        if isinstance(data, list) and len(data) > 0:
            print(f"Format: List of {len(data)} dicts")
            print(f"Keys: {list(data[0].keys())}")
            print(f"Sample: {data[0]}")
            
            # Check for "class_label" or similar keys
            label_key = next((k for k in data[0].keys() if "class" in k.lower() or "label" in k.lower() or "category" in k.lower()), None)
            if label_key:
                labels = Counter(item.get(label_key) for item in data)
                print(f"\nUnique values for '{label_key}':")
                for k, v in labels.most_common(10):
                    print(f"  - {k}: {v}")
                if len(labels) > 10:
                    print(f"  ... and {len(labels)-10} more")
        else:
            print("Format: Unknown or empty")

def explore_folders(dirpath, name):
    if not os.path.exists(dirpath):
        print(f"  [!] Missing Directory: {dirpath}")
        return
    
    print(f"\n--- {name} ---")
    print(f"Path: {dirpath}")
    
    subdirs = [d for d in os.listdir(dirpath) if os.path.isdir(os.path.join(dirpath, d))]
    print(f"Subdirectories ({len(subdirs)}):")
    for d in sorted(subdirs)[:15]:
        count = len([f for f in os.listdir(os.path.join(dirpath, d)) if os.path.isfile(os.path.join(dirpath, d, f))])
        print(f"  - {d}/  ({count} files)")
    if len(subdirs) > 15:
        print(f"  ... and {len(subdirs)-15} more")

def main():
    print_header("Exploring Model 1 Datasets")
    
    # 1. DeepFashion2
    explore_csv(os.path.join(BASE_DIR, "deepfashion2", "annotations", "train.csv"), "DeepFashion2 (Train CSV)")
    
    # 2. Indo Fashion
    explore_json(os.path.join(BASE_DIR, "Indo fashion dataset", "train_data.json"), "Indo Fashion (Train JSON)")
    
    # 3. E-Commerce Men's
    explore_folders(os.path.join(BASE_DIR, "E-Commerce Men’s Clothing Dataset", "dataset_clean"), "E-Commerce Men's (Folders)")
    
    # 4. Pakistani Cultural
    explore_folders(os.path.join(BASE_DIR, "Pakistani Cultural Clothes", "data"), "Pakistani Cultural (Folders)")
    
    # 5. Khaadi
    explore_csv(os.path.join(BASE_DIR, "Khaadi's Clothes Data with Images", "khaadi_data.csv"), "Khaadi (CSV)")
    
    # 6. Nordstrom & Myntra
    explore_csv(os.path.join(BASE_DIR, "Nordstrom & Myntra Clothes Image Data - GarmentIQ", "metadata.csv"), "Nordstrom & Myntra (CSV)")
    
    # 7. Clothes Carousell
    explore_folders(os.path.join(BASE_DIR, "Clothes Dataset (Carousell)"), "Clothes Carousell (Folders)")
    
    # 8. Fashionable Clothes
    explore_folders(os.path.join(BASE_DIR, "Fashionable Clothes", "Data", "train"), "Fashionable Clothes (Folders)")
    
    # 9. DeepFashion In-shop
    df_inshop = os.path.join(BASE_DIR, "DeepFashion_In-shop_Clothes_Retrieval", "img_highres")
    print(f"\n--- DeepFashion In-shop ---")
    if os.path.exists(df_inshop):
        men_path = os.path.join(df_inshop, "MEN")
        if os.path.exists(men_path):
            print(f"MEN subdirs: {', '.join(os.listdir(men_path)[:10])}")
        women_path = os.path.join(df_inshop, "WOMEN")
        if os.path.exists(women_path):
            print(f"WOMEN subdirs: {', '.join(os.listdir(women_path)[:10])}")
    
    # 10. Bridal Dress
    explore_folders(os.path.join(BASE_DIR, "Bridal Dress"), "Bridal Dress (Folders)")
    
    # 11. Clothing Dataset CC0
    explore_csv(os.path.join(BASE_DIR, "Clothing dataset (full, high resolution)", "images.csv"), "Clothing CC0 (CSV)")

if __name__ == "__main__":
    main()
