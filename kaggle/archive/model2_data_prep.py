"""
PHASE 3: Model 2 Data Preparation — v2
========================================
Extracts 1280-dim embeddings from Polyvore images using Model 1's
embedding extractor, then assembles 5123-dim input vectors for the
MLP compatibility scorer.

Vector layout: [top_1280 + bottom_1280 + outwear_1280 + shoes_1280 + occasion_3]
               = 5123 dimensions per outfit

Key fix in v2: Builds item lookup from IMAGE FILES ON DISK instead of
metadata JSONs. The metadata JSONs only cover ~5% of the outfit IDs in
the compatibility CSVs (different Polyvore snapshots). Scanning the
filesystem recovers ~95% of previously lost data.

Kaggle Setup:
  1. Upload model1_embedding_extractor.h5 as a Kaggle dataset
  2. Upload datasets.zip containing: for_model2/ and processed/final_dataset.json
  3. Paste this entire script into a Kaggle notebook cell and run
"""

import os
import json
import ast
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import load_model

print("=" * 60)
print("  PHASE 3: MODEL 2 DATA PREPARATION (v2)")
print("  Vector: top + bottom + outwear + shoes + occasion = 5123-dim")
print("=" * 60)

# ─── 1. PATH RESOLUTION ─────────────────────────────────────────
dataset_root = '/kaggle/input'
found_for_model2 = None
found_processed = None

for root, dirs, files in os.walk(dataset_root):
    if 'for_model2' in dirs and found_for_model2 is None:
        found_for_model2 = os.path.join(root, 'for_model2')
    if 'processed' in dirs:
        candidate = os.path.join(root, 'processed')
        if os.path.exists(os.path.join(candidate, 'final_dataset.json')):
            found_processed = candidate

if not found_for_model2 or not found_processed:
    print(f"\n[ERROR] Could not find 'for_model2' or 'processed' in {dataset_root}")
    print("FIX: Make sure datasets.zip contains both folders.")
    raise FileNotFoundError("Missing dataset folders on Kaggle.")

MODEL2_DIR = found_for_model2
CSV_DIR = os.path.join(MODEL2_DIR, "compatibility")
IMG_DIR = os.path.join(MODEL2_DIR, "images")
JSON_PATH = os.path.join(found_processed, "final_dataset.json")

# Find embedding extractor
EXTRACTOR_PATH = "/kaggle/working/model1_embedding_extractor.h5"
if not os.path.exists(EXTRACTOR_PATH):
    for root, dirs, files in os.walk(dataset_root):
        if 'model1_embedding_extractor.h5' in files:
            EXTRACTOR_PATH = os.path.join(root, 'model1_embedding_extractor.h5')
            break

if not os.path.exists(EXTRACTOR_PATH):
    print("\n[ERROR] Could not find model1_embedding_extractor.h5")
    print("FIX: Upload it as a Kaggle dataset, or run Model 1 training first.")
    raise FileNotFoundError("Missing Model 1 embedding extractor.")

print(f"Model 2 Dir:  {MODEL2_DIR}")
print(f"Processed:    {found_processed}")
print(f"Extractor:    {EXTRACTOR_PATH}")

# ─── 2. BUILD ITEM LOOKUP FROM IMAGE FILES ON DISK ──────────────
# Instead of relying on metadata JSONs (which only cover ~5% of
# compatibility CSV outfit IDs), scan the actual image folders.
# Each folder name IS the category. Each filename is {outfit_id}_{item_index}.jpg.
print("\nBuilding item lookup from image files on disk...")

CATEGORIES = ["top", "bottom", "outwear", "shoes", "dress", "jumpsuit"]
item_lookup = {}

for cat in CATEGORIES:
    cat_dir = os.path.join(IMG_DIR, cat)
    if not os.path.isdir(cat_dir):
        print(f"  [WARN] Category folder not found: {cat_dir}")
        continue
    count = 0
    for fname in os.listdir(cat_dir):
        if not fname.endswith(".jpg"):
            continue
        item_id = fname[:-4]  # strip .jpg -> e.g. "199244701_1"
        item_lookup[item_id] = {
            "category": cat,
            "image_path": os.path.join(cat_dir, fname),
        }
        count += 1
    print(f"  {cat}: {count:,} images")

print(f"  Total items in lookup: {len(item_lookup):,}")

# Load occasion labels from final_dataset.json (where available)
with open(JSON_PATH, "r") as f:
    occasion_data = json.load(f)
