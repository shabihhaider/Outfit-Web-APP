"""
app/health/routes.py
Observability endpoints: /health and /metrics.

/health  — shallow liveness check + component status (DB, ML pipeline, VTO config).
/metrics — operational counters for dashboards (users, items, jobs, cache stats).
"""

from __future__ import annotations

import logging
import time

from flask import Blueprint, current_app, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import func, text

from app.extensions import db, limiter
from app.models_db import TryOnJob, User, WardrobeItemDB

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__)


# ── GET /health ──────────────────────────────────────────────────────────────

@health_bp.get("/health")
def health():
    """
    Liveness & readiness probe.

    Returns component-level status so HF Space / monitoring can detect
    partial failures (e.g. DB down but app running).
    """
    components = {}

    # 1. Database connectivity
    try:
        db.session.execute(text("SELECT 1"))
        components["database"] = "ok"
    except Exception as exc:
        logger.warning("Health check: DB unreachable — %s", exc)
        components["database"] = "unavailable"

    # 2. ML pipeline
    pipeline = getattr(current_app, "pipeline", None)
    components["ml_pipeline"] = "loaded" if pipeline is not None else "not_loaded"

    # 3. VTO engine configuration
    hf_token = (current_app.config.get("HF_TOKEN") or "").strip()
    components["vto_engine"] = "configured" if hf_token else "not_configured"

    # Overall status: healthy only if DB is reachable
    overall = "healthy" if components["database"] == "ok" else "degraded"

    return jsonify({
        "status": overall,
        "components": components,
    }), 200 if overall == "healthy" else 503


# ── GET /metrics ─────────────────────────────────────────────────────────────

@health_bp.get("/metrics")
@jwt_required()
@limiter.limit("30/minute")
def metrics():
    """
    Operational metrics for monitoring dashboards.

    Lightweight aggregates — requires JWT so user counts are not publicly exposed.
    """
    start = time.monotonic()

    data: dict = {}

    # User & wardrobe counts
    try:
        data["users_total"] = db.session.query(func.count(User.id)).scalar() or 0
        data["wardrobe_items_total"] = db.session.query(func.count(WardrobeItemDB.id)).scalar() or 0
    except Exception:
        data["users_total"] = -1
        data["wardrobe_items_total"] = -1

    # VTO job breakdown
    try:
        job_counts = (
            db.session.query(TryOnJob.status, func.count(TryOnJob.id))
            .group_by(TryOnJob.status)
            .all()
        )
        data["vto_jobs"] = {status: count for status, count in job_counts}
        data["vto_jobs"]["total"] = sum(count for _, count in job_counts)
    except Exception:
        data["vto_jobs"] = {}

    # Recommendation cache stats
    try:
        from app.cache import recommendation_cache
        data["recommendation_cache"] = recommendation_cache.stats()
    except Exception:
        data["recommendation_cache"] = {}

    duration_ms = (time.monotonic() - start) * 1000
    data["query_time_ms"] = round(duration_ms, 1)

    return jsonify(data), 200
