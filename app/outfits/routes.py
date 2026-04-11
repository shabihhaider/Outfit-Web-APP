"""
app/outfits/routes.py
Outfit history, saved outfits, and feedback endpoints.

Routes (all registered under /outfits prefix):
  GET    /outfits/history             — last 50 recommendation history entries
  POST   /outfits/saved               — save / favourite an outfit
  GET    /outfits/saved               — list all saved outfits
  DELETE /outfits/saved/<id>          — remove a saved outfit
  POST   /outfits/<history_id>/feedback — rate an outfit 👍/👎
"""

from __future__ import annotations

import json
import logging

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models_db import OutfitHistory, OutfitFeedback, SavedOutfit, WardrobeItemDB
from app.storage import get_public_url as _img_url

logger = logging.getLogger(__name__)

outfits_bp = Blueprint("outfits", __name__)

VALID_OCCASIONS    = {"casual", "formal", "wedding"}
VALID_CONFIDENCES  = {"high", "medium", "low"}
VALID_RATINGS      = {1, -1}


# ─── Private helper ───────────────────────────────────────────────────────────

def _fetch_items_for_display(item_ids: list[int]) -> list[dict]:
    """
    Bulk-fetch WardrobeItemDB rows for the given IDs and return formatted dicts.
    Items that have been deleted from the wardrobe are silently omitted.
    """
    if not item_ids:
        return []
    rows = WardrobeItemDB.query.filter(WardrobeItemDB.id.in_(item_ids)).all()
    item_map = {row.id: row for row in rows}
    result = []
    for iid in item_ids:
        row = item_map.get(iid)
        if row:
            result.append({
                "id":        row.id,
                "category":  row.category,
                "image_url": _img_url(row.image_filename),
            })
    return result


# ─── GET /outfits/history ─────────────────────────────────────────────────────

@outfits_bp.route("/history", methods=["GET"])
@jwt_required()
def get_history():
    """
    GET /outfits/history
    Returns the last 50 outfit recommendation entries for the authenticated user.
    """
    user_id = int(get_jwt_identity())

    entries = (
        OutfitHistory.query
        .filter_by(user_id=user_id)
        .order_by(OutfitHistory.logged_at.desc())
        .limit(50)
        .all()
    )

    history = []
    for entry in entries:
        item_ids: list[int] = json.loads(entry.item_ids)
        history.append({
            "id":               entry.id,
            "occasion":         entry.occasion,
            "temperature_used": entry.temperature_used,
            "confidence":       entry.confidence,
            "final_score":      entry.final_score,
            "template":         entry.template,
            "logged_at":        entry.logged_at.isoformat() if entry.logged_at else None,
            "items":            _fetch_items_for_display(item_ids),
        })

    return jsonify({"history": history, "count": len(history)}), 200


# ─── POST /outfits/saved ──────────────────────────────────────────────────────

@outfits_bp.route("/saved", methods=["POST"])
@jwt_required()
def save_outfit():
    """
    POST /outfits/saved
    Body: {name, occasion, item_ids, final_score, confidence}
    """
    user_id = int(get_jwt_identity())
    data    = request.get_json(silent=True) or {}

    # Validate required fields
    name        = str(data.get("name", "")).strip()
    occasion    = str(data.get("occasion", "")).strip().lower()
    item_ids    = data.get("item_ids")
    final_score = data.get("final_score")
    confidence  = str(data.get("confidence", "")).strip().lower()

    if not name:
        return jsonify({"error": "'name' is required."}), 422
    if occasion not in VALID_OCCASIONS:
        return jsonify({"error": f"occasion must be one of: {', '.join(VALID_OCCASIONS)}."}), 422
    if not isinstance(item_ids, list) or not item_ids:
        return jsonify({"error": "'item_ids' must be a non-empty list."}), 422
    if final_score is None:
        return jsonify({"error": "'final_score' is required."}), 422
    if confidence not in VALID_CONFIDENCES:
        return jsonify({"error": f"confidence must be one of: {', '.join(VALID_CONFIDENCES)}."}), 422

    # Normalise item_ids so order doesn't matter when checking duplicates
    sorted_ids = sorted(int(i) for i in item_ids)

    # Check if the exact same item combination is already saved by this user
    existing_rows = SavedOutfit.query.filter_by(user_id=user_id).all()
    for row in existing_rows:
        try:
            existing_ids = sorted(json.loads(row.item_ids))
        except Exception:
            continue
        if existing_ids == sorted_ids:
            return jsonify({
                "error": f"This outfit combination is already saved as \"{row.name}\"."
            }), 409

    saved = SavedOutfit(
        user_id     = user_id,
        name        = name,
        occasion    = occasion,
        item_ids    = json.dumps(sorted_ids),
        final_score = float(final_score),
        confidence  = confidence,
    )
    db.session.add(saved)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": f"An outfit named '{name}' already exists."}), 409

    return jsonify({"id": saved.id, "name": saved.name, "message": "Outfit saved."}), 201


# ─── GET /outfits/saved ───────────────────────────────────────────────────────

@outfits_bp.route("/saved", methods=["GET"])
@jwt_required()
def list_saved():
    """GET /outfits/saved — all saved outfits for the authenticated user."""
    user_id = int(get_jwt_identity())

    rows = (
        SavedOutfit.query
        .filter_by(user_id=user_id)
        .order_by(SavedOutfit.saved_at.desc())
        .all()
    )

    saved = []
    for row in rows:
        item_ids: list[int] = json.loads(row.item_ids)
        saved.append({
            "id":          row.id,
            "name":        row.name,
            "occasion":    row.occasion,
            "confidence":  row.confidence,
            "final_score": row.final_score,
            "saved_at":    row.saved_at.isoformat() if row.saved_at else None,
            "items":       _fetch_items_for_display(item_ids),
        })

    return jsonify({"saved": saved, "count": len(saved)}), 200


