"""
app/recommendations/routes.py
POST /recommendations              — generate outfit recommendations
POST /recommendations/around-item/<item_id> — anchor-item recommendations
GET  /recommendations/ootd         — outfit of the day
POST /recommendations/score-outfit — live outfit scoring for editor

Two request paths (POST endpoints):
  Path A — auto weather:  {"occasion": "casual", "lat": 31.52, "lon": 74.36}
  Path B — manual temp:   {"occasion": "formal", "temp_celsius": 35.0}
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

from app.cache import recommendation_cache
from app.extensions import db, limiter
from app.models_db import User, WardrobeItemDB, OutfitHistory
from app.storage import get_public_url as _img_url
from app.utils import item_db_to_engine

logger = logging.getLogger(__name__)

recommendations_bp = Blueprint("recommendations", __name__)

VALID_OCCASIONS = {"casual", "formal"}


def _with_private_cache(response):
    """Apply short-lived private cache headers for authenticated data responses."""
    response.headers["Cache-Control"] = "private, max-age=60, stale-while-revalidate=300"
    response.headers["Vary"] = "Authorization"
    return response


# ─── Private helpers ──────────────────────────────────────────────────────────

def _missing_categories_hint(items_db: list) -> str:
    """
    Inspect the user's wardrobe and return a helpful hint about what categories
    are needed to form a valid outfit template.

    Valid templates require at minimum:
      - top + bottom + shoes  (Template A)
      - dress + shoes         (Template D)
      - jumpsuit + shoes      (Template F)

    Returns a plain-English string describing what is missing.
    """
    cats = {item.category for item in items_db}

    has_shoes    = "shoes"    in cats
    has_top      = "top"      in cats
    has_bottom   = "bottom"   in cats
    has_dress    = "dress"    in cats
    has_jumpsuit = "jumpsuit" in cats

    # Check if any valid template is satisfiable
    template_standard = (has_top and has_bottom and has_shoes) or (has_dress and has_shoes) or (has_jumpsuit and has_shoes)
    template_basic    = (has_top and has_bottom) or has_dress or has_jumpsuit

    if template_standard:
        # Standard templates are satisfiable — likely a formality issue
        return (
            "No items matched this occasion's formality requirements. "
            "Try changing the occasion or update your items' formality tags."
        )

    if template_basic:
        # Basic templates are satisfiable but shoe-less — likely formality issue for shoe-less variants
        return (
            "No items matched this occasion's formality requirements. "
            "Try updating your items' formality tags to 'formal' or 'both', and consider uploading shoes for a complete Look."
        )

    # Build a specific missing-categories message
    missing = []
    if not (has_top or has_dress or has_jumpsuit):
        missing.append("a top, dress, or jumpsuit")
    if has_top and not has_bottom:
        missing.append("a bottom (trousers, skirt, etc.)")

    if missing:
        return (
            f"Cannot form a basic outfit. Missing: {', '.join(missing)}. "
            "Upload more items to get recommendations."
        )

    return (
        "Not enough wardrobe items to form a basic outfit. "
        "Upload at least a top and bottom to get started."
    )


def _resolve_temperature(data: dict, pipeline) -> tuple[float | None, tuple | None]:
    """
    Parse temperature from request data.
    Returns (temp_celsius, None) on success or (None, (response, status)) on error.
    """
    from engine.models import WeatherLocationError, WeatherAPIError

    lat              = data.get("lat")
    lon              = data.get("lon")
    temp_celsius_raw = data.get("temp_celsius")

    if lat is not None and lon is not None:
        try:
            return pipeline.get_temperature(float(lat), float(lon)), None
        except WeatherLocationError:
            return None, (jsonify({"error": "Location required. Provide lat/lon or enter temperature manually."}), 400)
        except WeatherAPIError:
            return None, (jsonify({"error": "Weather service unavailable. Please enter temperature manually."}), 503)
        except Exception as exc:
            logger.error("Weather API error: %s", exc)
            return None, (jsonify({"error": "Weather service unavailable. Please enter temperature manually."}), 503)

    if temp_celsius_raw is not None:
        try:
            return float(temp_celsius_raw), None
        except (TypeError, ValueError):
            return None, (jsonify({"error": "temp_celsius must be a number."}), 422)

    return None, (jsonify({"error": "Provide either lat/lon or temp_celsius."}), 400)


def _format_outfits_response(
    outfits: list,
    filename_map: dict[int, str],
    temp_celsius: float,
    occasion: str,
) -> dict:
    """Build the JSON-serialisable response dict for recommendation results."""
    has_low_confidence = any(o.confidence == "low" for o in outfits)
    warning = "Some outfits have low confidence scores." if has_low_confidence else None

    formatted_outfits = []
    for rank, outfit in enumerate(outfits, start=1):
        outfit_items = []
        for eng_item in outfit.items:
            img_filename = filename_map.get(eng_item.item_id, "")
            outfit_items.append({
                "id":        eng_item.item_id,
                "category":  eng_item.category.value,
                "image_url": _img_url(img_filename),
            })
        formatted_outfits.append({
            "rank":           rank,
            "final_score":    round(outfit.final_score, 4),
            "confidence":     outfit.confidence,
            "model2_score":   round(outfit.model2_score, 4),
            "color_score":    round(outfit.color_score, 4),
            "weather_score":  round(outfit.weather_score, 4),
            "cohesion_score": round(outfit.cohesion_score, 4),
            "synergy_score":  round(outfit.synergy_score, 4),
            "items":          outfit_items,
            "template":       outfit.template_id.value if outfit.template_id else None,
        })

    return {
        "outfits":            formatted_outfits,
        "has_low_confidence": has_low_confidence,
        "warning":            warning,
        "temperature_used":   round(temp_celsius, 1),
        "occasion":           occasion,
    }


def _log_history(user_id: int, occasion: str, temp_celsius: float, outfits: list) -> None:
    """
    Persist each outfit in `outfits` to outfit_history.
    Called after a successful recommendation — failures are logged but do NOT
    abort the recommendation response.
    """
    try:
        for outfit in outfits:
            entry = OutfitHistory(
                user_id          = user_id,
                occasion         = occasion,
                temperature_used = temp_celsius,
                item_ids         = json.dumps([item.item_id for item in outfit.items]),
                final_score      = outfit.final_score,
                confidence       = getattr(outfit.confidence, 'value', str(outfit.confidence)),
                template         = getattr(outfit.template_id, 'value', str(outfit.template_id)) if outfit.template_id else '',
            )
            db.session.add(entry)
        db.session.commit()
        logger.info("Logged %d outfit(s) to history for user %s", len(outfits), user_id)
    except Exception as exc:
        db.session.rollback()
        logger.error("Failed to log outfit history: %s", exc, exc_info=True)


# ─── POST /recommendations ────────────────────────────────────────────────────

@recommendations_bp.route("/recommendations", methods=["POST"])
@jwt_required()
@limiter.limit("10 per minute")
def recommend():
    """
    POST /recommendations
    Body (JSON): {occasion, lat?, lon?} or {occasion, temp_celsius?}
    """
    user_id = int(get_jwt_identity())
    data    = request.get_json(silent=True) or {}

    # 1. Validate occasion
    occasion = str(data.get("occasion", "")).strip().lower()
    if occasion not in VALID_OCCASIONS:
        return jsonify({"error": f"occasion must be one of: {', '.join(VALID_OCCASIONS)}."}), 422

    # 2. Resolve temperature
    temp_celsius, err = _resolve_temperature(data, current_app.pipeline)
    if err:
        return err

    # 3. Check cache
    cached = recommendation_cache.get(user_id, occasion, temp_celsius)
    if cached is not None:
        logger.debug("Cache HIT for user=%s occasion=%s", user_id, occasion)
        return _with_private_cache(jsonify(cached)), 200

    # 4. Load wardrobe
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "User not found."}), 404

    items_db = (
        WardrobeItemDB.query
        .filter_by(user_id=user_id, is_archived=False)
        .order_by(WardrobeItemDB.created_at.desc())
        .all()
    )
    wardrobe = [item_db_to_engine(item) for item in items_db]

    # 5. Run recommendation pipeline
    from engine.models import InsufficientWardrobeError
    try:
        outfits = current_app.pipeline.recommend(
            wardrobe      = wardrobe,
            occasion      = occasion,
            temp_celsius  = temp_celsius,
            gender_filter = user.gender,
        )
    except InsufficientWardrobeError:
        return jsonify({"error": _missing_categories_hint(items_db)}), 422
    except Exception as exc:
        logger.error("Recommendation engine error: %s", exc)
        return jsonify({"error": "Recommendation engine failed. Please try again."}), 500

    # 6. Auto-log each outfit to history
    _log_history(user_id, occasion, temp_celsius, outfits)

    # 7. Format, cache, and return response
    filename_map = {item.id: item.image_filename for item in items_db}
    response_data = _format_outfits_response(outfits, filename_map, temp_celsius, occasion)
    recommendation_cache.put(user_id, occasion, temp_celsius, response_data)
    return _with_private_cache(jsonify(response_data)), 200


# ─── POST /recommendations/around-item/<item_id> ─────────────────────────────

@recommendations_bp.route("/recommendations/around-item/<int:item_id>", methods=["POST"])
@jwt_required()
@limiter.limit("10 per minute")
def recommend_around_item(item_id: int):
    """
    POST /recommendations/around-item/<item_id>
    Builds outfits that must include the specified wardrobe item.
    Body: same as POST /recommendations (occasion + temp source).
    """
    user_id = int(get_jwt_identity())
    data    = request.get_json(silent=True) or {}

    # 1. Validate occasion
    occasion = str(data.get("occasion", "")).strip().lower()
    if occasion not in VALID_OCCASIONS:
        return jsonify({"error": f"occasion must be one of: {', '.join(VALID_OCCASIONS)}."}), 422

    # 2. Verify anchor item ownership
    anchor_db = db.session.get(WardrobeItemDB, item_id)
    if anchor_db is None:
        return jsonify({"error": "Item not found."}), 404
    if anchor_db.user_id != user_id:
        return jsonify({"error": "Access forbidden."}), 403

    # 3. Resolve temperature
    temp_celsius, err = _resolve_temperature(data, current_app.pipeline)
    if err:
        return err

    # 4. Load wardrobe
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "User not found."}), 404

    items_db = (
        WardrobeItemDB.query
        .filter_by(user_id=user_id, is_archived=False)
        .order_by(WardrobeItemDB.created_at.desc())
        .all()
    )
    wardrobe = [item_db_to_engine(item) for item in items_db]

    # 5. Run pipeline with anchor
    from engine.models import InsufficientWardrobeError
    try:
        outfits = current_app.pipeline.recommend(
            wardrobe        = wardrobe,
            occasion        = occasion,
            temp_celsius    = temp_celsius,
            gender_filter   = user.gender,
            anchor_item_id  = item_id,
        )
    except InsufficientWardrobeError:
        return jsonify({"error": _missing_categories_hint(items_db)}), 422
    except Exception as exc:
        logger.error("Recommendation engine error (around-item): %s", exc)
        return jsonify({"error": "Recommendation engine failed. Please try again."}), 500

    # 6. Format and return response
    filename_map = {item.id: item.image_filename for item in items_db}
    return _with_private_cache(jsonify(_format_outfits_response(outfits, filename_map, temp_celsius, occasion))), 200


# ─── GET /recommendations/ootd ──────────────────────────────────────────────

@recommendations_bp.route("/recommendations/ootd", methods=["GET"])
@jwt_required()
@limiter.limit("10 per minute")
def outfit_of_the_day():
    """
    GET /recommendations/ootd?temp_celsius=25
    Returns a single best outfit suggestion for today.
    Uses user's most common occasion and avoids recently worn items.
    """
    user_id = int(get_jwt_identity())

    # 1. Resolve temperature
    temp_raw = request.args.get("temp_celsius")
    temp_celsius = 25.0  # default
    if temp_raw is not None:
        try:
            temp_celsius = float(temp_raw)
        except (TypeError, ValueError):
            return jsonify({"error": "temp_celsius must be a number."}), 422

    # 2. Determine preferred occasion from history (last 30 days)
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    occasion_counts = (
        db.session.query(OutfitHistory.occasion, func.count())
        .filter(OutfitHistory.user_id == user_id, OutfitHistory.logged_at >= cutoff)
        .group_by(OutfitHistory.occasion)
        .all()
    )
    occasion = max(occasion_counts, key=lambda x: x[1])[0] if occasion_counts else "casual"

    # 3. Load wardrobe
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": "User not found."}), 404

    items_db = WardrobeItemDB.query.filter_by(user_id=user_id).all()
    if not items_db:
        return _with_private_cache(jsonify({
            "outfit": None,
            "reason": "Your wardrobe is empty. Upload some items first.",
            "stats": {"preferred_occasion": occasion, "items_available": 0, "recently_worn_count": 0},
        })), 200

    wardrobe = [item_db_to_engine(item) for item in items_db]

    # 4. Find recently worn item IDs (last 7 days)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_histories = (
        OutfitHistory.query
        .filter(OutfitHistory.user_id == user_id, OutfitHistory.logged_at >= week_ago)
        .all()
    )
    recently_worn_ids = set()
    for h in recent_histories:
        try:
            recently_worn_ids.update(json.loads(h.item_ids))
        except (json.JSONDecodeError, TypeError):
            pass

    # 5. Run recommendation pipeline
    from engine.models import InsufficientWardrobeError
    try:
        outfits = current_app.pipeline.recommend(
            wardrobe      = wardrobe,
            occasion      = occasion,
            temp_celsius  = temp_celsius,
            gender_filter = user.gender,
        )
    except InsufficientWardrobeError:
        return _with_private_cache(jsonify({
            "outfit": None,
            "reason": _missing_categories_hint(items_db),
            "stats": {
                "preferred_occasion": occasion,
                "items_available": len(items_db),
                "recently_worn_count": len(recently_worn_ids),
            },
        })), 200
    except Exception as exc:
        logger.error("OOTD recommendation error: %s", exc)
        return jsonify({"error": "Could not generate outfit of the day."}), 500

    if not outfits:
        return _with_private_cache(jsonify({
            "outfit": None,
            "reason": "Could not find a suitable outfit. Try uploading more items.",
            "stats": {
                "preferred_occasion": occasion,
                "items_available": len(items_db),
                "recently_worn_count": len(recently_worn_ids),
            },
        })), 200

    # 6. Prefer outfits that avoid recently worn items
    filename_map = {item.id: item.image_filename for item in items_db}

    # 6b. Sort: fresh outfits first, then by score
    def _outfit_sort_key(o):
        ids = {item.item_id for item in o.items}
        is_fresh = not bool(ids & recently_worn_ids)
        return (int(is_fresh), o.final_score)

    outfits_sorted = sorted(outfits, key=_outfit_sort_key, reverse=True)
    top_outfits = outfits_sorted[:3]

    def _fmt_outfit(o):
        items_fmt = []
        for eng_item in o.items:
            img_filename = filename_map.get(eng_item.item_id, "")
            items_fmt.append({
                "id":        eng_item.item_id,
                "category":  eng_item.category.value,
                "image_url": _img_url(img_filename),
            })
        ids = {item.item_id for item in o.items}
        return {
            "items":            items_fmt,
            "final_score":      round(o.final_score, 4),
            "confidence":       getattr(o.confidence, 'value', str(o.confidence)),
            "model2_score":     round(o.model2_score, 4),
            "color_score":      round(o.color_score, 4),
            "weather_score":    round(o.weather_score, 4),
            "cohesion_score":   round(o.cohesion_score, 4),
            "synergy_score":    round(o.synergy_score, 4),
            "occasion":         occasion,
            "temperature_used": round(temp_celsius, 1),
            "is_fresh":         not bool(ids & recently_worn_ids),
        }

    has_shoes = any(item.category == "shoes" for item in items_db)

    return _with_private_cache(jsonify({
        "outfit":   _fmt_outfit(top_outfits[0]),
        "outfits":  [_fmt_outfit(o) for o in top_outfits],
        "stats": {
            "preferred_occasion":  occasion,
            "items_available":     len(items_db),
            "recently_worn_count": len(recently_worn_ids),
            "has_shoes":           has_shoes,
        },
    })), 200


# ─── POST /recommendations/score-outfit ─────────────────────────────────────

@recommendations_bp.route("/recommendations/score-outfit", methods=["POST"])
@jwt_required()
@limiter.limit("30 per minute")
def score_outfit_endpoint():
    """
    POST /recommendations/score-outfit
    Body: {item_ids: [1,4,7], occasion: "casual", temp_celsius: 25}
    Returns live scoring breakdown, rule violations, occasion mismatches,
    and swap suggestions for the outfit editor canvas.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    # 1. Validate item_ids
    item_ids_raw = data.get("item_ids")
    if not isinstance(item_ids_raw, list) or len(item_ids_raw) < 2:
        return jsonify({"error": "item_ids must be a list of at least 2 item IDs."}), 400

    # 2. Validate occasion
    occasion = str(data.get("occasion", "casual")).strip().lower()
    if occasion not in VALID_OCCASIONS:
        return jsonify({"error": f"occasion must be one of: {', '.join(VALID_OCCASIONS)}."}), 422

    # 3. Resolve temperature
    temp_celsius = 25.0
    temp_raw = data.get("temp_celsius")
    if temp_raw is not None:
        try:
            temp_celsius = float(temp_raw)
        except (TypeError, ValueError):
            return jsonify({"error": "temp_celsius must be a number."}), 422

    # 4. Fetch items and verify ownership
    items_db = (
        WardrobeItemDB.query
        .filter(WardrobeItemDB.id.in_(item_ids_raw), WardrobeItemDB.user_id == user_id)
        .all()
    )
    found_ids = {item.id for item in items_db}
    missing_ids = [iid for iid in item_ids_raw if iid not in found_ids]
    if missing_ids:
        return jsonify({"error": "Some items not found or not owned by you.", "missing_ids": missing_ids}), 403

    # 5. Convert to engine items
    engine_items = [item_db_to_engine(item) for item in items_db]
    # 6. Check hard rules (Gate 1)
    from engine.scorer import score_outfit as engine_score_outfit

    rule_violations = _check_rule_violations(engine_items)

    # 7. Check occasion mismatches (Gate 2)
    occasion_mismatches = _check_occasion_mismatches(engine_items, occasion)

    # 8. If hard rules fail, return without scoring
    if rule_violations:
        return jsonify({
            "valid": False,
            "final_score": None,
            "confidence": None,
            "breakdown": None,
            "rule_violations": rule_violations,
            "occasion_mismatches": occasion_mismatches,
            "suggestions": [],
        }), 200

    # 9. Score the outfit (Gate 3)
    try:
        result = engine_score_outfit(engine_items, current_app.pipeline.model2, temp_celsius)
    except Exception as exc:
        logger.error("Score-outfit engine error: %s", exc)
        return jsonify({"error": "Scoring engine failed. Please try again."}), 500

    # 10. Generate swap suggestions
    all_items_db = WardrobeItemDB.query.filter_by(user_id=user_id).all()
    all_engine = [item_db_to_engine(item) for item in all_items_db]
    all_filename_map = {item.id: item.image_filename for item in all_items_db}
    suggestions = _generate_swap_suggestions(
        engine_items, all_engine, occasion, temp_celsius,
        result.final_score, current_app.pipeline.model2, all_filename_map,
    )

    return jsonify({
        "valid": True,
        "final_score": round(result.final_score, 4),
        "confidence": result.confidence.value if hasattr(result.confidence, 'value') else result.confidence,
        "breakdown": {
            "model2_score":   round(result.model2_score, 4),
            "color_score":    round(result.color_score, 4),
            "weather_score":  round(result.weather_score, 4),
            "cohesion_score": round(result.cohesion_score, 4),
            "synergy_score":  round(result.synergy_score, 4),
            "weights": {"model2": 0.35, "color": 0.20, "weather": 0.15, "cohesion": 0.10, "synergy": 0.20},
        },
        "rule_violations": [],
        "occasion_mismatches": occasion_mismatches,
        "suggestions": suggestions,
    }), 200


