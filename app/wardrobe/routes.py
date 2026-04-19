"""
app/wardrobe/routes.py
Wardrobe management endpoints: upload, list, delete items, stats, and serve images.

Two blueprints are exported:
  wardrobe_bp  — registered at /wardrobe prefix
  uploads_bp   — registered without prefix → /uploads/<filename>

Routes (wardrobe_bp):
  POST   /wardrobe/items        — upload a clothing item
  GET    /wardrobe/items        — list all items for the authenticated user
  PATCH  /wardrobe/items/<id>   — correct category or formality after upload
  DELETE /wardrobe/items/<id>   — remove an item
  GET    /wardrobe/stats        — wardrobe statistics and insights

Routes (uploads_bp, public — no JWT):
  GET    /uploads/<filename>    — serve an uploaded image (404 if not in DB)
"""

from __future__ import annotations

import json
import logging
import os
import uuid

from flask import (
    Blueprint, current_app, jsonify, redirect, request, send_from_directory,
)
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import limiter

from sqlalchemy import func

from app.audit import log_action
from app.cache import recommendation_cache
from app.extensions import db
from app.models_db import WardrobeItemDB, OutfitHistory, OutfitFeedback, SavedOutfit
from app.utils import allowed_file, validate_image_content, validate_clothing_photo, process_image_for_atelier

logger = logging.getLogger(__name__)

wardrobe_bp = Blueprint("wardrobe", __name__)
uploads_bp  = Blueprint("uploads",  __name__)

VALID_FORMALITIES = {"casual", "formal", "both"}
VALID_GENDERS     = {"men", "women", "unisex"}
VALID_CATEGORIES  = {"top", "bottom", "outwear", "shoes", "dress", "jumpsuit"}
IRREGULAR_PLURALS = {"shoes": "shoes", "dress": "dresses"}

UPLOAD_TIPS = [
    "Lay the item flat or hang it for best results.",
    "Ensure good lighting — avoid shadows across the item.",
    "Crop to show only the clothing item, not the background.",
]


def _pluralize_category(category: str) -> str:
    """Pluralize wardrobe category names with small irregular overrides."""
    return IRREGULAR_PLURALS.get(category, f"{category}s")


# ─── POST /wardrobe/items ─────────────────────────────────────────────────────

