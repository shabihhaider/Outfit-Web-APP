"""
Script 07 — Preprocess Images for Model 1
=========================================
Reads model1_train.csv, model1_val.csv, model1_test.csv.
For every image:
  - Opens image using PIL
  - Converts to strict RGB (handles RGBA, grayscale, CMYK)
  - Resizes to exactly 256x256 (BILINEAR/LANCZOS)
  - Saves to `processed/model1_images/{category}/{filename}`
  - Drops corrupted images

Outputs new CSVs (`_kag.csv`) pointing to the NEW relative paths, which are
required for the Kaggle training pipeline.

Using `multiprocessing` to drastically speed up resizing over 357k images.
"""

import os
import csv
import glob
from PIL import Image, ImageOps
import multiprocessing as mp
from functools import partial
import tqdm
import uuid

INPUT_DIR = r"e:\Final\datasets\processed"
OUTPUT_DIR = os.path.join(INPUT_DIR, "model1_images")
TARGET_SIZE = (256, 256)

def process_single_image(row, out_base_dir):
    """
    Processes a single image row:
    - Reads absolute image_path
    - Validates, converts, resizes
    - Saves uniquely
    - Returns updated row or None if corrupted
    """
    img_path = row['image_path']
    category = row['category']
    gender = row['gender']
    
    if not os.path.isfile(img_path):
        return None  # Missing file
        
    try:
        with Image.open(img_path) as img:
            # Force load to catch truncation/corruption early
            img.load()
            
            # Convert to RGB (white background for transparent PNGs)
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1]) # Use alpha channel as mask
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Resize
            img = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
            
            # Subdirectory for this category
            cat_dir = os.path.join(out_base_dir, category)
            # Create a unique but consistent filename (prevent overwrites of same-named files from diff datasets)
            base_ext = os.path.splitext(os.path.basename(img_path))
            import hashlib
            path_hash = hashlib.md5(img_path.encode('utf-8')).hexdigest()[:6]
            new_filename = f"{base_ext[0]}_{path_hash}.jpg"
            
            out_file = os.path.join(cat_dir, new_filename)
            img.save(out_file, 'JPEG', quality=95)
            
            # Path relative to processing dir (for Kaggle)
            rel_path = f"model1_images/{category}/{new_filename}"
            
            return {
                'image_path': rel_path,
                'category': category,
                'gender': gender
            }
            
    except Exception as e:
        # Corrupted or unreadable image
        return None

def process_dataset_split(split_name):
    csv_file = os.path.join(INPUT_DIR, f"model1_{split_name}.csv")
    out_csv = os.path.join(INPUT_DIR, f"model1_{split_name}_kag.csv")
    
    if not os.path.exists(csv_file):
        print(f"Skipping {split_name} (CSV not found)")
        return
        
    # Read rows
    rows = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
            
    print(f"\nProcessing {len(rows)} images for '{split_name}' split...")
    
    # Setup multiprocesing pool
    pool = mp.Pool(mp.cpu_count())
    process_func = partial(process_single_image, out_base_dir=OUTPUT_DIR)
    
    valid_rows = []
    corrupted = 0
    
    # We use tracking with imap_unordered for speed
    for result in tqdm.tqdm(pool.imap_unordered(process_func, rows, chunksize=100), total=len(rows)):
        if result is not None:
            valid_rows.append(result)
        else:
            corrupted += 1
            
    pool.close()
    pool.join()
    
    # Save the updated CSV
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['image_path', 'category', 'gender'])
        writer.writeheader()
        writer.writerows(valid_rows)
        
    print(f"  → Saved {len(valid_rows)} valid images to {out_csv}")
    print(f"  → Dropped {corrupted} unreadable/missing images")


def setup_directories():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    categories = ['top', 'bottom', 'outwear', 'shoes', 'dress', 'jumpsuit']
    for cat in categories:
        os.makedirs(os.path.join(OUTPUT_DIR, cat), exist_ok=True)


if __name__ == '__main__':
    print("=====================================================")
    print("  Script 07 — Preprocess Images (Resize & RGB)")
    print("=====================================================")
    print(f"CPU Cores detected: {mp.cpu_count()}")
    setup_directories()
    
    # Process all three splits
    process_dataset_split('train')
    process_dataset_split('val')
    process_dataset_split('test')
    
    print("\n=====================================================")
    print("  PREPROCESSING COMPLETE")
    print("  Ready to zip processed/model1_images/ for Kaggle")
    print("=====================================================")