def _check_rule_violations(items: list) -> list[str]:
    """Return human-readable descriptions of hard rule violations."""
    from engine.models import Category, Formality

    violations = []
    categories = [item.category for item in items]

    if Category.DRESS in categories and (Category.TOP in categories or Category.BOTTOM in categories):
        violations.append("A dress cannot be combined with a top or bottom.")

    if Category.JUMPSUIT in categories and (Category.TOP in categories or Category.BOTTOM in categories):
        violations.append("A jumpsuit cannot be combined with a top or bottom.")

    if Category.DRESS in categories and Category.JUMPSUIT in categories:
        violations.append("A dress and jumpsuit cannot be worn together.")

    if len(categories) != len(set(categories)):
        from collections import Counter
        dupes = [cat.value for cat, count in Counter(categories).items() if count > 1]
        violations.append(f"Duplicate categories: {', '.join(dupes)}.")

    strict = {item.formality for item in items if item.formality != Formality.BOTH}
    if Formality.CASUAL in strict and Formality.FORMAL in strict:
        violations.append("Cannot mix casual and formal items in one outfit.")

    return violations


def _check_occasion_mismatches(items: list, occasion: str) -> list[str]:
    """Return descriptions of items that don't match the occasion formality."""
    from engine.occasion_filter import OCCASION_RULES

    allowed = OCCASION_RULES.get(occasion, {"casual", "formal", "both"})
    mismatches = []
    for item in items:
        formality_val = item.formality.value if hasattr(item.formality, 'value') else item.formality
        if formality_val not in allowed:
            cat_val = item.category.value if hasattr(item.category, 'value') else item.category
            mismatches.append(
                f"{cat_val.capitalize()} (tagged {formality_val}) doesn't match {occasion} occasion."
            )
    return mismatches


