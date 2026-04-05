"""
app/social/routes.py
Atelier Social — full /social/* blueprint.

Endpoints
---------
Profile
  PATCH  /social/profile
  GET    /social/profile/style-dna
  GET    /social/users/<username>
  GET    /social/users/<username>/style-dna
  GET    /social/users/<username>/compatibility

Follow graph
  POST   /social/follow/<int:user_id>
  DELETE /social/follow/<int:user_id>
  GET    /social/followers
  GET    /social/following

Publishing
  POST   /social/publish
  GET    /social/posts/<int:post_id>
  PATCH  /social/posts/<int:post_id>
  DELETE /social/posts/<int:post_id>

Feed
  GET    /social/feed

Post interactions
  POST   /social/posts/<int:post_id>/like
  POST   /social/posts/<int:post_id>/bookmark
  GET    /social/bookmarks

Remix
  POST   /social/posts/<int:post_id>/remix
  GET    /social/posts/<int:post_id>/remix-chain

Reference
  GET    /social/vibes
  GET    /social/vibes/trending
"""

from __future__ import annotations

import base64
import json
import logging
import math
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models_db import (
    Follow, OutfitLike, PostBookmark, RemixLog,
    SavedOutfit, SharedOutfit, User, VibeTag, WardrobeItemDB,
    post_vibes,
)
from app.utils import allowed_file, validate_image_content

logger = logging.getLogger(__name__)

social_bp = Blueprint("social", __name__)

# ── Constants ─────────────────────────────────────────────────────────────────

USERNAME_RE = re.compile(r"^[a-z0-9_]{3,30}$")
VALID_VISIBILITY = {"public", "followers", "private"}
MAX_VIBES_PER_POST = 3
FEED_PAGE_SIZE = 20

COMPAT_LABELS = {
    (0.75, 1.01): "High Match",
    (0.50, 0.75): "Good Match",
    (0.00, 0.50): "Unique Styles",
}