outfit_occasion_map = {outfit["outfit_id"]: outfit["occasion"] for outfit in occasion_data}
print(f"  Occasion labels available for: {len(outfit_occasion_map):,} outfits")

# ─── 3. PARSE COMPATIBILITY CSVs ────────────────────────────────
def get_outfit_id(item_id):
    """Extract outfit_id prefix from item_id like '199244701_1' -> '199244701'."""
    return item_id.rsplit("_", 1)[0]

def process_csv(csv_path):
    """Extract image paths for 4 slots: top, bottom, outwear, shoes."""
    print(f"\nParsing {os.path.basename(csv_path)}...")
    df = pd.read_csv(csv_path)

    top_paths, bottom_paths, outwear_paths, shoe_paths = [], [], [], []
    occasions, labels = [], []
    skipped_no_images = 0
    skipped_no_clothing = 0

    for _, row in df.iterrows():
        item_ids = ast.literal_eval(row['item_ids'])
        label = int(row['label'])

        t_img, b_img, o_img, s_img = None, None, None, None

        # Get occasion from outfit_id (use first item's prefix)
        outfit_id = get_outfit_id(item_ids[0]) if item_ids else None
        occ = outfit_occasion_map.get(outfit_id, "casual")

        # Assign each item to its correct slot
        found_any = False
        for item_id in item_ids:
            if item_id not in item_lookup:
                continue
            found_any = True
            cat = item_lookup[item_id]["category"]
            img = item_lookup[item_id]["image_path"]

            if cat == "top" and t_img is None:
                t_img = img
            elif cat == "bottom" and b_img is None:
                b_img = img
            elif cat == "outwear" and o_img is None:
                o_img = img
            elif cat == "shoes" and s_img is None:
                s_img = img
            elif cat == "dress" and t_img is None:
                # Dress replaces top+bottom (full-body garment)
                t_img = img
                b_img = img
            elif cat == "jumpsuit" and t_img is None:
                # Jumpsuit also replaces top+bottom
                t_img = img
                b_img = img

        if not found_any:
            skipped_no_images += 1
            continue

        # Must have at least a top or a bottom
        if t_img is None and b_img is None:
            skipped_no_clothing += 1
            continue

        occ_idx = {"casual": 0, "formal": 1, "wedding": 2}.get(occ, 0)

        top_paths.append(t_img)
        bottom_paths.append(b_img)
        outwear_paths.append(o_img)
        shoe_paths.append(s_img)
        occasions.append(occ_idx)
        labels.append(label)

    kept = len(labels)
    total = len(df)
    print(f"  Kept: {kept:,} / {total:,} ({kept/total*100:.1f}%)")
    if skipped_no_images > 0:
        print(f"  Skipped (no images found on disk): {skipped_no_images:,}")
    if skipped_no_clothing > 0:
        print(f"  Skipped (no top or bottom): {skipped_no_clothing:,}")

    return top_paths, bottom_paths, outwear_paths, shoe_paths, occasions, labels

print("\n" + "-" * 60)
print("Processing compatibility CSVs...")
print("-" * 60)

tr_t, tr_b, tr_o, tr_s, tr_occ, tr_y = process_csv(os.path.join(CSV_DIR, "train_clean.csv"))
v_t, v_b, v_o, v_s, v_occ, v_y       = process_csv(os.path.join(CSV_DIR, "validation_clean.csv"))
te_t, te_b, te_o, te_s, te_occ, te_y = process_csv(os.path.join(CSV_DIR, "test_clean.csv"))

total_kept = len(tr_y) + len(v_y) + len(te_y)
total_rows = 33990 + 6000 + 30290
print(f"\nOverall: {total_kept:,} / {total_rows:,} pairs retained ({total_kept/total_rows*100:.1f}%)")

if total_kept < 5000:
    print("\n[WARN] Less than 5,000 training pairs. Model may underperform.")
    print("This likely means many CSV item IDs have no matching images on disk.")

# ─── 4. EXTRACT EMBEDDINGS ──────────────────────────────────────
print("\n" + "-" * 60)
print("Loading embedding extractor...")
print("-" * 60)
embedding_model = load_model(EXTRACTOR_PATH)

# Determine embedding dimensionality from the model
dummy_input = np.zeros((1, 256, 256, 3), dtype=np.float32)
EMB_DIM = embedding_model.predict(dummy_input, verbose=0).shape[1]
print(f"Embedding dimensionality: {EMB_DIM}")
EXPECTED_VECTOR_DIM = EMB_DIM * 4 + 3  # 4 slots + occasion one-hot
print(f"Expected output vector: {EMB_DIM}*4 + 3 = {EXPECTED_VECTOR_DIM}-dim")