@wardrobe_bp.route("/items", methods=["POST"])
@jwt_required()
@limiter.limit("10/minute")
def upload_item():
    """
    POST /wardrobe/items  (multipart/form-data)
    Fields: image (file), formality (str), gender (str)

    Processing order (see PHASE5 plan §4):
      1. Wardrobe size guard (max 50)
      2. Validate extension
      3. Read content + Pillow verify()
      4. Validate formality / gender
      5. Save file
      6. classify_and_embed → (category, embedding, confidence)
      7. extract_color      → (hue, sat, val)
      8. Save DB record
      9. Return item details + upload tips
    """
    user_id = int(get_jwt_identity())

    # ── 1. Wardrobe size guard ────────────────────────────────────────────────
    item_count = WardrobeItemDB.query.filter_by(user_id=user_id).count()
    if item_count >= 50:
        return jsonify({
            "error": "Wardrobe is full. Maximum 50 items allowed. Please delete some items first."
        }), 400

    # ── 2. File presence + extension ─────────────────────────────────────────
    if "image" not in request.files:
        return jsonify({"error": "No image file provided."}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename, current_app.config["ALLOWED_EXTENSIONS"]):
        return jsonify({"error": "File type not allowed. Use jpg or png."}), 400

    # ── 3. Read content + Pillow verify ──────────────────────────────────────
    content = file.read()
    if not validate_image_content(content):
        return jsonify({"error": "File is not a valid image."}), 400

    # ── 3b. Clothing photo heuristic ─────────────────────────────────────────
    if not current_app.config.get("SKIP_CLOTHING_PHOTO_CHECK"):
        is_clothing, rejection_reason = validate_clothing_photo(content)
        if not is_clothing:
            return jsonify({"error": rejection_reason}), 422

    # ── 4. Validate form fields ───────────────────────────────────────────────
    formality = (request.form.get("formality") or "").strip().lower()
    gender    = (request.form.get("gender")    or "").strip().lower()

    if formality not in VALID_FORMALITIES:
        return jsonify({"error": f"formality must be one of: {', '.join(VALID_FORMALITIES)}."}), 422
    if gender not in VALID_GENDERS:
        return jsonify({"error": f"gender must be one of: {', '.join(VALID_GENDERS)}."}), 422

    # ── 5. Save file ──────────────────────────────────────────────────────────
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename  = f"{user_id}_{uuid.uuid4().hex}.{ext}"
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, filename)

    with open(save_path, "wb") as f:
        f.write(content)

    # ── 5b. Atelier image processing (background removal + normalization) ────────
    # Runs on every upload regardless of input format.
    # Produces a clean white-background PNG in a predictably-named file.
    # If processing fails, the original file is kept — upload is never blocked.
    atelier_filename = f"{user_id}_{uuid.uuid4().hex}_atelier.png"
    atelier_path     = os.path.join(upload_dir, atelier_filename)
    atelier_ok, bg_removed = process_image_for_atelier(save_path, atelier_path)
    if atelier_ok:
        try:
            os.remove(save_path)
        except OSError:
            pass
        filename  = atelier_filename
        save_path = atelier_path
        logger.info(
            "Atelier: processed upload → %s (bg_removed=%s)", filename, bg_removed
        )
    else:
        bg_removed = False
        logger.warning("Atelier: processing failed for %s — using original.", filename)

    # ── 5c. CLIP Zero-Shot OOD Detection ──────────────────────────────────────
    if not current_app.config.get("SKIP_CLOTHING_PHOTO_CHECK"):
        try:
            from engine.clip_tagger import get_tagger
            tagger = get_tagger()
            is_clothing, rejection_reason = tagger.is_clothing_image(save_path)
            if not is_clothing:
                os.remove(save_path)
                return jsonify({"error": rejection_reason}), 422
        except RuntimeError as exc:
            logger.warning("CLIP tagger unavailable for OOD check: %s", exc)
        except Exception as exc:
            logger.warning("CLIP OOD check failed for %s: %s", filename, exc)

    # ── 6. classify_and_embed ─────────────────────────────────────────────────
    try:
        category, embedding_array, model_confidence = current_app.pipeline.classify_and_embed(save_path)
        embedding_json = json.dumps(embedding_array.tolist())
    except ValueError as exc:
        os.remove(save_path)
        return jsonify({"error": str(exc)}), 422
    except Exception as exc:
        os.remove(save_path)
        logger.error("Model inference failed for %s: %s", save_path, exc)
        return jsonify({"error": "Model inference failed. Please try again."}), 500

    # ── 7. extract_color ──────────────────────────────────────────────────────
    try:
        hue, sat, val = current_app.pipeline.extract_color(save_path)
    except Exception as exc:
        os.remove(save_path)
        logger.error("Color extraction failed for %s: %s", save_path, exc)
        return jsonify({"error": "Color extraction failed. Please try again."}), 500

    # ── 7b. CLIP sub-category tagging (non-fatal) ─────────────────────────────
    # Uses CLIP ViT-B/32 zero-shot classification to detect fine-grained sub-category
    # (e.g. "kurta", "blazer", "jeans") without additional training.
    # Failure is logged but does not block the upload — sub_category stays None.
    sub_category    = None
    clip_confidence = None
    try:
        from engine.clip_tagger import get_tagger
        tagger = get_tagger()
        sub_category, clip_confidence = tagger.classify(save_path, category)
        logger.info("CLIP sub-category for %s (%s): %s (%.3f)", filename, category, sub_category, clip_confidence)
    except RuntimeError as exc:
        # transformers/torch not installed — CLIP is optional
        logger.warning("CLIP tagger unavailable (install transformers + torch to enable): %s", exc)
    except Exception as exc:
        logger.warning("CLIP sub-category tagging failed for %s: %s", filename, exc)

    # ── 8. Save to database ───────────────────────────────────────────────────
    item = WardrobeItemDB(
        user_id          = user_id,
        image_filename   = filename,
        category         = category,
        sub_category     = sub_category,
        formality        = formality,
        gender           = gender,
        embedding        = embedding_json,
        color_hue        = float(hue),
        color_sat        = float(sat),
        color_val        = float(val),
        model_confidence = model_confidence,
        clip_confidence  = float(clip_confidence) if clip_confidence is not None else None,
    )
    db.session.add(item)
    db.session.commit()
    recommendation_cache.invalidate_user(user_id)
    log_action("upload_item", user_id=user_id, detail=f"item_id={item.id} category={category}")

    # ── 9. Upload to Supabase Storage ────────────────────────────────────────
    actual_image_url = None
    try:
        from app.storage import upload_file_from_path
        actual_image_url = upload_file_from_path(save_path, filename)
    except Exception as exc:
        logger.warning("Supabase upload failed for %s: %s", filename, exc)

    # ── 10. Return with upload guidance ───────────────────────────────────────
    return jsonify({**item.to_dict(image_url=actual_image_url), "tips": UPLOAD_TIPS, "bg_removed": bg_removed}), 201