VIBE_SEED = [
    (1,  "streetwear",            "Streetwear",             "global"),
    (2,  "minimalist",            "Minimalist",             "global"),
    (3,  "old-money",             "Old Money",              "global"),
    (4,  "cottagecore",           "Cottagecore",            "global"),
    (5,  "dark-academia",         "Dark Academia",          "global"),
    (6,  "y2k",                   "Y2K Revival",            "global"),
    (7,  "boho",                  "Boho",                   "global"),
    (8,  "grunge",                "Grunge",                 "global"),
    (9,  "preppy",                "Preppy",                 "global"),
    (10, "athleisure",            "Athleisure",             "global"),
    (11, "party-glam",            "Party Glam",             "global"),
    (12, "quiet-luxury",          "Quiet Luxury",           "global"),
    (13, "coastal",               "Coastal",                "global"),
    (14, "balletcore",            "Balletcore",             "global"),
    (15, "techwear",              "Techwear",               "global"),
    (16, "gorpcore",              "Gorpcore",               "global"),
    (17, "avant-garde",           "Avant-Garde",            "global"),
    (18, "mob-wife",              "Mob Wife",               "global"),
    (19, "business-casual",       "Business Casual",        "global"),
    (20, "smart-casual",          "Smart Casual",           "global"),
    (21, "desi-casual",           "Desi Casual",            "south-asian"),
    (22, "desi-formal",           "Desi Formal",            "south-asian"),
    (23, "fusion-east-west",      "East-West Fusion",       "south-asian"),
    (24, "lawn-chic",             "Lawn Chic",              "south-asian"),
    (25, "bridal-south-asian",    "South Asian Bridal",     "south-asian"),
    (26, "mehndi-festive",        "Mehndi & Festive",       "south-asian"),
    (27, "modest-fashion",        "Modest Fashion",         "south-asian"),
    (28, "south-asian-streetwear","Desi Streetwear",        "south-asian"),
    (29, "mughal-luxe",           "Mughal Luxe",            "south-asian"),
    (30, "peshawari-traditional", "Peshawari Traditional",  "south-asian"),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ensure_vibes_seeded() -> None:
    """Idempotently seed the vibe_tags reference table if empty."""
    if VibeTag.query.count() == 0:
        for vid, slug, label, region in VIBE_SEED:
            db.session.add(VibeTag(id=vid, slug=slug, label=label, region=region))
        db.session.commit()
        logger.info("Seeded %d vibe tags.", len(VIBE_SEED))


def _encode_cursor(post_id: int, created_at: datetime) -> str:
    payload = json.dumps({"id": post_id, "ts": created_at.isoformat()})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _decode_cursor(cursor: str) -> dict | None:
    try:
        return json.loads(base64.urlsafe_b64decode(cursor.encode()))
    except Exception:
        return None


def _upload_dir() -> str:
    return current_app.config.get("UPLOAD_FOLDER", os.path.join(os.getcwd(), "uploads"))


def _post_to_dict(post: SharedOutfit, viewer_id: int | None) -> dict:
    """Serialise a SharedOutfit with like/bookmark status for the given viewer."""
    d = post.to_dict(viewer_id=viewer_id)

    if viewer_id is not None:
        liked = OutfitLike.query.filter_by(
            user_id=viewer_id, shared_outfit_id=post.id
        ).first() is not None
        bookmarked = PostBookmark.query.filter_by(
            user_id=viewer_id, shared_outfit_id=post.id
        ).first() is not None
        is_following_author = (
            post.user_id != viewer_id and
            Follow.query.filter_by(follower_id=viewer_id, following_id=post.user_id).first() is not None
        )
        d["is_liked"]            = liked
        d["is_bookmarked"]       = bookmarked
        d["is_following_author"] = is_following_author
    else:
        d["is_liked"]            = False
        d["is_bookmarked"]       = False
        d["is_following_author"] = False

    # Attach saved outfit metadata + item thumbnail URLs for preview fallback
    if post.saved_outfit:
        so = post.saved_outfit
        try:
            item_ids = json.loads(so.item_ids) if so.item_ids else []
        except (json.JSONDecodeError, TypeError):
            item_ids = []
        # Fetch up to 6 item images so the feed card can render a grid when preview_url is null
        thumb_items = WardrobeItemDB.query.filter(WardrobeItemDB.id.in_(item_ids[:6])).all()
        thumb_map   = {i.id: i for i in thumb_items}
        item_images = [
            f"/uploads/{thumb_map[iid].image_filename}"
            for iid in item_ids[:6]
            if iid in thumb_map and thumb_map[iid].image_filename
        ]
        d["outfit"] = {
            "id":          so.id,
            "name":        so.name,
            "occasion":    so.occasion,
            "final_score": so.final_score,
            "confidence":  so.confidence,
            "item_count":  len(item_ids),
            "item_images": item_images,
        }

    return d


def _is_post_visible(post: SharedOutfit, viewer_id: int | None) -> bool:
    """Check if viewer is allowed to see this post."""
    if post.visibility == "public":
        return True
    if viewer_id is None:
        return False
    if post.user_id == viewer_id:
        return True
    if post.visibility == "followers":
        return Follow.query.filter_by(
            follower_id=viewer_id, following_id=post.user_id
        ).first() is not None
    return False   # "private"


def _feed_score(
    created_at: datetime,
    like_count: int,
    remix_count: int,
    view_count: int,
    is_following: bool,
    shared_vibes: int,
    post_vibes_count: int,
) -> float:
    age_hours   = (datetime.now(timezone.utc) - created_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
    recency     = math.exp(-0.05 * age_hours)
    impressions = max(view_count, 1)
    engagement  = min((like_count + remix_count * 3) / impressions, 1.0)
    follow_sig  = 1.0 if is_following else 0.2
    vibe_aff    = (shared_vibes / post_vibes_count) if post_vibes_count > 0 else 0.0
    return 0.40 * recency + 0.30 * engagement + 0.20 * follow_sig + 0.10 * vibe_aff


# ── Profile ───────────────────────────────────────────────────────────────────

@social_bp.route("/profile", methods=["PATCH"])
@jwt_required()
def update_profile():
    user_id = int(get_jwt_identity())
    user    = db.session.get(User, user_id)
    data    = request.get_json(silent=True) or {}

    if "name" in data:
        n = str(data["name"]).strip()[:80]
        if n:
            user.name = n

    if "username" in data:
        uname = str(data["username"]).strip().lower()
        if not USERNAME_RE.match(uname):
            return jsonify({"error": "username must be 3–30 chars: lowercase letters, digits, underscore."}), 422
        # Check uniqueness (excluding self)
        existing = User.query.filter(User.username == uname, User.id != user_id).first()
        if existing:
            return jsonify({"error": "Username already taken."}), 409
        user.username = uname

    if "bio" in data:
        bio = str(data["bio"]).strip()[:150]
        user.bio = bio or None

    if "is_public" in data:
        user.is_public = bool(data["is_public"])

    if "vibe_preferences" in data:
        prefs = data["vibe_preferences"]
        if not isinstance(prefs, list):
            return jsonify({"error": "vibe_preferences must be a list of slug strings."}), 422
        # Validate slugs exist
        valid_slugs = {v.slug for v in VibeTag.query.all()}
        bad = [s for s in prefs if s not in valid_slugs]
        if bad:
            return jsonify({"error": f"Unknown vibe slugs: {bad}"}), 422
        user.vibe_preferences = json.dumps(prefs[:10])

    if "gender" in data:
        g = str(data["gender"]).strip().lower()
        if g in ("men", "women", "unisex"):
            user.gender = g

    if "fusion_mode_enabled" in data:
        user.fusion_mode_enabled = bool(data["fusion_mode_enabled"])

    db.session.commit()
    return jsonify(user.to_dict()), 200


@social_bp.route("/profile/avatar", methods=["POST"])
@jwt_required()
def upload_avatar():
    """Upload or replace the user's profile avatar image."""
    user_id = int(get_jwt_identity())

    if "avatar" not in request.files:
        return jsonify({"error": "No file provided. Field name must be 'avatar'."}), 400

    file = request.files["avatar"]
    if not file.filename:
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename, current_app.config["ALLOWED_EXTENSIONS"]):
        return jsonify({"error": "File type not allowed. Use jpg or png."}), 400

    content = file.read()
    if not validate_image_content(content):
        return jsonify({"error": "File is not a valid image."}), 400

    user = db.session.get(User, user_id)

    # Delete previous avatar
    if user.avatar_filename:
        old_path = os.path.join(current_app.config["UPLOAD_FOLDER"], user.avatar_filename)
        try:
            if os.path.exists(old_path):
                os.remove(old_path)
        except OSError:
            pass

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"avatar_{user_id}_{uuid.uuid4().hex[:12]}.{ext}"
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    with open(os.path.join(upload_dir, filename), "wb") as f:
        f.write(content)

    user.avatar_filename = filename
    db.session.commit()

    return jsonify({
        "avatar_url": f"/uploads/{filename}",
    }), 200


@social_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_my_profile():
    """Return the current user's full profile."""
    user_id = int(get_jwt_identity())
    user    = db.session.get(User, user_id)
    return jsonify(user.to_dict()), 200


@social_bp.route("/profile/style-dna", methods=["GET"])
@jwt_required()
def my_style_dna():
    user_id = int(get_jwt_identity())
    items   = WardrobeItemDB.query.filter_by(user_id=user_id).all()
    from engine.style_dna import compute_style_dna
    dna = compute_style_dna(items)
    return jsonify(dna.to_dict()), 200


@social_bp.route("/users/<username>", methods=["GET"])
def get_public_profile(username: str):
    """Public profile page — no auth required for public accounts."""
    _ensure_vibes_seeded()

    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify({"error": "User not found."}), 404

    # Determine viewer
    viewer_id: int | None = None
    try:
        verify_jwt_in_request(optional=True)
        raw = get_jwt_identity()
        if raw:
            viewer_id = int(raw)
    except Exception:
        pass

    if not user.is_public and viewer_id != user.id:
        # Check if viewer follows this private user
        if viewer_id is None or not Follow.query.filter_by(
            follower_id=viewer_id, following_id=user.id
        ).first():
            return jsonify({"error": "This profile is private."}), 403

    posts = (
        SharedOutfit.query
        .filter_by(user_id=user.id, visibility="public")
        .order_by(SharedOutfit.created_at.desc())
        .limit(12)
        .all()
    )

    is_following = False
    if viewer_id and viewer_id != user.id:
        is_following = Follow.query.filter_by(
            follower_id=viewer_id, following_id=user.id
        ).first() is not None

    return jsonify({
        "user":         user.social_dict(),
        "posts":        [_post_to_dict(p, viewer_id) for p in posts],
        "is_following": is_following,
    }), 200


@social_bp.route("/users/<username>/style-dna", methods=["GET"])
def get_user_style_dna(username: str):
    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify({"error": "User not found."}), 404
    if not user.is_public:
        return jsonify({"error": "Profile is private."}), 403

    items = WardrobeItemDB.query.filter_by(user_id=user.id).all()
    from engine.style_dna import compute_style_dna
    dna = compute_style_dna(items)
    return jsonify(dna.to_dict()), 200


@social_bp.route("/users/<username>/compatibility", methods=["GET"])
@jwt_required()
def get_compatibility(username: str):
    viewer_id = int(get_jwt_identity())

    other = User.query.filter_by(username=username).first()
    if other is None:
        return jsonify({"error": "User not found."}), 404
    if other.id == viewer_id:
        return jsonify({"error": "Cannot compute compatibility with yourself."}), 400

    my_items    = WardrobeItemDB.query.filter_by(user_id=viewer_id).all()
    their_items = WardrobeItemDB.query.filter_by(user_id=other.id).all()

    if len(my_items) < 5 or len(their_items) < 5:
        return jsonify({"score": None, "label": "Not enough wardrobe data", "shared_vibes": []}), 200

    from engine.style_dna import compute_style_compatibility
    score = compute_style_compatibility(my_items, their_items)

    label = "Unique Styles"
    if score is not None:
        for (lo, hi), lbl in COMPAT_LABELS.items():
            if lo <= score < hi:
                label = lbl
                break

    # Shared vibe slugs (from published posts of each user)
    my_vibes    = {v.slug for p in SharedOutfit.query.filter_by(user_id=viewer_id) for v in p.vibes}
    their_vibes = {v.slug for p in SharedOutfit.query.filter_by(user_id=other.id) for v in p.vibes}
    shared = list(my_vibes & their_vibes)

    return jsonify({"score": score, "label": label, "shared_vibes": shared}), 200


# ── Follow graph ──────────────────────────────────────────────────────────────

@social_bp.route("/follow/<int:target_id>", methods=["POST"])
@jwt_required()
def follow_user(target_id: int):
    follower_id = int(get_jwt_identity())

    if follower_id == target_id:
        return jsonify({"error": "Cannot follow yourself."}), 400

    target = db.session.get(User, target_id)
    if target is None:
        return jsonify({"error": "User not found."}), 404

    if Follow.query.filter_by(follower_id=follower_id, following_id=target_id).first():
        return jsonify({"error": "Already following."}), 409

    db.session.add(Follow(follower_id=follower_id, following_id=target_id))
    User.query.filter_by(id=follower_id).update({"following_count": User.following_count + 1})
    User.query.filter_by(id=target_id).update({"follower_count": User.follower_count + 1})
    db.session.commit()

    db.session.refresh(target)
    return jsonify({"message": "Now following.", "follower_count": target.follower_count}), 201


@social_bp.route("/follow/<int:target_id>", methods=["DELETE"])
@jwt_required()
def unfollow_user(target_id: int):
    follower_id = int(get_jwt_identity())

    rows = Follow.query.filter_by(follower_id=follower_id, following_id=target_id).delete()
    if not rows:
        return jsonify({"error": "Not following this user."}), 404

    User.query.filter_by(id=follower_id).update(
        {"following_count": case((User.following_count >= 1, User.following_count - 1), else_=0)}
    )
    User.query.filter_by(id=target_id).update(
        {"follower_count": case((User.follower_count >= 1, User.follower_count - 1), else_=0)}
    )
    db.session.commit()
    return jsonify({"message": "Unfollowed."}), 200


@social_bp.route("/followers", methods=["GET"])
@jwt_required()
def list_followers():
    user_id = int(get_jwt_identity())
    limit   = min(int(request.args.get("limit", 20)), 50)
    cursor  = request.args.get("cursor")

    q = (
        db.session.query(User)
        .join(Follow, Follow.follower_id == User.id)
        .filter(Follow.following_id == user_id)
        .order_by(Follow.created_at.desc(), Follow.follower_id.desc())
    )
    if cursor:
        c = _decode_cursor(cursor)
        if c:
            q = q.filter(Follow.created_at < c["ts"])

    rows     = q.limit(limit + 1).all()
    has_more = len(rows) > limit
    rows     = rows[:limit]

    next_cursor = None
    if has_more and rows:
        last_follow = Follow.query.filter_by(
            follower_id=rows[-1].id, following_id=user_id
        ).first()
        if last_follow:
            next_cursor = _encode_cursor(rows[-1].id, last_follow.created_at)

    return jsonify({
        "users":      [u.social_dict() for u in rows],
        "pagination": {"next_cursor": next_cursor, "has_more": has_more},
    }), 200


@social_bp.route("/following", methods=["GET"])
@jwt_required()
def list_following():
    user_id = int(get_jwt_identity())
    limit   = min(int(request.args.get("limit", 20)), 50)

    rows = (
        db.session.query(User)
        .join(Follow, Follow.following_id == User.id)
        .filter(Follow.follower_id == user_id)
        .order_by(Follow.created_at.desc())
        .limit(limit)
        .all()
    )
    return jsonify({"users": [u.social_dict() for u in rows]}), 200


# ── Publishing ────────────────────────────────────────────────────────────────

@social_bp.route("/publish", methods=["POST"])
@jwt_required()
def publish_outfit():
    _ensure_vibes_seeded()
    user_id = int(get_jwt_identity())
    data    = request.get_json(silent=True) or {}

    saved_outfit_id = data.get("saved_outfit_id")
    if not saved_outfit_id:
        return jsonify({"error": "'saved_outfit_id' is required."}), 422

    saved = db.session.get(SavedOutfit, saved_outfit_id)
    if saved is None or saved.user_id != user_id:
        return jsonify({"error": "Saved outfit not found."}), 404

    caption    = str(data.get("caption", "")).strip()[:300] or None
    visibility = str(data.get("visibility", "public")).lower()
    if visibility not in VALID_VISIBILITY:
        return jsonify({"error": f"visibility must be one of: {', '.join(VALID_VISIBILITY)}."}), 422

    # Resolve vibe tags
    vibe_slugs = data.get("vibe_slugs", [])
    if not isinstance(vibe_slugs, list) or len(vibe_slugs) > MAX_VIBES_PER_POST:
        return jsonify({"error": f"vibe_slugs must be a list of up to {MAX_VIBES_PER_POST} slugs."}), 422

    vibes: list[VibeTag] = []
    for slug in vibe_slugs:
        vt = VibeTag.query.filter_by(slug=slug).first()
        if vt is None:
            return jsonify({"error": f"Unknown vibe slug: '{slug}'."}), 422
        vibes.append(vt)

    # Optional remix attribution
    remix_source_id = data.get("remix_source_post_id")
    if remix_source_id is not None:
        source_post = db.session.get(SharedOutfit, remix_source_id)
        if source_post is None:
            remix_source_id = None

    # Create the post
    post = SharedOutfit(
        user_id             = user_id,
        saved_outfit_id     = saved_outfit_id,
        caption             = caption,
        visibility          = visibility,
        remix_source_post_id= remix_source_id,
    )
    post.vibes = vibes
    db.session.add(post)
    db.session.flush()   # get post.id before commit

    # Generate preview image
    try:
        item_ids: list[int] = json.loads(saved.item_ids) if saved.item_ids else []
        items = WardrobeItemDB.query.filter(WardrobeItemDB.id.in_(item_ids)).all()
        upload_dir = _upload_dir()
        image_paths = [
            os.path.join(upload_dir, item.image_filename)
            for item in items
        ]
        preview_filename = f"preview_{post.id}_{uuid.uuid4().hex[:8]}.jpg"
        preview_path     = os.path.join(upload_dir, preview_filename)

        from engine.preview_generator import generate_outfit_preview
        ok = generate_outfit_preview(image_paths, preview_path)
        if ok:
            post.preview_image_filename = preview_filename
    except Exception as exc:
        logger.warning("Preview generation failed for post %s: %s", post.id, exc)

    db.session.commit()

    return jsonify({
        "id":          post.id,
        "preview_url": f"/uploads/{post.preview_image_filename}" if post.preview_image_filename else None,
        "caption":     post.caption,
        "vibes":       [v.to_dict() for v in post.vibes],
        "visibility":  post.visibility,
        "created_at":  post.created_at.isoformat(),
    }), 201


@social_bp.route("/posts/<int:post_id>", methods=["GET"])
def get_post(post_id: int):
    """Full post detail — public for public posts."""
    viewer_id: int | None = None
    try:
        verify_jwt_in_request(optional=True)
        raw = get_jwt_identity()
        if raw:
            viewer_id = int(raw)
    except Exception:
        pass

    post = db.session.get(SharedOutfit, post_id)
    if post is None:
        return jsonify({"error": "Post not found."}), 404
    if not _is_post_visible(post, viewer_id):
        return jsonify({"error": "Access denied."}), 403

    # Increment view count (non-author views only)
    if viewer_id != post.user_id:
        SharedOutfit.query.filter_by(id=post_id).update(
            {"view_count": SharedOutfit.view_count + 1}
        )
        db.session.commit()

    d = _post_to_dict(post, viewer_id)

    # Attach full item list
    if post.saved_outfit:
        try:
            item_ids = json.loads(post.saved_outfit.item_ids) if post.saved_outfit.item_ids else []
        except (json.JSONDecodeError, TypeError):
            item_ids = []
        items = WardrobeItemDB.query.filter(WardrobeItemDB.id.in_(item_ids)).all()
        item_map = {i.id: i for i in items}
        d["items"] = [
            {
                "id":           item_map[iid].id,
                "category":     item_map[iid].category,
                "image_url":    f"/uploads/{item_map[iid].image_filename}",
                "sub_category": item_map[iid].sub_category,
            }
            for iid in item_ids if iid in item_map
        ]

    # Can this viewer remix?
    d["can_remix"] = viewer_id is not None and viewer_id != post.user_id

    return jsonify(d), 200


@social_bp.route("/posts/<int:post_id>", methods=["PATCH"])
@jwt_required()
def update_post(post_id: int):
    user_id = int(get_jwt_identity())
    post    = db.session.get(SharedOutfit, post_id)
    if post is None:
        return jsonify({"error": "Post not found."}), 404
    if post.user_id != user_id:
        return jsonify({"error": "Access forbidden."}), 403

    data = request.get_json(silent=True) or {}

    if "caption" in data:
        post.caption = str(data["caption"]).strip()[:300] or None
    if "visibility" in data:
        v = str(data["visibility"]).lower()
        if v not in VALID_VISIBILITY:
            return jsonify({"error": "Invalid visibility."}), 422
        post.visibility = v

    db.session.commit()
    return jsonify({"id": post.id, "caption": post.caption, "visibility": post.visibility}), 200


@social_bp.route("/posts/<int:post_id>", methods=["DELETE"])
@jwt_required()
def delete_post(post_id: int):
    user_id = int(get_jwt_identity())
    post    = db.session.get(SharedOutfit, post_id)
    if post is None:
        return jsonify({"error": "Post not found."}), 404
    if post.user_id != user_id:
        return jsonify({"error": "Access forbidden."}), 403

    # Delete preview file from disk (best-effort)
    if post.preview_image_filename:
        try:
            path = os.path.join(_upload_dir(), post.preview_image_filename)
            if os.path.isfile(path):
                os.remove(path)
        except OSError as exc:
            logger.warning("Could not delete preview file: %s", exc)

    db.session.delete(post)
    db.session.commit()
    return jsonify({"message": "Post deleted."}), 200


# ── Feed ──────────────────────────────────────────────────────────────────────

@social_bp.route("/feed", methods=["GET"])
@jwt_required()
def get_feed():
    _ensure_vibes_seeded()
    user_id = int(get_jwt_identity())
    tab     = request.args.get("tab", "discover").lower()
    limit   = min(int(request.args.get("limit", FEED_PAGE_SIZE)), 50)
    cursor  = request.args.get("cursor")
    vibe_filter = request.args.get("vibe")

    # Decode cursor
    cursor_ts = None
    cursor_id = None
    if cursor:
        c = _decode_cursor(cursor)
        if c:
            cursor_ts = c.get("ts")
            cursor_id = c.get("id")

    # User's vibe preferences for scoring
    me = db.session.get(User, user_id)
    my_vibe_prefs: set[str] = set()
    if me and me.vibe_preferences:
        try:
            my_vibe_prefs = set(json.loads(me.vibe_preferences))
        except (json.JSONDecodeError, TypeError):
            pass

    if tab == "following":
        # Posts from users I follow
        following_ids = [
            f.following_id for f in Follow.query.filter_by(follower_id=user_id).all()
        ]
        if not following_ids:
            return jsonify({"tab": "following", "posts": [], "pagination": {"next_cursor": None, "has_more": False}}), 200

        q = SharedOutfit.query.filter(
            SharedOutfit.user_id.in_(following_ids),
            SharedOutfit.visibility.in_(["public", "followers"]),
        )
    else:
        # Discover — all public posts, not your own
        q = SharedOutfit.query.filter(
            SharedOutfit.visibility == "public",
            SharedOutfit.user_id != user_id,
        )

    # Vibe filter
    if vibe_filter:
        vt = VibeTag.query.filter_by(slug=vibe_filter).first()
        if vt:
            q = q.join(post_vibes, SharedOutfit.id == post_vibes.c.post_id).filter(
                post_vibes.c.vibe_id == vt.id
            )

    # Cursor pagination
    if cursor_ts and cursor_id:
        q = q.filter(
            db.or_(
                SharedOutfit.created_at < cursor_ts,
                db.and_(SharedOutfit.created_at == cursor_ts, SharedOutfit.id < cursor_id),
            )
        )

    q = q.order_by(SharedOutfit.created_at.desc(), SharedOutfit.id.desc())

    # Fetch extra for has_more
    raw = q.limit(limit + 1).all()
    has_more = len(raw) > limit
    raw = raw[:limit]

    # Score and sort (for discover tab — already ordered by recency for following)
    if tab == "discover":
        following_ids_set = {
            f.following_id for f in Follow.query.filter_by(follower_id=user_id).all()
        }
        def _score(p: SharedOutfit) -> float:
            post_vibe_slugs = {v.slug for v in (p.vibes or [])}
            return _feed_score(
                p.created_at, p.like_count, p.remix_count, p.view_count,
                p.user_id in following_ids_set,
                len(my_vibe_prefs & post_vibe_slugs),
                len(post_vibe_slugs),
            )
        raw.sort(key=_score, reverse=True)

    posts = [_post_to_dict(p, user_id) for p in raw]

    next_cursor = None
    if has_more and raw:
        next_cursor = _encode_cursor(raw[-1].id, raw[-1].created_at)

    return jsonify({
        "tab":        tab,
        "posts":      posts,
        "pagination": {"next_cursor": next_cursor, "has_more": has_more},
    }), 200


# ── Post interactions ─────────────────────────────────────────────────────────

@social_bp.route("/posts/<int:post_id>/like", methods=["POST"])
@jwt_required()
def toggle_like(post_id: int):
    user_id = int(get_jwt_identity())

    post = db.session.get(SharedOutfit, post_id)
    if post is None:
        return jsonify({"error": "Post not found."}), 404
    if not _is_post_visible(post, user_id):
        return jsonify({"error": "Access denied."}), 403
    if post.user_id == user_id:
        return jsonify({"error": "You cannot like your own post."}), 400

    existing = OutfitLike.query.filter_by(
        user_id=user_id, shared_outfit_id=post_id
    ).first()

    if existing:
        # Unlike
        db.session.delete(existing)
        SharedOutfit.query.filter_by(id=post_id).update(
            {"like_count": case((SharedOutfit.like_count >= 1, SharedOutfit.like_count - 1), else_=0)}
        )
        db.session.commit()
        db.session.refresh(post)
        return jsonify({"liked": False, "like_count": post.like_count}), 200
    else:
        # Like
        db.session.add(OutfitLike(user_id=user_id, shared_outfit_id=post_id))
        SharedOutfit.query.filter_by(id=post_id).update(
            {"like_count": SharedOutfit.like_count + 1}
        )
        db.session.commit()
        db.session.refresh(post)
        return jsonify({"liked": True, "like_count": post.like_count}), 200


@social_bp.route("/posts/<int:post_id>/bookmark", methods=["POST"])
@jwt_required()
def toggle_bookmark(post_id: int):
    user_id = int(get_jwt_identity())

    post = db.session.get(SharedOutfit, post_id)
    if post is None:
        return jsonify({"error": "Post not found."}), 404
    if not _is_post_visible(post, user_id):
        return jsonify({"error": "Access denied."}), 403

    existing = PostBookmark.query.filter_by(
        user_id=user_id, shared_outfit_id=post_id
    ).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"bookmarked": False}), 200
    else:
        db.session.add(PostBookmark(user_id=user_id, shared_outfit_id=post_id))
        db.session.commit()
        return jsonify({"bookmarked": True}), 200