# Collect all unique image paths across all splits
all_paths = tr_t + tr_b + tr_o + tr_s + v_t + v_b + v_o + v_s + te_t + te_b + te_o + te_s
unique_paths = sorted(set(p for p in all_paths if p is not None and os.path.exists(p)))
print(f"\nUnique images to process: {len(unique_paths):,}")

# Check for missing files
all_referenced = set(p for p in all_paths if p is not None)
missing = [p for p in all_referenced if not os.path.exists(p)]
if missing:
    print(f"[WARN] {len(missing)} referenced images not found on disk")
    for m in list(missing)[:3]:
        print(f"  {m}")

def decode_img(path):
    img = tf.io.read_file(path)
    img = tf.image.decode_jpeg(img, channels=3)
    img = tf.image.resize(img, [256, 256])
    img = tf.cast(img, tf.float32)
    return img

path_ds = tf.data.Dataset.from_tensor_slices(unique_paths)
img_ds = path_ds.map(decode_img, num_parallel_calls=tf.data.AUTOTUNE).batch(128).prefetch(tf.data.AUTOTUNE)

print("Extracting embeddings (GPU)...")
embeddings_raw = embedding_model.predict(img_ds, verbose=1)
print(f"Extracted: {embeddings_raw.shape}")

# Build path -> embedding lookup
emb_dict = {path: emb for path, emb in zip(unique_paths, embeddings_raw)}

# ─── 5. ASSEMBLE VECTORS AND SAVE ───────────────────────────────
ZERO_EMB = np.zeros(EMB_DIM, dtype=np.float32)

def build_npz(t_list, b_list, o_list, s_list, occ_list, y_list, filename):
    """Build NPZ with 4-slot architecture: top + bottom + outwear + shoes + occasion."""
    print(f"\nAssembling {os.path.basename(filename)}...")
    X, y = [], []
    skipped = 0

    for i in range(len(y_list)):
        if t_list[i] is None and b_list[i] is None:
            skipped += 1
            continue

        t_emb = emb_dict.get(t_list[i], ZERO_EMB) if t_list[i] else ZERO_EMB
        b_emb = emb_dict.get(b_list[i], ZERO_EMB) if b_list[i] else ZERO_EMB
        o_emb = emb_dict.get(o_list[i], ZERO_EMB) if o_list[i] else ZERO_EMB
        s_emb = emb_dict.get(s_list[i], ZERO_EMB) if s_list[i] else ZERO_EMB

        occ_vec = np.zeros(3, dtype=np.float32)
        occ_vec[occ_list[i]] = 1.0

        # [top_1280 | bottom_1280 | outwear_1280 | shoes_1280 | occasion_3] = 5123-dim
        fused = np.concatenate([t_emb, b_emb, o_emb, s_emb, occ_vec])
        X.append(fused)
        y.append(y_list[i])

    if skipped > 0:
        print(f"  Skipped {skipped} pairs (no top or bottom)")

    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.float32)
    np.savez_compressed(filename, X=X, y=y)
    print(f"  Saved: X.shape={X.shape}, y.shape={y.shape}")

    # Verify dimension
    assert X.shape[1] == EXPECTED_VECTOR_DIM, \
        f"Dimension mismatch! Got {X.shape[1]}, expected {EXPECTED_VECTOR_DIM}"

    # Label distribution
    unique, counts = np.unique(y, return_counts=True)
    for val, cnt in zip(unique, counts):
        label_name = "Compatible" if val == 1 else "Incompatible"
        print(f"  {label_name}: {cnt:,} ({cnt / len(y) * 100:.1f}%)")

build_npz(tr_t, tr_b, tr_o, tr_s, tr_occ, tr_y, "/kaggle/working/model2_train.npz")
build_npz(v_t, v_b, v_o, v_s, v_occ, v_y, "/kaggle/working/model2_val.npz")
build_npz(te_t, te_b, te_o, te_s, te_occ, te_y, "/kaggle/working/model2_test.npz")

print("\n" + "=" * 60)
print("  DATA PREP COMPLETE")
print(f"  Vector dimension: {EXPECTED_VECTOR_DIM}")
print("  Files saved in /kaggle/working/")
print("  Next: Run the Model 2 MLP training script")
print("=" * 60)