# ─── GET /wardrobe/items ──────────────────────────────────────────────────────

@wardrobe_bp.route("/items", methods=["GET"])
@jwt_required()
def list_items():
    """GET /wardrobe/items — return all wardrobe items for the authenticated user."""
    user_id = int(get_jwt_identity())
    items   = WardrobeItemDB.query.filter_by(user_id=user_id).order_by(WardrobeItemDB.created_at.desc()).all()
    response = jsonify({
        "items": [item.to_dict() for item in items],
        "count": len(items),
    })
    response.headers["Cache-Control"] = "private, max-age=60, stale-while-revalidate=300"
    response.headers["Vary"] = "Authorization"
    return response, 200


# ─── DELETE /wardrobe/items/<id> ──────────────────────────────────────────────

@wardrobe_bp.route("/items/<int:item_id>", methods=["DELETE"])
@jwt_required()
def delete_item(item_id: int):
    """
    DELETE /wardrobe/items/<id>
    Deletes the DB record and image file. Returns 403 if item belongs to another user.
    """
    user_id = int(get_jwt_identity())
    item    = db.session.get(WardrobeItemDB, item_id)

    if item is None:
        return jsonify({"error": "Item not found."}), 404
    if item.user_id != user_id:
        return jsonify({"error": "Access forbidden."}), 403

    # Delete image file from local disk and Supabase
    image_path = os.path.join(current_app.config["UPLOAD_FOLDER"], item.image_filename)
    try:
        if os.path.exists(image_path):
            os.remove(image_path)
    except OSError as exc:
        logger.warning("Could not delete image file %s: %s", image_path, exc)
    from app.storage import delete_file as storage_delete
    storage_delete(item.image_filename)

    db.session.delete(item)
    db.session.commit()
    recommendation_cache.invalidate_user(user_id)
    log_action("delete_item", user_id=user_id, detail=f"item_id={item_id}")
    return jsonify({"message": "Item deleted."}), 200


# ─── PATCH /wardrobe/items/<id> ───────────────────────────────────────────────

@wardrobe_bp.route("/items/<int:item_id>", methods=["PATCH"])
@jwt_required()
def edit_item(item_id: int):
    """
    PATCH /wardrobe/items/<id>
    Body (JSON): {category?, formality?}
    At least one field is required.
    """
    user_id = int(get_jwt_identity())
    item    = db.session.get(WardrobeItemDB, item_id)

    if item is None:
        return jsonify({"error": "Item not found."}), 404
    if item.user_id != user_id:
        return jsonify({"error": "Access forbidden."}), 403

    data = request.get_json(silent=True) or {}

    new_category     = data.get("category")
    new_formality    = data.get("formality")
    new_sub_category = data.get("sub_category")  # allow manual correction of CLIP label

    if new_category is None and new_formality is None and new_sub_category is None:
        return jsonify({"error": "Request body must include at least one of: category, formality, sub_category."}), 400

    if new_category is not None:
        new_category = str(new_category).strip().lower()
        if new_category not in VALID_CATEGORIES:
            return jsonify({"error": f"category must be one of: {', '.join(sorted(VALID_CATEGORIES))}."}), 422
        item.category = new_category

    if new_formality is not None:
        new_formality = str(new_formality).strip().lower()
        if new_formality not in VALID_FORMALITIES:
            return jsonify({"error": f"formality must be one of: {', '.join(VALID_FORMALITIES)}."}), 422
        item.formality = new_formality

    if new_sub_category is not None:
        item.sub_category = str(new_sub_category).strip().lower() or None

    db.session.commit()
    return jsonify(item.to_dict()), 200


# ─── GET /wardrobe/stats ─────────────────────────────────────────────────────

