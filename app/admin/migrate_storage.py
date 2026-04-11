"""
app/admin/migrate_storage.py
One-time migration endpoint: copy files from old HF bucket (/data/uploads/)
to Supabase Storage.

Usage (after temporarily re-mounting the HF persistent storage volume):
  POST /admin/migrate-storage
  Header: X-Migrate-Token: <MIGRATE_SECRET>

Returns a JSON report of what was uploaded, skipped, and failed.
Set MIGRATE_SECRET env var on HF Space before calling.
"""

from __future__ import annotations

import logging
import os

from flask import Blueprint, current_app, jsonify, request

from app.models_db import SharedOutfit, TryOnJob, User, WardrobeItemDB
from app.storage import is_configured, upload_file_from_path

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__)

# Old HF persistent storage mount path
_OLD_MOUNT = "/data/uploads"


def _collect_filenames() -> list[str]:
    """Gather every image filename stored in the DB."""
    filenames: list[str] = []

    for row in User.query.filter(User.avatar_filename.isnot(None)).all():
        filenames.append(row.avatar_filename)

    for row in WardrobeItemDB.query.all():
        filenames.append(row.image_filename)

    for row in TryOnJob.query.filter(TryOnJob.result_filename.isnot(None)).all():
        filenames.append(row.result_filename)

    for row in SharedOutfit.query.filter(SharedOutfit.preview_image_filename.isnot(None)).all():
        filenames.append(row.preview_image_filename)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for fn in filenames:
        if fn and fn not in seen:
            seen.add(fn)
            unique.append(fn)
    return unique


@admin_bp.post("/admin/migrate-storage")
def migrate_storage():
    """
    POST /admin/migrate-storage
    Reads every image filename from DB, copies the file from the old HF
    persistent storage mount (/data/uploads/) to Supabase Storage.

    Protected by X-Migrate-Token header — set MIGRATE_SECRET env var.
    """
    secret = os.environ.get("MIGRATE_SECRET", "").strip()
    if not secret:
        return jsonify({"error": "MIGRATE_SECRET env var not set on this Space."}), 503

    provided = (request.headers.get("X-Migrate-Token") or "").strip()
    if provided != secret:
        return jsonify({"error": "Unauthorized."}), 401

    if not is_configured():
        return jsonify({"error": "Supabase Storage not configured (check SUPABASE_URL / SUPABASE_SERVICE_KEY)."}), 503

    old_dir = current_app.config.get("MIGRATE_SOURCE_DIR", _OLD_MOUNT)
    if not os.path.isdir(old_dir):
        return jsonify({
            "error": f"Source directory not found: {old_dir}",
            "hint": "Re-mount the HF persistent storage volume, then retry.",
        }), 400

    filenames = _collect_filenames()
    results = {"uploaded": [], "already_exists": [], "missing_locally": [], "failed": []}

    for filename in filenames:
        src_path = os.path.join(old_dir, filename)

        if not os.path.exists(src_path):
            results["missing_locally"].append(filename)
            continue

        try:
            public_url = upload_file_from_path(src_path, filename)
            if public_url.startswith("http"):
                results["uploaded"].append(filename)
                logger.info("Migrated %s → %s", filename, public_url)
            else:
                results["failed"].append({"file": filename, "reason": "upload returned local path"})
        except Exception as exc:
            results["failed"].append({"file": filename, "reason": str(exc)})
            logger.warning("Migration failed for %s: %s", filename, exc)

    summary = {
        "total_db_filenames": len(filenames),
        "uploaded": len(results["uploaded"]),
        "missing_locally": len(results["missing_locally"]),
        "failed": len(results["failed"]),
        "details": results,
    }
    logger.info("Storage migration complete: %s", summary)
    return jsonify(summary), 200
