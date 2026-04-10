"""
app/calendar/routes.py
Outfit calendar/planner endpoints.

Routes (all registered under /calendar prefix):
  GET    /calendar/plans?month=YYYY-MM  — plans for a month
  POST   /calendar/plans               — create a plan
  PATCH  /calendar/plans/<id>          — update a plan
  DELETE /calendar/plans/<id>          — delete a plan
"""

from __future__ import annotations

import json
import logging
from datetime import date

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models_db import OutfitPlan, SavedOutfit, WardrobeItemDB
from app.storage import get_public_url as _img_url

logger = logging.getLogger(__name__)

calendar_bp = Blueprint("calendar", __name__)

VALID_OCCASIONS = {"casual", "formal", "wedding"}


def _fetch_plan_items(item_ids: list[int]) -> list[dict]:
    """Fetch wardrobe items for display in plan responses."""
    if not item_ids:
        return []
    rows = WardrobeItemDB.query.filter(WardrobeItemDB.id.in_(item_ids)).all()
    item_map = {r.id: r for r in rows}
    return [
        {"id": r.id, "category": r.category, "image_url": _img_url(r.image_filename)}
        for iid in item_ids
        if (r := item_map.get(iid))
    ]


def _plan_to_response(plan: OutfitPlan) -> dict:
    """Convert an OutfitPlan to its API response dict."""
    d = plan.to_dict()
    # Resolve actual item images for display
    try:
        item_ids = json.loads(plan.item_ids) if plan.item_ids else []
    except (json.JSONDecodeError, TypeError):
        item_ids = []
    # If plan has a saved outfit, use its item_ids for display
    if plan.saved_outfit and not item_ids:
        try:
            item_ids = json.loads(plan.saved_outfit.item_ids) if plan.saved_outfit.item_ids else []
        except (json.JSONDecodeError, TypeError):
            item_ids = []
    d["items"] = _fetch_plan_items(item_ids)
    return d


# ─── GET /calendar/plans ────────────────────────────────────────────────────

@calendar_bp.route("/plans", methods=["GET"])
@jwt_required()
def get_plans():
    """
    GET /calendar/plans?month=YYYY-MM
    Returns all plans for the specified month.
    """
    user_id = int(get_jwt_identity())
    month_str = request.args.get("month", "").strip()

    if not month_str:
        return jsonify({"error": "month parameter is required (YYYY-MM)."}), 400

    try:
        parts = month_str.split("-")
        year = int(parts[0])
        month = int(parts[1])
        if month < 1 or month > 12:
            raise ValueError
        start_date = date(year, month, 1)
        # End date: first day of next month
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
    except (ValueError, IndexError):
        return jsonify({"error": "Invalid month format. Use YYYY-MM."}), 400

    plans = (
        OutfitPlan.query
        .filter(
            OutfitPlan.user_id == user_id,
            OutfitPlan.plan_date >= start_date,
            OutfitPlan.plan_date < end_date,
        )
        .order_by(OutfitPlan.plan_date)
        .all()
    )

    return jsonify({
        "plans": [_plan_to_response(p) for p in plans],
        "count": len(plans),
        "month": month_str,
    }), 200


# ─── POST /calendar/plans ───────────────────────────────────────────────────