def _generate_swap_suggestions(
    items: list, all_wardrobe: list, occasion: str, temp_celsius: float,
    current_score: float, model2, filename_map: dict,
) -> list[dict]:
    """Generate top 3 swap suggestions that improve the outfit score."""
    from engine.hard_rules import passes_hard_rules
    from engine.scorer import score_outfit as engine_score_outfit
    from engine.occasion_filter import OCCASION_RULES

    current_ids = {item.item_id for item in items}
    allowed_formalities = OCCASION_RULES.get(occasion, {"casual", "formal", "both"})
    suggestions = []

    for idx, item in enumerate(items):
        alternatives = [
            w for w in all_wardrobe
            if w.category == item.category
            and w.item_id != item.item_id
            and w.item_id not in current_ids
            and (w.formality.value if hasattr(w.formality, 'value') else w.formality) in allowed_formalities
        ]
        for alt in alternatives[:3]:
            trial = items[:idx] + [alt] + items[idx + 1:]
            if not passes_hard_rules(trial):
                continue
            try:
                trial_result = engine_score_outfit(trial, model2, temp_celsius)
                delta = trial_result.final_score - current_score
                if delta > 0.03:
                    img_fn = filename_map.get(alt.item_id, "")
                    cat_val = alt.category.value if hasattr(alt.category, 'value') else alt.category
                    suggestions.append({
                        "action": "swap",
                        "remove_item_id": item.item_id,
                        "remove_item_category": item.category.value if hasattr(item.category, 'value') else item.category,
                        "add_item_id": alt.item_id,
                        "add_item_category": cat_val,
                        "add_item_image": _img_url(img_fn) if img_fn else None,
                        "score_delta": round(delta, 4),
                        "new_score": round(trial_result.final_score, 4),
                    })
            except Exception:  # nosec B112 — skip items that fail scoring, batch continues
                continue

    suggestions.sort(key=lambda s: s["score_delta"], reverse=True)
    return suggestions[:3]
