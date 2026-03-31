"""
PHASE 3: Model 2 Data Preparation — v3 (Pairwise)
===================================================
Uses the NEW Polyvore dataset (polyvore-processed-images-512 + polyvore-manifests-both)
to build pairwise compatibility vectors for the MLP scorer.

Vector layout: [item_a_emb(1280) + item_b_emb(1280) + cat_a(5) + cat_b(5)] = 2570-dim

Kaggle Setup:
  1. Add dataset: polyvore-processed-images-512 (contains images/train/, images/val/, images/test/)
  2. Add dataset: polyvore-manifests-both (contains manifests_disjoint/)
  3. Add dataset: model1-embedding-extractor (contains model1_embedding_extractor.h5)
  4. Enable GPU accelerator
  5. Paste this entire script into a Kaggle notebook cell and run
"""

import os
import sys
import csv
import time
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model

# ─── PROGRESS TRACKER ────────────────────────────────────────────
class Progress:
    """Simple progress tracker that prints percentage completion."""
    def __init__(self, total, desc="Processing", bar_len=30):
        self.total = total
        self.desc = desc
        self.bar_len = bar_len
        self.current = 0
        self.start_time = time.time()
        self._last_print = -1

    def update(self, n=1):
        self.current += n
        pct = int(self.current / self.total * 100) if self.total > 0 else 100
        if pct != self._last_print:  # only print on % change
            self._last_print = pct
            filled = int(self.bar_len * self.current / self.total)
            bar = "█" * filled + "░" * (self.bar_len - filled)
            elapsed = time.time() - self.start_time
            if self.current > 0 and self.current < self.total:
                eta = elapsed / self.current * (self.total - self.current)
                eta_str = f"ETA {eta:.0f}s"
            else:
                eta_str = f"{elapsed:.1f}s"
            print(f"\r  {self.desc}: |{bar}| {pct:3d}% ({self.current:,}/{self.total:,}) {eta_str}  ", end="", flush=True)

    def done(self):
        elapsed = time.time() - self.start_time
        bar = "█" * self.bar_len
        print(f"\r  {self.desc}: |{bar}| 100% ({self.total:,}/{self.total:,}) Done in {elapsed:.1f}s  ")


SCRIPT_START = time.time()

def phase(num, total, desc):
    elapsed = time.time() - SCRIPT_START
    pct = int(num / total * 100)
    print(f"\n{'='*60}")
    print(f"  STEP {num}/{total} — {desc}  [{pct}% overall | {elapsed:.0f}s elapsed]")
    print(f"{'='*60}")

TOTAL_STEPS = 8

print("=" * 60)
print("  PHASE 3: MODEL 2 DATA PREPARATION (v3 — Pairwise)")
print("  Vector: item_a(1280) + item_b(1280) + cat_a(5) + cat_b(5) = 2570-dim")
print("=" * 60)

# ─── STEP 1/8: PATH RESOLUTION ──────────────────────────────────
phase(1, TOTAL_STEPS, "PATH RESOLUTION")

dataset_root = '/kaggle/input'

# Find images directory
IMG_DIR = None
for root, dirs, files in os.walk(dataset_root):
    if 'images' in dirs:
        candidate = os.path.join(root, 'images')
        if os.path.isdir(os.path.join(candidate, 'train')):
            IMG_DIR = candidate
            break

# Find manifests directory
MANIFEST_DIR = None
for root, dirs, files in os.walk(dataset_root):
    if 'manifests_disjoint' in dirs:
        MANIFEST_DIR = os.path.join(root, 'manifests_disjoint')
        break

# Find embedding extractor
EXTRACTOR_PATH = None
for root, dirs, files in os.walk(dataset_root):
    if 'model1_embedding_extractor.h5' in files:
        EXTRACTOR_PATH = os.path.join(root, 'model1_embedding_extractor.h5')
        break

# Validate all paths found
errors = []
if not IMG_DIR:
    errors.append("Could not find images/ directory with train/val/test subfolders")
if not MANIFEST_DIR:
    errors.append("Could not find manifests_disjoint/ directory")
if not EXTRACTOR_PATH:
    errors.append("Could not find model1_embedding_extractor.h5")

if errors:
    print("\n  [ERROR] Missing required data:")
    for e in errors:
        print(f"    - {e}")
    print("\n  Required Kaggle datasets:")
    print("    1. polyvore-processed-images-512")
    print("    2. polyvore-manifests-both")
    print("    3. model1-embedding-extractor")
    raise FileNotFoundError("Missing required datasets on Kaggle.")

print(f"  Images dir:   {IMG_DIR}")
print(f"  Manifests:    {MANIFEST_DIR}")
print(f"  Extractor:    {EXTRACTOR_PATH}")

# Verify image folders exist
for split in ['train', 'val', 'test']:
    split_dir = os.path.join(IMG_DIR, split)
    count = len([f for f in os.listdir(split_dir) if f.endswith('.jpg')])
    print(f"    {split}/: {count:,} images")
print("  [OK] All paths resolved")

# ─── STEP 2/8: CATEGORY MAPPING ─────────────────────────────────
phase(2, TOTAL_STEPS, "CATEGORY MAPPING")