@calendar_bp.route("/plans", methods=["POST"])
@jwt_required()
def create_plan():
    """
    POST /calendar/plans
    Body: {plan_date, occasion?, saved_outfit_id?, item_ids?, notes?}
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    # 1. Validate plan_date
    date_str = str(data.get("plan_date", "")).strip()
    if not date_str:
        return jsonify({"error": "plan_date is required (YYYY-MM-DD)."}), 400
    try:
        plan_date = date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    # 2. Validate occasion (optional)
    occasion = data.get("occasion")
    if occasion is not None:
        occasion = str(occasion).strip().lower()
        if occasion not in VALID_OCCASIONS:
            return jsonify({"error": f"occasion must be one of: {', '.join(VALID_OCCASIONS)}."}), 422

    # 3. Validate saved_outfit_id or item_ids
    saved_outfit_id = data.get("saved_outfit_id")
    item_ids_raw = data.get("item_ids")
    notes = data.get("notes")

    if notes is not None and len(str(notes)) > 200:
        return jsonify({"error": "notes must be 200 characters or less."}), 422

    if saved_outfit_id is None and (not isinstance(item_ids_raw, list) or len(item_ids_raw) == 0):
        return jsonify({"error": "Provide saved_outfit_id or item_ids."}), 400

    # Validate saved_outfit ownership
    item_ids_json = None
    if saved_outfit_id is not None:
        so = db.session.get(SavedOutfit, int(saved_outfit_id))
        if so is None:
            return jsonify({"error": "Saved outfit not found."}), 404
        if so.user_id != user_id:
            return jsonify({"error": "Access forbidden."}), 403
        # Store item_ids as backup
        item_ids_json = so.item_ids

    # Validate item_ids ownership
    if isinstance(item_ids_raw, list) and len(item_ids_raw) > 0:
        owned = WardrobeItemDB.query.filter(
            WardrobeItemDB.id.in_(item_ids_raw),
            WardrobeItemDB.user_id == user_id,
        ).count()
        if owned != len(item_ids_raw):
            return jsonify({"error": "Some items not found or not owned by you."}), 403
        item_ids_json = json.dumps(item_ids_raw)

    plan = OutfitPlan(
        user_id=user_id,
        plan_date=plan_date,
        occasion=occasion,
        saved_outfit_id=int(saved_outfit_id) if saved_outfit_id is not None else None,
        item_ids=item_ids_json,
        notes=str(notes).strip() if notes else None,
    )
    db.session.add(plan)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "You already have an outfit planned for this date."}), 409

    return jsonify(_plan_to_response(plan)), 201


# ─── PATCH /calendar/plans/<id> ──────────────────────────────────────────────

@calendar_bp.route("/plans/<int:plan_id>", methods=["PATCH"])
@jwt_required()
def update_plan(plan_id: int):
    """
    PATCH /calendar/plans/<id>
    Body: {occasion?, saved_outfit_id?, item_ids?, notes?}
    """
    user_id = int(get_jwt_identity())
    plan = db.session.get(OutfitPlan, plan_id)

    if plan is None:
        return jsonify({"error": "Plan not found."}), 404
    if plan.user_id != user_id:
        return jsonify({"error": "Access forbidden."}), 403

    data = request.get_json(silent=True) or {}

    # Update occasion
    if "occasion" in data:
        occasion = data["occasion"]
        if occasion is not None:
            occasion = str(occasion).strip().lower()
            if occasion not in VALID_OCCASIONS:
                return jsonify({"error": f"occasion must be one of: {', '.join(VALID_OCCASIONS)}."}), 422
        plan.occasion = occasion

    # Update saved_outfit_id
    if "saved_outfit_id" in data:
        so_id = data["saved_outfit_id"]
        if so_id is not None:
            so = db.session.get(SavedOutfit, int(so_id))
            if so is None:
                return jsonify({"error": "Saved outfit not found."}), 404
            if so.user_id != user_id:
                return jsonify({"error": "Access forbidden."}), 403
            plan.saved_outfit_id = so.id
            # Update item_ids backup from saved outfit
            plan.item_ids = so.item_ids
        else:
            plan.saved_outfit_id = None

    # Update item_ids
    if "item_ids" in data:
        item_ids_raw = data["item_ids"]
        if isinstance(item_ids_raw, list) and len(item_ids_raw) > 0:
            owned = WardrobeItemDB.query.filter(
                WardrobeItemDB.id.in_(item_ids_raw),
                WardrobeItemDB.user_id == user_id,
            ).count()
            if owned != len(item_ids_raw):
                return jsonify({"error": "Some items not found or not owned by you."}), 403
            plan.item_ids = json.dumps(item_ids_raw)
        elif item_ids_raw is None or (isinstance(item_ids_raw, list) and len(item_ids_raw) == 0):
            plan.item_ids = None

    # Update notes
    if "notes" in data:
        notes = data["notes"]
        if notes is not None and len(str(notes)) > 200:
            return jsonify({"error": "notes must be 200 characters or less."}), 422
        plan.notes = str(notes).strip() if notes else None

    db.session.commit()
    return jsonify(_plan_to_response(plan)), 200


# ─── DELETE /calendar/plans/<id> ─────────────────────────────────────────────

@calendar_bp.route("/plans/<int:plan_id>", methods=["DELETE"])
@jwt_required()
def delete_plan(plan_id: int):
    """DELETE /calendar/plans/<id>"""
    user_id = int(get_jwt_identity())
    plan = db.session.get(OutfitPlan, plan_id)

    if plan is None:
        return jsonify({"error": "Plan not found."}), 404
    if plan.user_id != user_id:
        return jsonify({"error": "Access forbidden."}), 403

    db.session.delete(plan)
    db.session.commit()
    return jsonify({"message": "Plan deleted."}), 200
