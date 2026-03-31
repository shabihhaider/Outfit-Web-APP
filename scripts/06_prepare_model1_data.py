"""
Script 06 — Prepare Model 1 Data
================================
Consolidates all 11 datasets in `for_model1/` into unified CSVs.
Maps original labels to our 6 target categories:
['top', 'bottom', 'outwear', 'shoes', 'dress', 'jumpsuit']

Discards items that map to 'ignore' (e.g., accessories, bags, kids clothing).
Applies gender tags (men/women/unisex) per dataset where known.
Verifies image paths exist.
Splits into train (70%), val (15%), test (15%) with stratification.

Output:
    datasets/processed/model1_train.csv
    datasets/processed/model1_val.csv
    datasets/processed/model1_test.csv
Columns: image_path, category, gender
"""

import os
import csv
import json
import glob
from collections import Counter
from sklearn.model_selection import train_test_split

BASE_DIR = r"e:\Final\datasets\for_model1"
OUTPUT_DIR = r"e:\Final\datasets\processed"

TARGET_CATEGORIES = {'top', 'bottom', 'outwear', 'shoes', 'dress', 'jumpsuit'}

# 1. DeepFashion2 Map (from CSV)
DF2_MAP = {
    'short_sleeve_top': 'top',
    'long_sleeve_top': 'top',
    'short_sleeve_outwear': 'outwear',
    'long_sleeve_outwear': 'outwear',
    'vest': 'top',
    'sling': 'top',
    'shorts': 'bottom',
    'trousers': 'bottom',
    'skirt': 'bottom',
    'short_sleeve_dress': 'dress',
    'long_sleeve_dress': 'dress',
    'vest_dress': 'dress',
    'sling_dress': 'dress'
}

# 2. Indo Fashion Map (from JSON `class_label`)
INDO_MAP = {
    'saree': 'dress',
    'kurta': 'top',
    'women_kurta': 'top',
    'dhoti_pants': 'bottom',
    'palazzos': 'bottom',
    'sherwani': 'outwear',
    'nehru_jackets': 'outwear',
    'blouse': 'top',
    'dupattas': 'ignore',
    'petticoats': 'bottom',
    'leggings': 'bottom',
    'salwar': 'bottom',
    'lehenga': 'dress',
    'mens_kurta': 'top',
    'gowns': 'dress',
    'mojaris_men': 'shoes',
    'mojaris_women': 'shoes'
}

# 3. Carousell Map (from folder names)
CAROUSELL_MAP = {
    'Blazer': 'outwear',
    'Celana_Panjang': 'bottom',
    'Celana_Pendek': 'bottom',
    'Gaun': 'dress',
    'Hoodie': 'outwear',
    'Jaket': 'outwear',
    'Jaket_Denim': 'outwear',
    'Jaket_Olahraga': 'outwear',
    'Jeans': 'bottom',
    'Kaos': 'top',
    'Kemeja': 'top',
    'Mantel': 'outwear',
    'Polo': 'top',
    'Rok': 'bottom',
    'Sweter': 'outwear'
}

# 4. E-Commerce Men's Map (from folder names)
ECOMMERCE_MAP = {
    'casual_shirts': 'top',
    'formal_shirts': 'top',
    'printed_tshirts': 'top',
    'solid_tshirts': 'top',
    'formal_pants': 'bottom',
    'jeans': 'bottom',
    'men_cargos': 'bottom',
    'printed_hoodies': 'outwear'
}

# 5. Pakistani Fashion Map (from folder names)
PAKISTANI_MAP = {
    'ajrak': 'outwear', # Often worn as a shawl/wrapper, mapping to outwear
    'balochi': 'dress', # Traditional balochi dresses are full body
    'kalash': 'dress',
    'shalwarKameez': 'dress' # Represents a full outfit/suit
}

