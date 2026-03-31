"""
scripts/seed_social_demo.py
Creates 4 demo social accounts with wardrobes, published outfits, follow
relationships, and likes — so the social feed is pre-populated for the panel demo.

Run ONCE before the demo:
    cd D:/FYP
    py -3.11 scripts/seed_social_demo.py

Safe to re-run — existing accounts (matched by email) are skipped, not duplicated.
Requires: the Flask server to NOT be running (uses direct DB access via Flask app context).
"""

from __future__ import annotations

import json
import os
import sys

# ── Bootstrap Flask app context ───────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("FLASK_ENV", "development")

# Load .env so MySQL credentials are available
_env_path = os.path.join(ROOT, ".env")
if os.path.isfile(_env_path):
    from dotenv import load_dotenv
    load_dotenv(_env_path)

from app import create_app
from app.extensions import db
from app.models_db import (
    Follow, OutfitLike, SavedOutfit, SharedOutfit,
    User, VibeTag, WardrobeItemDB, post_vibes,
)

app = create_app("development")

# ── Demo account definitions ──────────────────────────────────────────────────

DEMO_ACCOUNTS = [
    {
        "email":    "demo_farhan@outfitai.local",
        "password": "Demo1234!",
        "name":     "Farhan Malik",
        "username": "farhan_malik",
        "bio":      "Old Money aesthetics from Lahore 🎩",
        "gender":   "men",
        "style":    "old-money",
        "outfits": [
            {
                "name":     "Monday Board Meeting",
                "occasion": "formal",
                "caption":  "When the meeting demands authority. Quiet luxury, loud presence.",
                "vibes":    ["old-money", "quiet-luxury"],
            },
            {
                "name":     "Weekend Stroll",
                "occasion": "casual",
                "caption":  "Lahore Sunday mornings deserve this fit.",
                "vibes":    ["smart-casual", "minimalist"],
            },
        ],
    },
    {
        "email":    "demo_ayesha@outfitai.local",
        "password": "Demo1234!",
        "name":     "Ayesha Raza",
        "username": "ayesha_raza",
        "bio":      "Desi Chic | Lawn Season enthusiast 🌿",
        "gender":   "women",
        "style":    "desi-casual",
        "outfits": [
            {
                "name":     "Eid Morning Slay",
                "occasion": "formal",
                "caption":  "Chaand Raat to Eid morning — the full glow-up 🌙",
                "vibes":    ["mehndi-festive", "desi-formal"],
            },
            {
                "name":     "Lawn Season Casual",
                "occasion": "casual",
                "caption":  "Nothing beats fresh lawn in May. Light, breezy, effortless.",
                "vibes":    ["lawn-chic", "desi-casual"],
            },
        ],
    },
    {
        "email":    "demo_zain@outfitai.local",
        "password": "Demo1234!",
        "name":     "Zain Ahmed",
        "username": "zain_ahmed",
        "bio":      "Streetwear x East-West fusion | Karachi 🏙️",
        "gender":   "men",
        "style":    "streetwear",
        "outfits": [
            {
                "name":     "Kurta Jogger Combo",
                "occasion": "casual",
                "caption":  "Kurta + joggers + fresh kicks. Fusion done right. 🔥",
                "vibes":    ["fusion-east-west", "south-asian-streetwear"],
            },
            {
                "name":     "Techwear Friday",
                "occasion": "casual",
                "caption":  "Karachi humidity? Never heard of it (I always heard of it).",
                "vibes":    ["streetwear", "techwear"],
            },
        ],
    },
    {
        "email":    "demo_sana@outfitai.local",
        "password": "Demo1234!",
        "name":     "Sana Qureshi",
        "username": "sana_qureshi",
        "bio":      "Minimalist wardrobe, maximal style | Islamabad ✨",
        "gender":   "women",
        "style":    "minimalist",
        "outfits": [
            {
                "name":     "Corporate Minimal",
                "occasion": "formal",
                "caption":  "Less is more — especially in a boardroom.",
                "vibes":    ["minimalist", "business-casual"],
            },
            {
                "name":     "Dark Academia Sunday",
                "occasion": "casual",
                "caption":  "Books, coffee, and this look. Perfect trio.",
                "vibes":    ["dark-academia", "minimalist"],
            },
        ],
    },
]

# Follow matrix: index → follows indices
FOLLOW_MATRIX = {
    0: [1, 2, 3],   # farhan follows everyone
    1: [0, 3],      # ayesha follows farhan, sana
    2: [0, 1],      # zain follows farhan, ayesha
    3: [1, 2],      # sana follows ayesha, zain
}

# Like matrix: (liker_idx, post_idx_of_account)
LIKE_PAIRS = [
    (1, 0, 0),   # ayesha likes farhan's first post
    (2, 0, 0),   # zain likes farhan's first post
    (3, 0, 1),   # sana likes farhan's second post
    (0, 1, 0),   # farhan likes ayesha's first post
    (2, 1, 0),   # zain likes ayesha's first post
    (0, 2, 0),   # farhan likes zain's first post
    (1, 3, 0),   # ayesha likes sana's first post
    (0, 3, 1),   # farhan likes sana's second post
]