CATEGORY_MAP = {
    'tops': 'top',
    'bottoms': 'bottom',
    'outerwear': 'outwear',
    'shoes': 'shoes',
    'all-body': 'dress',
}
EXCLUDED_CATS = {'jewellery', 'accessories', 'hats'}
CAT_ORDER = ['bottom', 'dress', 'outwear', 'shoes', 'top']
CAT_TO_IDX = {cat: i for i, cat in enumerate(CAT_ORDER)}
NUM_CATS = len(CAT_ORDER)

print(f"  Valid categories: {CAT_ORDER}")
print(f"  Excluded: {EXCLUDED_CATS}")
print("  [OK] Category mapping ready")

# ─── STEP 3/8: BUILD ITEM LOOKUP ────────────────────────────────
phase(3, TOTAL_STEPS, "BUILD ITEM LOOKUP")

item_category = {}
items_total = 0
items_valid = 0

for split in ['train', 'val', 'test']:
    csv_path = os.path.join(MANIFEST_DIR, f'items_{split}.csv')
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            items_total += 1
            orig_cat = row['category']
            if orig_cat in CATEGORY_MAP:
                item_category[row['image_path']] = CATEGORY_MAP[orig_cat]
                items_valid += 1

print(f"  Total items scanned: {items_total:,}")
print(f"  Items with valid categories: {items_valid:,} ({items_valid/items_total*100:.1f}%)")

cat_counts = {}
for cat in item_category.values():
    cat_counts[cat] = cat_counts.get(cat, 0) + 1
for cat in CAT_ORDER:
    print(f"    {cat}: {cat_counts.get(cat, 0):,}")
print("  [OK] Item lookup built")

# ─── STEP 4/8: FILTER PAIRS ─────────────────────────────────────
phase(4, TOTAL_STEPS, "FILTER PAIRS TO VALID CATEGORIES")

def count_csv_rows(path):
    with open(path, encoding='utf-8') as f:
        return sum(1 for _ in f) - 1  # minus header

def load_filtered_pairs(split):
    csv_path = os.path.join(MANIFEST_DIR, f'pairs_{split}.csv')
    total_rows = count_csv_rows(csv_path)
    img_a_list, img_b_list, cat_a_list, cat_b_list, labels = [], [], [], [], []
    skipped = 0

    prog = Progress(total_rows, desc=f"Filtering {split}")
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            prog.update()
            cat_a = item_category.get(row['img_a'])
            cat_b = item_category.get(row['img_b'])

            if cat_a is None or cat_b is None:
                skipped += 1
                continue

            img_a_list.append(os.path.join(IMG_DIR, row['img_a']))
            img_b_list.append(os.path.join(IMG_DIR, row['img_b']))
            cat_a_list.append(CAT_TO_IDX[cat_a])
            cat_b_list.append(CAT_TO_IDX[cat_b])
            labels.append(int(row['label']))
    prog.done()

    kept = len(labels)
    pos = sum(labels)
    neg = kept - pos
    print(f"    Kept: {kept:,} / {total_rows:,} ({kept/total_rows*100:.1f}%)")
    print(f"    Compatible: {pos:,} | Incompatible: {neg:,}")

    return img_a_list, img_b_list, cat_a_list, cat_b_list, labels

train_data = load_filtered_pairs('train')
val_data = load_filtered_pairs('val')
test_data = load_filtered_pairs('test')

total_kept = len(train_data[4]) + len(val_data[4]) + len(test_data[4])
print(f"\n  Total pairs retained: {total_kept:,}")
print("  [OK] Pairs filtered")

# ─── STEP 5/8: LOAD EMBEDDING EXTRACTOR ─────────────────────────
phase(5, TOTAL_STEPS, "LOAD EMBEDDING EXTRACTOR")

embedding_model = load_model(EXTRACTOR_PATH)
dummy = np.zeros((1, 256, 256, 3), dtype=np.float32)
EMB_DIM = embedding_model.predict(dummy, verbose=0).shape[1]
VECTOR_DIM = EMB_DIM * 2 + NUM_CATS * 2
print(f"  Embedding dim: {EMB_DIM}")
print(f"  Output vector: {EMB_DIM}*2 + {NUM_CATS}*2 = {VECTOR_DIM}-dim")
print("  [OK] Extractor loaded")

# ─── STEP 6/8: EXTRACT EMBEDDINGS ───────────────────────────────
phase(6, TOTAL_STEPS, "EXTRACT EMBEDDINGS (GPU — slowest step)")

all_paths = (train_data[0] + train_data[1] +
             val_data[0] + val_data[1] +
             test_data[0] + test_data[1])
unique_paths = sorted(set(all_paths))

missing = [p for p in unique_paths if not os.path.exists(p)]
if missing:
    print(f"  [WARN] {len(missing)} images not found. Examples:")
    for m in missing[:3]:
        print(f"    {m}")
    unique_paths = [p for p in unique_paths if os.path.exists(p)]