@social_bp.route("/bookmarks", methods=["GET"])
@jwt_required()
def list_bookmarks():
    user_id = int(get_jwt_identity())
    limit   = min(int(request.args.get("limit", FEED_PAGE_SIZE)), 50)
    cursor  = request.args.get("cursor")

    q = (
        db.session.query(SharedOutfit)
        .join(PostBookmark, PostBookmark.shared_outfit_id == SharedOutfit.id)
        .filter(PostBookmark.user_id == user_id)
        .order_by(PostBookmark.created_at.desc(), SharedOutfit.id.desc())
    )
    if cursor:
        c = _decode_cursor(cursor)
        if c:
            q = q.filter(PostBookmark.created_at < c["ts"])

    raw      = q.limit(limit + 1).all()
    has_more = len(raw) > limit
    raw      = raw[:limit]

    next_cursor = None
    if has_more and raw:
        bm = PostBookmark.query.filter_by(
            user_id=user_id, shared_outfit_id=raw[-1].id
        ).first()
        if bm:
            next_cursor = _encode_cursor(raw[-1].id, bm.created_at)

    return jsonify({
        "posts":      [_post_to_dict(p, user_id) for p in raw],
        "pagination": {"next_cursor": next_cursor, "has_more": has_more},
    }), 200


# ── Remix ─────────────────────────────────────────────────────────────────────