def _make_dummy_wardrobe_item(
    user_id: int, category: str, formality: str, upload_dir: str
) -> WardrobeItemDB | None:
    """
    Creates a WardrobeItemDB row with a dummy 1280-dim embedding and a real
    clothing image copied from the dataset folder.
    """
    import hashlib
    import random
    import shutil

    # ── Pick a real clothing image from the dataset ───────────────────────────
    dataset_dir = os.path.join(ROOT, "datasets", "for_model2", "images", category)
    src_image   = None
    if os.path.isdir(dataset_dir):
        images = [f for f in os.listdir(dataset_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
        if images:
            # Seed random by user+category for reproducibility across runs
            rng_pick = random.Random(int(hashlib.md5(f"{user_id}{category}{formality}".encode()).hexdigest(), 16))
            src_image = os.path.join(dataset_dir, rng_pick.choice(images))

    ext      = os.path.splitext(src_image)[1] if src_image else ".png"
    filename = f"demo_{user_id}_{category}_{formality}_{random.randint(1000,9999)}{ext}"
    filepath = os.path.join(upload_dir, filename)

    if not os.path.isfile(filepath):
        if src_image and os.path.isfile(src_image):
            # Copy real clothing image → uploads/
            shutil.copy2(src_image, filepath)
        else:
            # Fallback: plain white PNG when dataset image is unavailable
            try:
                from PIL import Image
                img = Image.new("RGB", (256, 256), color=(240, 238, 235))
                img.save(filepath, "PNG")
            except Exception:
                pass

    # Random 1280-dim L2-normalised embedding (seeded by user+category for reproducibility)
    import numpy as np
    rng = np.random.RandomState(int(hashlib.md5(f"{user_id}{category}".encode()).hexdigest(), 16) % (2**31))
    emb = rng.randn(1280).astype(np.float32)
    emb = emb / np.linalg.norm(emb)
    embedding_json = json.dumps(emb.tolist())

    # Random HSV
    hue = rng.uniform(0, 360)
    sat = rng.uniform(0.1, 0.9)
    val = rng.uniform(0.3, 0.9)

    item = WardrobeItemDB(
        user_id         = user_id,
        image_filename  = filename,
        category        = category,
        formality       = formality,
        gender          = "unisex",
        embedding       = embedding_json,
        color_hue       = hue,
        color_sat       = sat,
        color_val       = val,
        model_confidence= 0.92,
    )
    return item


def seed():
    with app.app_context():
        upload_dir = app.config.get("UPLOAD_FOLDER", os.path.join(os.getcwd(), "uploads"))
        os.makedirs(upload_dir, exist_ok=True)

        # ── Ensure vibe tags are seeded ────────────────────────────────────────
        if VibeTag.query.count() == 0:
            from app.social.routes import VIBE_SEED
            for vid, slug, label, region in VIBE_SEED:
                db.session.add(VibeTag(id=vid, slug=slug, label=label, region=region))
            db.session.commit()
            print(f"  Seeded {len(VIBE_SEED)} vibe tags")
        else:
            print(f"  Vibe tags already seeded ({VibeTag.query.count()} entries)")

        # ── Create accounts ────────────────────────────────────────────────────
        from app.extensions import bcrypt as _bcrypt
        created_users: list[User] = []

        for acct in DEMO_ACCOUNTS:
            existing = User.query.filter_by(email=acct["email"]).first()
            if existing:
                print(f"  Skipping existing account: {acct['username']}")
                created_users.append(existing)
                continue

            pw_hash = _bcrypt.generate_password_hash(acct["password"]).decode("utf-8")
            user = User(
                email         = acct["email"],
                password_hash = pw_hash,
                name          = acct["name"],
                gender        = acct["gender"],
                username      = acct["username"],
                bio           = acct["bio"],
                is_public     = True,
            )
            db.session.add(user)
            db.session.flush()   # get user.id

            # Add wardrobe items (2–3 per category)
            categories_formal  = [("top", "formal"), ("bottom", "formal"), ("shoes", "formal")]
            categories_casual  = [("top", "casual"),  ("bottom", "casual"),  ("shoes", "casual"), ("outwear", "casual")]
            for cat, form in categories_formal + categories_casual:
                item = _make_dummy_wardrobe_item(user.id, cat, form, upload_dir)
                if item:
                    db.session.add(item)

            db.session.flush()
            print(f"  Created user: @{acct['username']} (id={user.id})")
            created_users.append(user)

        db.session.commit()

        # ── Create saved outfits + publish posts ───────────────────────────────
        created_posts: dict[int, list[SharedOutfit]] = {}

        for idx, (acct, user) in enumerate(zip(DEMO_ACCOUNTS, created_users)):
            created_posts[idx] = []

            for outfit_def in acct["outfits"]:
                # Check if outfit already exists
                existing_so = SavedOutfit.query.filter_by(
                    user_id=user.id, name=outfit_def["name"]
                ).first()

                if existing_so is None:
                    # Pick 3 wardrobe items (top + bottom + shoes)
                    item_ids = []
                    for cat in ["top", "bottom", "shoes"]:
                        item = WardrobeItemDB.query.filter_by(
                            user_id=user.id,
                            category=cat,
                            formality=outfit_def["occasion"],
                        ).first()
                        if item:
                            item_ids.append(item.id)
                    if not item_ids:
                        item_ids = [
                            i.id for i in WardrobeItemDB.query.filter_by(user_id=user.id).limit(3).all()
                        ]

                    saved = SavedOutfit(
                        user_id     = user.id,
                        name        = outfit_def["name"],
                        occasion    = outfit_def["occasion"],
                        item_ids    = json.dumps(item_ids),
                        final_score = round(0.72 + idx * 0.03, 2),
                        confidence  = "high",
                    )
                    db.session.add(saved)
                    db.session.flush()
                else:
                    saved = existing_so
                    try:
                        item_ids = json.loads(saved.item_ids)
                    except Exception:
                        item_ids = []

                # Check if post already published
                existing_post = SharedOutfit.query.filter_by(
                    user_id=user.id, saved_outfit_id=saved.id
                ).first()
                if existing_post:
                    created_posts[idx].append(existing_post)
                    continue

                # Resolve vibe tags
                vibes = []
                for slug in outfit_def.get("vibes", []):
                    vt = VibeTag.query.filter_by(slug=slug).first()
                    if vt:
                        vibes.append(vt)

                post = SharedOutfit(
                    user_id         = user.id,
                    saved_outfit_id = saved.id,
                    caption         = outfit_def["caption"],
                    visibility      = "public",
                    like_count      = 0,
                    remix_count     = 0,
                    view_count      = 0,
                )
                post.vibes = vibes
                db.session.add(post)
                db.session.flush()

                # Generate preview mosaic
                try:
                    from engine.preview_generator import generate_outfit_preview
                    image_paths = [
                        os.path.join(upload_dir, WardrobeItemDB.query.get(iid).image_filename)
                        for iid in item_ids if WardrobeItemDB.query.get(iid)
                    ]
                    if len(image_paths) >= 2:
                        import uuid
                        preview_fn = f"preview_{post.id}_{uuid.uuid4().hex[:8]}.jpg"
                        preview_path = os.path.join(upload_dir, preview_fn)
                        ok = generate_outfit_preview(image_paths, preview_path)
                        if ok:
                            post.preview_image_filename = preview_fn
                except Exception as exc:
                    print(f"    Warning: preview generation failed: {exc}")

                created_posts[idx].append(post)
                print(f"    Published: '{outfit_def['name']}' by @{acct['username']}")

        db.session.commit()

        # ── Follow relationships ───────────────────────────────────────────────
        for follower_idx, following_idxs in FOLLOW_MATRIX.items():
            follower = created_users[follower_idx]
            for fi in following_idxs:
                target = created_users[fi]
                if not Follow.query.filter_by(
                    follower_id=follower.id, following_id=target.id
                ).first():
                    db.session.add(Follow(follower_id=follower.id, following_id=target.id))
                    User.query.filter_by(id=follower.id).update(
                        {"following_count": User.following_count + 1}
                    )
                    User.query.filter_by(id=target.id).update(
                        {"follower_count": User.follower_count + 1}
                    )

        db.session.commit()
        print(f"\n  Follow relationships created.")

        # ── Likes ──────────────────────────────────────────────────────────────
        for liker_idx, post_owner_idx, post_idx in LIKE_PAIRS:
            liker = created_users[liker_idx]
            posts = created_posts.get(post_owner_idx, [])
            if post_idx >= len(posts):
                continue
            post = posts[post_idx]
            if not OutfitLike.query.filter_by(
                user_id=liker.id, shared_outfit_id=post.id
            ).first():
                db.session.add(OutfitLike(user_id=liker.id, shared_outfit_id=post.id))
                SharedOutfit.query.filter_by(id=post.id).update(
                    {"like_count": SharedOutfit.like_count + 1}
                )

        db.session.commit()
        print(f"  Likes created.")

        # ── Summary ────────────────────────────────────────────────────────────
        print("\n" + "="*60)
        print("DEMO SEED COMPLETE")
        print("="*60)
        for idx, acct in enumerate(DEMO_ACCOUNTS):
            user = created_users[idx]
            post_count = SharedOutfit.query.filter_by(user_id=user.id).count()
            print(f"  @{acct['username']:20s}  id={user.id:3d}  posts={post_count}  followers={user.follower_count}  following={user.following_count}")
        print("="*60)
        print("\nLogin with any of these accounts:")
        print("  Email:    demo_farhan@outfitai.local   (or ayesha/zain/sana)")
        print("  Password: Demo1234!")


if __name__ == "__main__":
    seed()
