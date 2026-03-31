"""
download_demo_images.py
Downloads real clothing images from Unsplash/Pexels and updates the DB
wardrobe image_filename for the 4 demo accounts.
Run from D:/FYP:  venv\Scripts\python.exe scripts/download_demo_images.py
"""

import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_env_path = os.path.join(ROOT, ".env")
if os.path.isfile(_env_path):
    from dotenv import load_dotenv
    load_dotenv(_env_path)

# ── Real clothing image URLs (Unsplash / Pexels — free to use) ────────────────
# Mapping: user_id -> list of (item_id_index, category, formality, url)
# item_id_index matches the order items were seeded (0-based within user)
DEMO_IMAGE_MAP = {
    8: [  # @farhan_malik — Old Money / Quiet Luxury (Men's)
        ("top",     "formal", "https://images.unsplash.com/photo-1602810316693-3667c854239a?w=600&q=80"),
        ("bottom",  "formal", "https://images.pexels.com/photos/4066293/pexels-photo-4066293.jpeg?auto=compress&cs=tinysrgb&w=600"),
        ("shoes",   "formal", "https://images.pexels.com/photos/2529148/pexels-photo-2529148.jpeg?auto=compress&cs=tinysrgb&w=600"),
        ("top",     "casual", "https://images.unsplash.com/photo-1598033129183-c4f50c736f10?w=600&q=80"),
        ("bottom",  "casual", "https://images.unsplash.com/photo-1605518216938-7c31b7b14ad0?w=600&q=80"),
        ("shoes",   "casual", "https://images.pexels.com/photos/1464625/pexels-photo-1464625.jpeg?auto=compress&cs=tinysrgb&w=600"),
        ("outwear", "formal", "https://images.unsplash.com/photo-1617137968427-85924c800a22?w=600&q=80"),
    ],
    9: [  # @ayesha_raza — Minimalist / Smart Casual (Women's)
        ("top",     "formal", "https://images.unsplash.com/photo-1564257631407-4deb1f99d992?w=600&q=80"),
        ("bottom",  "formal", "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=600&q=80"),
        ("shoes",   "formal", "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=600&q=80"),
        ("top",     "casual", "https://images.unsplash.com/photo-1503342394128-c104d54dba01?w=600&q=80"),
        ("bottom",  "casual", "https://images.unsplash.com/photo-1583496661160-fb5886a0aaaa?w=600&q=80"),
        ("shoes",   "casual", "https://images.pexels.com/photos/336372/pexels-photo-336372.jpeg?auto=compress&cs=tinysrgb&w=600"),
        ("outwear", "casual", "https://images.unsplash.com/photo-1485462537746-965f33f7f6a7?w=600&q=80"),
    ],
    10: [  # @zain_ahmed — Streetwear / Casual (Men's)
        ("top",     "casual", "https://images.unsplash.com/photo-1576566588028-4147f3842f27?w=600&q=80"),
        ("bottom",  "casual", "https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=600&q=80"),
        ("shoes",   "casual", "https://images.pexels.com/photos/1464625/pexels-photo-1464625.jpeg?auto=compress&cs=tinysrgb&w=600"),
        ("top",     "casual", "https://images.unsplash.com/photo-1583743814966-8936f5b7be1a?w=600&q=80"),
        ("bottom",  "casual", "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=600&q=80"),
        ("shoes",   "casual", "https://images.pexels.com/photos/1464625/pexels-photo-1464625.jpeg?auto=compress&cs=tinysrgb&w=600"),
        ("outwear", "casual", "https://images.pexels.com/photos/5698851/pexels-photo-5698851.jpeg?auto=compress&cs=tinysrgb&w=600"),
    ],
    11: [  # @sana_qureshi — Desi Fusion / Modest (Women's)
        ("top",     "formal", "https://images.pexels.com/photos/2220316/pexels-photo-2220316.jpeg?auto=compress&cs=tinysrgb&w=600"),
        ("bottom",  "formal", "https://images.pexels.com/photos/1152077/pexels-photo-1152077.jpeg?auto=compress&cs=tinysrgb&w=600"),
        ("shoes",   "formal", "https://images.pexels.com/photos/3782786/pexels-photo-3782786.jpeg?auto=compress&cs=tinysrgb&w=600"),
        ("top",     "casual", "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=600&q=80"),
        ("bottom",  "casual", "https://images.unsplash.com/photo-1591369822096-ffd140ec948f?w=600&q=80"),
        ("shoes",   "casual", "https://images.pexels.com/photos/1407354/pexels-photo-1407354.jpeg?auto=compress&cs=tinysrgb&w=600"),
        ("outwear", "casual", "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=600&q=80"),
    ],
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def download(url: str, dest: str) -> bool:
    """Download a URL to dest. Returns True on success."""
    try:
        req  = urllib.request.Request(url, headers=HEADERS)
        data = urllib.request.urlopen(req, timeout=20).read()
        if len(data) < 5000:
            print(f"    WARNING: file too small ({len(data)} bytes) — may be error page")
            return False
        with open(dest, "wb") as f:
            f.write(data)
        return True
    except Exception as e:
        print(f"    DOWNLOAD FAILED: {e}")
        return False


def run():
    from app import create_app
    from app.models_db import db, WardrobeItemDB

    app = create_app("development")
    upload_dir = app.config.get("UPLOAD_FOLDER", os.path.join(ROOT, "uploads"))
    os.makedirs(upload_dir, exist_ok=True)

    with app.app_context():
        total_fixed = 0

        for user_id, image_list in DEMO_IMAGE_MAP.items():
            print(f"\nUser {user_id}:")

            # Get DB items in creation order
            db_items = (
                WardrobeItemDB.query
                .filter_by(user_id=user_id)
                .order_by(WardrobeItemDB.id)
                .all()
            )

            for idx, (cat, form, url) in enumerate(image_list):
                if idx >= len(db_items):
                    print(f"  [{idx}] SKIP — no DB row for index {idx}")
                    continue

                item = db_items[idx]
                new_filename = f"real_{user_id}_{cat}_{form}_{item.id}.jpg"
                dest = os.path.join(upload_dir, new_filename)

                # Remove old file if it exists
                old_path = os.path.join(upload_dir, item.image_filename)
                if os.path.isfile(old_path):
                    os.remove(old_path)

                print(f"  [{idx}] {cat}/{form} id={item.id} ... ", end="", flush=True)
                ok = download(url, dest)
                if ok:
                    item.image_filename = new_filename
                    total_fixed += 1
                    size_kb = os.path.getsize(dest) // 1024
                    print(f"OK ({size_kb} KB) -> {new_filename}")
                else:
                    print(f"FAILED — keeping old file")

                time.sleep(0.3)  # polite rate-limit

        db.session.commit()
        print(f"\nDone. {total_fixed} items updated with downloaded images.")


if __name__ == "__main__":
    run()