# ─── DELETE /outfits/saved/<id> ───────────────────────────────────────────────

@outfits_bp.route("/saved/<int:saved_id>", methods=["DELETE"])
@jwt_required()
def delete_saved(saved_id: int):
    """DELETE /outfits/saved/<id>"""
    user_id = int(get_jwt_identity())

    row = db.session.get(SavedOutfit, saved_id)
    if row is None:
        return jsonify({"error": "Saved outfit not found."}), 404
    if row.user_id != user_id:
        return jsonify({"error": "Access forbidden."}), 403

    db.session.delete(row)
    db.session.commit()
    return jsonify({"message": "Outfit removed."}), 200


# ─── POST /outfits/<history_id>/feedback ─────────────────────────────────────

@outfits_bp.route("/<int:history_id>/feedback", methods=["POST"])
@jwt_required()
def submit_feedback(history_id: int):
    """
    POST /outfits/<history_id>/feedback
    Body: {rating: 1 or -1}
    """
    user_id = int(get_jwt_identity())
    data    = request.get_json(silent=True) or {}

    rating_raw = data.get("rating")
    if rating_raw not in VALID_RATINGS:
        return jsonify({"error": "rating must be 1 (thumbs up) or -1 (thumbs down)."}), 422

    # Verify history entry exists and belongs to this user
    entry = db.session.get(OutfitHistory, history_id)
    if entry is None:
        return jsonify({"error": "History entry not found."}), 404
    if entry.user_id != user_id:
        return jsonify({"error": "Access forbidden."}), 403

    feedback = OutfitFeedback(
        user_id    = user_id,
        history_id = history_id,
        rating     = int(rating_raw),
    )
    db.session.add(feedback)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "You have already rated this outfit."}), 409

    # Auto-run weight optimization every 20 feedback events.
    # Runs in a background thread so it never delays the HTTP response.
    # Requires ≥10 positive AND ≥10 negative events to be statistically meaningful.
    _maybe_optimize_weights_async()

    return jsonify({"message": "Feedback recorded."}), 201


# ─── Background weight optimizer ─────────────────────────────────────────────

# Optimization fires every N feedback events to avoid running on every single submit.
_OPTIMIZE_EVERY_N = 20


def _maybe_optimize_weights_async() -> None:
    """
    Check if enough feedback exists to optimize weights.
    If total feedback count is a multiple of _OPTIMIZE_EVERY_N, run optimization
    in a background thread so it never blocks the HTTP response.
    """
    try:
        total = OutfitFeedback.query.count()
        positives = OutfitFeedback.query.filter_by(rating=1).count()
        negatives = OutfitFeedback.query.filter_by(rating=-1).count()

        # Need enough data and hit a checkpoint
        if total % _OPTIMIZE_EVERY_N != 0:
            return
        if positives < 10 or negatives < 10:
            logger.info(
                "Weight optimizer: %d total feedback (%d+/%d-), need ≥10 each to optimize.",
                total, positives, negatives,
            )
            return

        # Run in background thread — do not import heavy libs on every request
        import threading
        from flask import current_app
        app = current_app._get_current_object()
        t = threading.Thread(
            target=_run_weight_optimization,
            args=(app, positives, negatives),
            daemon=True,
        )
        t.start()
    except Exception as exc:
        logger.warning("Weight optimizer check failed (non-fatal): %s", exc)


def _run_weight_optimization(app, positives: int, negatives: int) -> None:
    """
    Background thread: query all feedback + history scores, run AUC-ROC
    correlation analysis, log the result. Does NOT auto-apply weights —
    logs recommendation for the developer to review.
    """
    try:
        with app.app_context():
            from sqlalchemy import func as sqlfunc  # noqa: F401
            from app.extensions import db as _db

            # Join feedback with history to get (final_score, rating) pairs
            rows = (
                _db.session.query(OutfitHistory.final_score, OutfitFeedback.rating)
                .join(OutfitFeedback, OutfitFeedback.history_id == OutfitHistory.id)
                .all()
            )

            if len(rows) < 20:
                return

            import numpy as np
            scores  = np.array([r[0] for r in rows], dtype=float)
            ratings = np.array([r[1] for r in rows], dtype=float)
            binary  = (ratings > 0).astype(int)

            # AUC-ROC: how well does final_score predict positive feedback?
            from sklearn.metrics import roc_auc_score
            auc = roc_auc_score(binary, scores)

            # Pearson correlation
            corr = float(np.corrcoef(scores, binary)[0, 1])

            logger.info(
                "=== WEIGHT OPTIMIZER REPORT (%d feedback events) ===\n"
                "  AUC-ROC (final_score vs. positive feedback): %.4f\n"
                "  Pearson correlation: %.4f\n"
                "  Positive: %d | Negative: %d\n"
                "  Interpretation: %.1f%% of the time, scored-higher outfit also got thumbs-up.\n"
                "  Current weights: model2=0.45, color=0.25, weather=0.15, cohesion=0.15\n"
                "  %s",
                len(rows), auc, corr, positives, negatives, auc * 100,
                "Weights performing well (AUC > 0.65)." if auc > 0.65
                else "Consider re-tuning weights — run scripts/optimize_weights.py manually."
            )
    except Exception as exc:
        logger.warning("Background weight optimization failed (non-fatal): %s", exc)