def clean_record(path, category, gender, skip_check=False):
    """Normalize and validate a record."""
    if not path:
        return None
    if not skip_check and not os.path.isfile(path):
        return None
        
    category = str(category).lower().strip()
    if category not in TARGET_CATEGORIES:
        return None
        
    return {'image_path': os.path.abspath(path), 'category': category, 'gender': gender}


def load_deepfashion2():
    records = []
    print("Loading DeepFashion2...")
    ds_dir = os.path.join(BASE_DIR, "deepfashion2")
    for split in ['train', 'validation']:
        csv_path = os.path.join(ds_dir, "annotations", f"{split}.csv")
        img_dir = os.path.join(ds_dir, "images", split)
        if not os.path.exists(csv_path): continue
        if not os.path.exists(img_dir): continue
        
        existing_files = set(os.listdir(img_dir))
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                count += 1
                if count % 20000 == 0: print(f"    ... processed {count} records in {split}", flush=True)
                
                img_name_raw = row.get('path', row.get('image', row.get('file_name', '')))
                if not img_name_raw:
                    img_name_raw = list(row.values())[0] if row else ""
                
                img_name = os.path.basename(img_name_raw.replace('\\', '/'))
                cat_name = row.get('category_name')
                if not cat_name:
                    cat_name = row.get('label') or row.get('class')
                    if not cat_name:
                        for v in row.values():
                            if v in DF2_MAP: cat_name = v; break
                            
                target_cat = DF2_MAP.get(cat_name, 'ignore')
                if target_cat == 'ignore': continue
                
                if img_name not in existing_files and not any(img_name + ext in existing_files for ext in ['.jpg', '.png', '.jpeg']):
                    continue # Skip fast without touching disk
                    
                img_path = os.path.join(img_dir, img_name)
                if not img_path.lower().endswith(('.jpg', '.png', '.jpeg')):
                    img_path += '.jpg'
                    
                rec = clean_record(img_path, target_cat, 'women', skip_check=True)
                if rec: records.append(rec)
    print(f"  → Found {len(records)} usable items")
    return records