@wardrobe_bp.route("/stats", methods=["GET"])
@jwt_required()
def wardrobe_stats():
    """
    GET /wardrobe/stats
    Returns wardrobe statistics, activity summary, and insights for the user.
    """
    user_id = int(get_jwt_identity())

    # ── Category distribution ────────────────────────────────────────────────
    items = WardrobeItemDB.query.filter_by(user_id=user_id).all()
    total_items = len(items)

    categories = {}
    for cat in ["top", "bottom", "outwear", "shoes", "dress", "jumpsuit"]:
        categories[cat] = sum(1 for i in items if i.category == cat)

    # ── Color data ───────────────────────────────────────────────────────────
    colors = [
        {"hue": i.color_hue, "sat": i.color_sat, "val": i.color_val}
        for i in items
    ]

    # ── Formality distribution ───────────────────────────────────────────────
    formality = {}
    for f in ["casual", "formal", "both"]:
        formality[f] = sum(1 for i in items if i.formality == f)

    # ── Activity stats ───────────────────────────────────────────────────────
    total_recs = OutfitHistory.query.filter_by(user_id=user_id).count()
    avg_score_result = (
        db.session.query(func.avg(OutfitHistory.final_score))
        .filter_by(user_id=user_id)
        .scalar()
    )
    avg_score = round(float(avg_score_result), 4) if avg_score_result else None

    saved_count = SavedOutfit.query.filter_by(user_id=user_id).count()

    thumbs_up = OutfitFeedback.query.filter_by(user_id=user_id, rating=1).count()
    thumbs_down = OutfitFeedback.query.filter_by(user_id=user_id, rating=-1).count()

    # ── Most common occasion ─────────────────────────────────────────────────
    occasion_counts = (
        db.session.query(OutfitHistory.occasion, func.count())
        .filter_by(user_id=user_id)
        .group_by(OutfitHistory.occasion)
        .all()
    )
    most_common_occasion = max(occasion_counts, key=lambda x: x[1])[0] if occasion_counts else None

    # ── Items never used in any recommendation ───────────────────────────────
    all_item_ids = {i.id for i in items}
    used_ids = set()
    histories = OutfitHistory.query.filter_by(user_id=user_id).all()
    for h in histories:
        try:
            used_ids.update(json.loads(h.item_ids))
        except (json.JSONDecodeError, TypeError):
            pass
    never_used_ids = sorted(all_item_ids - used_ids)

    # ── Wardrobe balance insight ─────────────────────────────────────────────
    balance_tip = None
    if total_items > 0:
        # Check for imbalances
        has_tops = categories.get("top", 0)
        has_bottoms = categories.get("bottom", 0)
        has_shoes = categories.get("shoes", 0)

        if has_tops > 0 and has_bottoms == 0:
            balance_tip = "Your tops are ready — adding some pants or skirts will unlock complete outfit recommendations."
        elif has_bottoms > 0 and has_tops == 0:
            balance_tip = "Your bottoms are ready — adding some shirts or t-shirts will unlock complete outfit recommendations."
        elif has_shoes == 0 and total_items >= 3:
            balance_tip = "Great start! Adding footwear will unlock full 3-piece outfit recommendations."
        else:
            # Check for big imbalances
            max_cat = max(categories, key=categories.get)
            max_count = categories[max_cat]
            min_essentials = {k: v for k, v in categories.items() if k in ("top", "bottom", "shoes") and v > 0}
            if min_essentials:
                min_cat = min(min_essentials, key=min_essentials.get)
                min_count = min_essentials[min_cat]
                if max_count >= 3 * min_count and min_count > 0:
                    balance_tip = (
                        f"Your {_pluralize_category(max_cat)} are well-stocked! "
                        f"Adding more {_pluralize_category(min_cat)} could unlock more complete outfit looks."
                    )

    response = jsonify({
        "wardrobe": {
            "total_items": total_items,
            "capacity": 50,
            "categories": categories,
            "formality": formality,
            "colors": colors,
        },
        "activity": {
            "total_recommendations": total_recs,
            "avg_score": avg_score,
            "saved_outfits": saved_count,
            "feedback": {"thumbs_up": thumbs_up, "thumbs_down": thumbs_down},
        },
        "insights": {
            "never_used_item_ids": never_used_ids,
            "most_common_occasion": most_common_occasion,
            "wardrobe_balance": balance_tip,
        },
    })
    response.headers["Cache-Control"] = "private, max-age=60, stale-while-revalidate=300"
    response.headers["Vary"] = "Authorization"
    return response, 200


# ─── GET /uploads/<filename> ─────────────────────────────────────────────────
# Registered WITHOUT the /wardrobe prefix (via uploads_bp in create_app)

@uploads_bp.route("/uploads/<string:filename>")
def serve_upload(filename: str):
    """
    GET /uploads/<filename>
    Redirects to Supabase CDN when configured, otherwise serves from local disk.
    """
    from app.storage import is_configured, get_public_url

    if is_configured():
        response = redirect(get_public_url(filename), code=302)
        response.headers["Cache-Control"] = "public, max-age=86400"
        return response

    # Fallback for local dev without Supabase
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    response = send_from_directory(os.path.abspath(upload_dir), filename)
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response