@social_bp.route("/posts/<int:post_id>/remix", methods=["POST"])
@jwt_required()
def remix_post(post_id: int):
    user_id = int(get_jwt_identity())

    post = db.session.get(SharedOutfit, post_id)
    if post is None:
        return jsonify({"error": "Post not found."}), 404
    if post.user_id == user_id:
        return jsonify({"error": "Cannot remix your own post."}), 400
    if not _is_post_visible(post, user_id):
        return jsonify({"error": "Access denied."}), 403

    # Get the source item IDs
    if post.saved_outfit is None:
        return jsonify({"error": "Source outfit no longer available."}), 422
    try:
        source_item_ids: list[int] = json.loads(post.saved_outfit.item_ids) if post.saved_outfit.item_ids else []
    except (json.JSONDecodeError, TypeError):
        source_item_ids = []

    if not source_item_ids:
        return jsonify({"error": "Source outfit has no items."}), 422

    # Get remixer's wardrobe
    my_wardrobe = WardrobeItemDB.query.filter_by(user_id=user_id).all()
    if not my_wardrobe:
        return jsonify({"error": "Your wardrobe is empty. Add items to remix."}), 422

    from engine.remix import remix_outfit
    result = remix_outfit(source_item_ids, my_wardrobe)

    # Log the remix (even if partial)
    db.session.add(RemixLog(
        source_shared_outfit_id=post_id,
        remixer_user_id=user_id,
    ))
    SharedOutfit.query.filter_by(id=post_id).update(
        {"remix_count": SharedOutfit.remix_count + 1}
    )
    db.session.commit()

    # Serialise matches with source item info
    matches_out = []
    for m in result.matches:
        src_item = db.session.get(WardrobeItemDB, m.source_item_id)
        src_info = None
        if src_item:
            src_info = {
                "id":           src_item.id,
                "category":     src_item.category,
                "image_url":    f"/uploads/{src_item.image_filename}",
                "sub_category": src_item.sub_category,
            }
        candidates_out = [
            {
                "item_id":         c.item_id,
                "final_score":     c.final_score,
                "embedding_score": c.embedding_score,
                "color_score":     c.color_score,
                "formality_score": c.formality_score,
                "category":        c.category,
                "image_url":       c.image_url,
            }
            for c in m.candidates
        ]
        matches_out.append({
            "source_item":   src_info,
            "source_category": m.source_category,
            "candidates":    candidates_out,
        })

    return jsonify({
        "source_post_id":     post_id,
        "coverage":           result.coverage,
        "missing_categories": result.missing_categories,
        "can_remix":          result.can_remix,
        "matches":            matches_out,
        "remix_source_post_id": post_id,   # for PublishModal to set attribution
    }), 200