total_images = len(unique_paths)
total_batches = (total_images + 127) // 128
print(f"  Unique images: {total_images:,}")
print(f"  Batches (128/batch): {total_batches}")
print(f"  Estimated time: ~{total_batches * 0.7:.0f}s on T4 GPU")

def decode_img(path):
    img = tf.io.read_file(path)
    img = tf.image.decode_jpeg(img, channels=3)
    img = tf.image.resize(img, [256, 256])
    img = tf.cast(img, tf.float32)
    return img

path_ds = tf.data.Dataset.from_tensor_slices(unique_paths)
img_ds = (path_ds
          .map(decode_img, num_parallel_calls=tf.data.AUTOTUNE)
          .batch(128)
          .prefetch(tf.data.AUTOTUNE))

# Extract with progress tracking
print(f"  Extracting embeddings...")
embed_start = time.time()
all_embeddings = []
prog = Progress(total_batches, desc="GPU extraction")
for batch in img_ds:
    batch_emb = embedding_model.predict(batch, verbose=0)
    all_embeddings.append(batch_emb)
    prog.update()
prog.done()

embeddings_raw = np.concatenate(all_embeddings, axis=0)
print(f"  Extracted shape: {embeddings_raw.shape}")
print(f"  GPU time: {time.time() - embed_start:.1f}s")

emb_dict = {path: emb for path, emb in zip(unique_paths, embeddings_raw)}
print("  [OK] All embeddings extracted")

# ─── STEP 7/8: ASSEMBLE VECTORS AND SAVE ────────────────────────
phase(7, TOTAL_STEPS, "ASSEMBLE PAIRWISE VECTORS & SAVE NPZ")

ZERO_EMB = np.zeros(EMB_DIM, dtype=np.float32)

def build_npz(data, filename):
    img_a_list, img_b_list, cat_a_list, cat_b_list, labels = data
    name = os.path.basename(filename)
    total = len(labels)

    X, y = [], []
    missing_emb = 0
    prog = Progress(total, desc=f"Building {name}")

    for i in range(total):
        emb_a = emb_dict.get(img_a_list[i])
        emb_b = emb_dict.get(img_b_list[i])

        if emb_a is None or emb_b is None:
            missing_emb += 1
            emb_a = emb_a if emb_a is not None else ZERO_EMB
            emb_b = emb_b if emb_b is not None else ZERO_EMB

        cat_a_vec = np.zeros(NUM_CATS, dtype=np.float32)
        cat_a_vec[cat_a_list[i]] = 1.0
        cat_b_vec = np.zeros(NUM_CATS, dtype=np.float32)
        cat_b_vec[cat_b_list[i]] = 1.0

        fused = np.concatenate([emb_a, emb_b, cat_a_vec, cat_b_vec])
        X.append(fused)
        y.append(labels[i])
        prog.update()
    prog.done()

    if missing_emb > 0:
        print(f"    [WARN] {missing_emb} pairs had missing embeddings")

    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.float32)

    assert X.shape[1] == VECTOR_DIM, \
        f"Dimension mismatch! Got {X.shape[1]}, expected {VECTOR_DIM}"

    np.savez_compressed(filename, X=X, y=y)

    pos = int(np.sum(y))
    neg = len(y) - pos
    mb = X.nbytes / (1024 * 1024)
    print(f"    Shape: {X.shape} | Compatible: {pos:,} | Incompatible: {neg:,} | Size: {mb:.1f} MB")

build_npz(train_data, "/kaggle/working/model2_train.npz")
build_npz(val_data, "/kaggle/working/model2_val.npz")
build_npz(test_data, "/kaggle/working/model2_test.npz")
print("  [OK] All NPZ files saved")

# ─── STEP 8/8: SAVE METADATA ────────────────────────────────────
phase(8, TOTAL_STEPS, "SAVE METADATA")

import json
metadata = {
    "embedding_dim": int(EMB_DIM),
    "vector_dim": int(VECTOR_DIM),
    "num_categories": NUM_CATS,
    "category_order": CAT_ORDER,
    "train_pairs": len(train_data[4]),
    "val_pairs": len(val_data[4]),
    "test_pairs": len(test_data[4]),
    "architecture": "pairwise",
    "vector_layout": f"emb_a({EMB_DIM}) + emb_b({EMB_DIM}) + cat_a({NUM_CATS}) + cat_b({NUM_CATS})",
}
with open("/kaggle/working/model2_metadata.json", "w") as f:
    json.dump(metadata, f, indent=2)
print("  Saved: model2_metadata.json")
print("  [OK] Metadata saved")

# ─── FINAL SUMMARY ──────────────────────────────────────────────
total_time = time.time() - SCRIPT_START
print("\n" + "=" * 60)
print("  DATA PREP v3 COMPLETE")
print(f"  Total time: {total_time/60:.1f} minutes")
print(f"  Vector dimension: {VECTOR_DIM}")
print(f"  Train: {len(train_data[4]):,} pairs")
print(f"  Val:   {len(val_data[4]):,} pairs")
print(f"  Test:  {len(test_data[4]):,} pairs")
print("  Files saved in /kaggle/working/")
print("  Next: Run Cell 2 (Model 2 MLP Training)")
print("=" * 60)