def load_indo_fashion():
    records = []
    print("Loading Indo Fashion...")
    ds_dir = os.path.join(BASE_DIR, "Indo fashion dataset")
    for split in ['train', 'val', 'test']:
        json_path = os.path.join(ds_dir, f"{split}_data.json")
        img_split_dir = os.path.join(ds_dir, "images", split)
        if not os.path.exists(json_path): continue
        
        # Indo fashion uses 'images/train', 'images/val', 'images/test' and also flat 'images/'.
        # We'll just collect all files in 'images' and its subdirs into a set of relative paths.
        
        existing_files = set()
        img_base_dir = os.path.join(ds_dir, "images")
        if os.path.exists(img_base_dir):
            for root, _, files in os.walk(img_base_dir):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), ds_dir).replace('\\', '/')
                    existing_files.add(rel_path)
        
        with open(json_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    img_rel = data.get('image_path', '').replace('\\', '/')
                    cat_name = data.get('class_label', '')
                    target_cat = INDO_MAP.get(cat_name, 'ignore')
                    if target_cat == 'ignore': continue
                    
                    if img_rel not in existing_files:
                        continue
                        
                    gender = 'men' if 'men' in cat_name else 'women'
                    if cat_name in ['mojaris_men', 'mens_kurta']: gender = 'men'
                    
                    img_path = os.path.join(ds_dir, img_rel)
                    rec = clean_record(img_path, target_cat, gender, skip_check=True)
                    if rec: records.append(rec)
                except json.JSONDecodeError:
                    pass
    print(f"  → Found {len(records)} usable items")
    return records


def load_folder_dataset(ds_name, folder_map, default_gender, subfolder=""):
    records = []
    print(f"Loading {ds_name}...")
    ds_dir = os.path.join(BASE_DIR, ds_name, subfolder) if subfolder else os.path.join(BASE_DIR, ds_name)
    
    if not os.path.exists(ds_dir):
        print(f"  → Directory missing: {ds_dir}")
        return records
        
    for class_folder, target_cat in folder_map.items():
        if target_cat == 'ignore': continue
        
        cat_dir = os.path.join(ds_dir, class_folder)
        if not os.path.exists(cat_dir): continue
        
        for ext in ('*.jpg', '*.jpeg', '*.png', '*.webp'):
            for img_path in glob.glob(os.path.join(cat_dir, ext)):
                rec = clean_record(img_path, target_cat, default_gender)
                if rec: records.append(rec)
    print(f"  → Found {len(records)} usable items")
    return records


def load_khaadi():
    records = []
    print("Loading Khaadi...")
    csv_path = os.path.join(BASE_DIR, "Khaadi's Clothes Data with Images", "khaadi_data.csv")
    img_dir = os.path.join(BASE_DIR, "Khaadi's Clothes Data with Images", "images")
    if not os.path.exists(csv_path) or not os.path.exists(img_dir): return records
    
    existing_files = {}
    for f in os.listdir(img_dir):
        existing_files[f.split('.')[0].lower()] = f
        
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            img_name = row.get('Img Path', '').split('\\')[-1]
            if not img_name: continue
            base_name = img_name.split('.')[0].lower()
            
            # Khaadi is mostly full suits/dresses and tops
            # Try to infer from Item Type or category
            title = str(row.get('Product Name', row.get('Product Description', ''))).lower()
            if 'suit' in title or 'unstitched' in title or 'piece' in title: target_cat = 'dress'
            elif 'kurta' in title or 'top' in title or 'shirt' in title: target_cat = 'top'
            elif '裤' in title or 'pant' in title or 'trouser' in title: target_cat = 'bottom'
            else: target_cat = 'dress' # Default to dress for 2/3 piece ethnic wear
            
            if base_name in existing_files:
                img_path = os.path.join(img_dir, existing_files[base_name])
                rec = clean_record(img_path, target_cat, 'women', skip_check=True)
                if rec: records.append(rec)
    print(f"  → Found {len(records)} usable items")
    return records


def load_nordstrom():
    records = []
    print("Loading Nordstrom...")
    csv_path = os.path.join(BASE_DIR, "Nordstrom & Myntra Clothes Image Data - GarmentIQ", "metadata.csv")
    img_dir = os.path.join(BASE_DIR, "Nordstrom & Myntra Clothes Image Data - GarmentIQ", "images")
    if not os.path.exists(csv_path) or not os.path.exists(img_dir): return records
    
    existing_files = {}
    for f in os.listdir(img_dir):
        existing_files[f.split('.')[0].lower()] = f
        
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            img_raw = row.get('filename') or row.get('image_name') or row.get('id', '')
            if not img_raw: continue
            base_name = img_raw.split('.')[0].lower()
            
            cat = str(row.get('masterCategory', row.get('garment', ''))).lower()
            gender = str(row.get('gender', 'unisex')).lower()
            
            if 'shirt' in cat or 'top' in cat or 'tee' in cat or 'tank' in cat: target_cat = 'top'
            elif 'pant' in cat or 'jeans' in cat or 'short' in cat or 'skirt' in cat: target_cat = 'bottom'
            elif 'jacket' in cat or 'coat' in cat or 'sweater' in cat or 'blazer' in cat: target_cat = 'outwear'
            elif 'dress' in cat: target_cat = 'dress'
            elif 'shoe' in cat or 'sneaker' in cat or 'boot' in cat: target_cat = 'shoes'
            elif 'jumpsuit' in cat or 'romper' in cat: target_cat = 'jumpsuit'
            else: target_cat = 'ignore'
            
            if target_cat == 'ignore': continue
            
            if base_name in existing_files:
                img_path = os.path.join(img_dir, existing_files[base_name])
                rec = clean_record(img_path, target_cat, gender, skip_check=True)
                if rec: records.append(rec)
    print(f"  → Found {len(records)} usable items")
    return records


def load_inshop():
    records = []
    print("Loading DeepFashion In-shop...")
    df_inshop = os.path.join(BASE_DIR, "DeepFashion_In-shop_Clothes_Retrieval", "img_highres")
    if not os.path.exists(df_inshop): return records
    
    for gender, subdir in [('men', 'MEN'), ('women', 'WOMEN')]:
        gender_dir = os.path.join(df_inshop, subdir)
        if not os.path.exists(gender_dir): continue
        
        for category_folder in os.listdir(gender_dir):
            cat_path = os.path.join(gender_dir, category_folder)
            if not os.path.isdir(cat_path): continue
            
            cat = category_folder.lower()
            if 'shirt' in cat or 'tee' in cat or 'tank' in cat or 'top' in cat: target_cat = 'top'
            elif 'pant' in cat or 'short' in cat or 'skirt' in cat or 'legging' in cat or 'denim' in cat: target_cat = 'bottom'
            elif 'jacket' in cat or 'coat' in cat or 'sweater' in cat or 'cardigan' in cat or 'suiting' in cat: target_cat = 'outwear'
            elif 'dress' in cat: target_cat = 'dress'
            elif 'jumpsuit' in cat or 'romper' in cat: target_cat = 'jumpsuit'
            else: target_cat = 'ignore'
            
            if target_cat == 'ignore': continue
            
            for root, _, files in os.walk(cat_path):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                        rec = clean_record(os.path.join(root, file), target_cat, gender)
                        if rec: records.append(rec)
    print(f"  → Found {len(records)} usable items")
    return records


def load_bridal():
    records = []
    print("Loading Bridal Dress...")
    bridal_dir = os.path.join(BASE_DIR, "Bridal Dress")
    if not os.path.exists(bridal_dir): return records
    
    for sub in ['cloths', 'test_cloths']:
        sub_dir = os.path.join(bridal_dir, sub)
        if not os.path.exists(sub_dir): continue
        
        for root, _, files in os.walk(sub_dir):
            for file in files:
                if file.lower().endswith(('.jpg', '.png', '.jpeg')):
                    rec = clean_record(os.path.join(root, file), 'dress', 'women')
                    if rec: records.append(rec)
    print(f"  → Found {len(records)} usable items")
    return records


def load_fashionable():
    records = []
    print("Loading Fashionable Clothes...")
    fash_dir = os.path.join(BASE_DIR, "Fashionable Clothes", "Data")
    if not os.path.exists(fash_dir): return records
    
    for split in ['train', 'test']:
        split_dir = os.path.join(fash_dir, split)
        if not os.path.exists(split_dir): continue
        
        for folder in os.listdir(split_dir):
            cat_dir = os.path.join(split_dir, folder)
            if not os.path.isdir(cat_dir): continue
            
            gender = 'men' if 'MEN' in folder else 'women'
            cat = folder.lower()
            if 'coat' in cat or 'suit' in cat or 'hood' in cat: target_cat = 'outwear'
            elif 'dress' in cat: target_cat = 'dress'
            else: target_cat = 'ignore'
            
            if target_cat == 'ignore': continue
            
            for file in os.listdir(cat_dir):
                if file.lower().endswith(('.jpg', '.png', '.jpeg')):
                    rec = clean_record(os.path.join(cat_dir, file), target_cat, gender)
                    if rec: records.append(rec)
    print(f"  → Found {len(records)} usable items")
    return records


def load_cc0():
    records = []
    print("Loading Clothing CC0...")
    csv_path = os.path.join(BASE_DIR, "Clothing dataset (full, high resolution)", "images.csv")
    img_dir = os.path.join(BASE_DIR, "Clothing dataset (full, high resolution)", "images_original")
    if not os.path.exists(csv_path) or not os.path.exists(img_dir): return records
    
    existing_files = {}
    for f in os.listdir(img_dir):
        existing_files[f.split('.')[0].lower()] = f
        
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            img_id = row.get('image')
            if not img_id: continue
            base_name = img_id.split('.')[0].lower()
            
            cat = row.get('label', '').lower()
            if 'shirt' in cat or 'top' in cat or 'blouse' in cat: target_cat = 'top'
            elif 'pant' in cat or 'jeans' in cat or 'short' in cat or 'skirt' in cat: target_cat = 'bottom'
            elif 'jacket' in cat or 'coat' in cat or 'hoodie' in cat or 'sweater' in cat: target_cat = 'outwear'
            elif 'dress' in cat: target_cat = 'dress'
            elif 'shoe' in cat: target_cat = 'shoes'
            else: target_cat = 'ignore'
            
            if target_cat == 'ignore': continue
            
            if base_name in existing_files:
                img_path = os.path.join(img_dir, existing_files[base_name])
                rec = clean_record(img_path, target_cat, 'unisex', skip_check=True)
                if rec: records.append(rec)
    print(f"  → Found {len(records)} usable items")
    return records


def main():
    print("="*60)
    print("  Script 06 — Compiling Model 1 Data")
    print("="*60)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    all_records = []
    all_records.extend(load_deepfashion2())
    all_records.extend(load_indo_fashion())
    all_records.extend(load_folder_dataset("Clothes Dataset (Carousell)", CAROUSELL_MAP, "unisex"))
    all_records.extend(load_folder_dataset("E-Commerce Men’s Clothing Dataset", ECOMMERCE_MAP, "men", subfolder="dataset_clean"))
    all_records.extend(load_folder_dataset("Pakistani Cultural Clothes", PAKISTANI_MAP, "unisex", subfolder="data"))
    all_records.extend(load_khaadi())
    all_records.extend(load_nordstrom())
    all_records.extend(load_inshop())
    all_records.extend(load_bridal())
    all_records.extend(load_fashionable())
    all_records.extend(load_cc0())
    
    if not all_records:
        print("ERROR: No valid records found! Check paths.")
        return
        
    print("\n--- Summary Statistics ---")
    print(f"Total Combined Images: {len(all_records):,}")
    
    cat_counts = Counter(r['category'] for r in all_records)
    print("Category Breakdown:")
    for k, v in cat_counts.most_common():
        print(f"  {k}: {v:,}")
        
    # Split
    print("\nSplitting Train (70%) / Val (15%) / Test (15%)...")
    
    X = all_records
    y = [r['category'] for r in all_records]
    
    try:
        # Train and Temp (30%)
        X_train, X_temp, _, y_temp = train_test_split(X, y, test_size=0.3, stratify=y, random_state=42)
        # Val (15%) and Test (15%)
        X_val, X_test = train_test_split(X_temp, test_size=0.5, stratify=y_temp, random_state=42)
    except ValueError as e:
        print(f"WARNING: Stratification failed ({e}). Falling back to random split.")
        X_train, X_temp = train_test_split(X, test_size=0.3, random_state=42)
        X_val, X_test = train_test_split(X_temp, test_size=0.5, random_state=42)
        
    print(f"  Train: {len(X_train):,} images")
    print(f"  Val:   {len(X_val):,} images")
    print(f"  Test:  {len(X_test):,} images")
    
    # Save
    def save_csv(records, filename):
        path = os.path.join(OUTPUT_DIR, filename)
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['image_path', 'category', 'gender'])
            writer.writeheader()
            writer.writerows(records)
        print(f"Saved: {path}")

    save_csv(X_train, 'model1_train.csv')
    save_csv(X_val, 'model1_val.csv')
    save_csv(X_test, 'model1_test.csv')
    
    print("\n============================================================")
    print("  DONE! Next step: python scripts/07_preprocess_images.py")
    print("============================================================")

if __name__ == "__main__":
    main()