@social_bp.route("/posts/<int:post_id>/remix-chain", methods=["GET"])
def get_remix_chain(post_id: int):
    """Returns ancestor chain (up to 5 levels) and direct children."""
    post = db.session.get(SharedOutfit, post_id)
    if post is None:
        return jsonify({"error": "Post not found."}), 404

    # Walk up the ancestry chain
    ancestors: list[int] = []
    current = post
    for _ in range(5):
        if current.remix_source_post_id is None:
            break
        parent = db.session.get(SharedOutfit, current.remix_source_post_id)
        if parent is None:
            break
        ancestors.append(parent.id)
        current = parent
    ancestors.reverse()

    # Direct children
    children = (
        SharedOutfit.query
        .filter_by(remix_source_post_id=post_id)
        .filter(SharedOutfit.visibility == "public")
        .order_by(SharedOutfit.created_at.desc())
        .limit(6)
        .all()
    )

    return jsonify({
        "ancestors":    ancestors,
        "current":      post_id,
        "remix_depth":  len(ancestors),
        "remixes":      [{"id": c.id, "user": c.author.social_dict() if c.author else None} for c in children],
    }), 200


# ── Vibe reference data ───────────────────────────────────────────────────────

@social_bp.route("/vibes", methods=["GET"])
def list_vibes():
    _ensure_vibes_seeded()
    all_vibes = VibeTag.query.order_by(VibeTag.id).all()
    return jsonify({
        "global":     [v.to_dict() for v in all_vibes if v.region == "global"],
        "south-asian":[v.to_dict() for v in all_vibes if v.region == "south-asian"],
    }), 200


