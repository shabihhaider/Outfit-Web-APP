"""
fix_demo_images.py
Replace the white placeholder images for demo accounts (users 8–11)
with real clothing images from the dataset.
Run from D:/FYP:  venv\Scripts\python.exe scripts/fix_demo_images.py
"""

import os
import sys
import random
import hashlib
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_env_path = os.path.join(ROOT, ".env")
if os.path.isfile(_env_path):
    from dotenv import load_dotenv
    load_dotenv(_env_path)

from app import create_app
from app.models_db import db, WardrobeItemDB

DATASET_DIR = os.path.join(ROOT, "datasets", "for_model2", "images")
DEMO_USER_IDS = [8, 9, 10, 11]


def _pick_image(category: str, seed_key: str) -> str | None:
    """Pick a deterministic real clothing image from the dataset for this category."""
    cat_dir = os.path.join(DATASET_DIR, category)
    if not os.path.isdir(cat_dir):
        return None
    images = [f for f in os.listdir(cat_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    if not images:
        return None
    rng = random.Random(int(hashlib.md5(seed_key.encode()).hexdigest(), 16))
    return os.path.join(cat_dir, rng.choice(images))


def fix():
    app = create_app("development")
    upload_dir = app.config.get("UPLOAD_FOLDER", os.path.join(ROOT, "uploads"))
    os.makedirs(upload_dir, exist_ok=True)

    with app.app_context():
        items = (
            WardrobeItemDB.query
            .filter(WardrobeItemDB.user_id.in_(DEMO_USER_IDS))
            .all()
        )
        print(f"Found {len(items)} demo wardrobe items to fix.")

        fixed = 0
        for item in items:
            src = _pick_image(item.category, f"{item.user_id}{item.category}{item.formality}{item.id}")
            if not src:
                print(f"  SKIP id={item.id}: no dataset image for category '{item.category}'")
                continue

            ext      = os.path.splitext(src)[1]
            new_name = f"demo_{item.user_id}_{item.category}_{item.formality}_{item.id}{ext}"
            dst      = os.path.join(upload_dir, new_name)

            # Copy real image → uploads/
            shutil.copy2(src, dst)

            # Update DB record
            item.image_filename = new_name
            fixed += 1
            print(f"  FIXED id={item.id} user={item.user_id} {item.category}/{item.formality} -> {new_name}")

        db.session.commit()
        print(f"\nDone. {fixed}/{len(items)} items updated with real clothing images.")


if __name__ == "__main__":
    fix()