@social_bp.route("/vibes/trending", methods=["GET"])
def trending_vibes():
    _ensure_vibes_seeded()
    limit  = min(int(request.args.get("limit", 5)), 10)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    results = (
        db.session.query(
            VibeTag.id,
            VibeTag.slug,
            VibeTag.label,
            VibeTag.region,
            func.count(post_vibes.c.post_id).label("post_count"),
        )
        .join(post_vibes, VibeTag.id == post_vibes.c.vibe_id)
        .join(SharedOutfit, post_vibes.c.post_id == SharedOutfit.id)
        .filter(
            SharedOutfit.created_at >= cutoff,
            SharedOutfit.visibility == "public",
        )
        .group_by(VibeTag.id, VibeTag.slug, VibeTag.label, VibeTag.region)
        .order_by(func.count(post_vibes.c.post_id).desc())
        .limit(limit)
        .all()
    )

    # Fall back to most-used all-time if nothing posted in last 24h
    if not results:
        results = (
            db.session.query(
                VibeTag.id,
                VibeTag.slug,
                VibeTag.label,
                VibeTag.region,
                func.count(post_vibes.c.post_id).label("post_count"),
            )
            .join(post_vibes, VibeTag.id == post_vibes.c.vibe_id)
            .group_by(VibeTag.id, VibeTag.slug, VibeTag.label, VibeTag.region)
            .order_by(func.count(post_vibes.c.post_id).desc())
            .limit(limit)
            .all()
        )

    return jsonify([
        {"slug": r.slug, "label": r.label, "region": r.region, "post_count": r.post_count}
        for r in results
    ]), 200
