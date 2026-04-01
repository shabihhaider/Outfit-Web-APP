"""
app/vto/routes.py
Virtual Try-On endpoints — powered by IDM-VTON on Hugging Face Spaces.

Architecture: pre-generation + persistent cache.
  - First time (user, item, person_photo) is tried:  background thread calls
    HF Spaces API (~60-90 s), result is saved and cached forever.
  - Every subsequent request for the same combination:  result served instantly
    from the local uploads/ folder.  Zero external calls.

Routes:
  POST   /vto/person-photo   — upload / replace user's VTO person photo
  GET    /vto/person-photo   — get person photo info (has_photo, url)
  POST   /vto/jobs           — submit try-on job; returns cached result or job_id
  GET    /vto/jobs/<id>      — poll job status: pending / processing / ready / failed
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import threading
import uuid
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models_db import TryOnJob, User, WardrobeItemDB
from app.utils import allowed_file, validate_image_content

logger = logging.getLogger(__name__)

vto_bp = Blueprint("vto", __name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _photo_hash(content: bytes) -> str:
    """SHA-256 hex digest of image bytes — used as cache key."""
    return hashlib.sha256(content).hexdigest()


def _person_photo_url(filename: str) -> str:
    return f"/uploads/{filename}"


# ─── POST /vto/person-photo ───────────────────────────────────────────────────

@vto_bp.route("/person-photo", methods=["POST"])
@jwt_required()
def upload_person_photo():
    """
    Upload or replace the user's VTO person photo.

    Stores the photo in uploads/ and records the filename on the User row.
    Any previous person photo file is deleted to save disk space.

    The same photo is reused for all future try-on jobs for this user,
    so the user only needs to do this once.
    """
    user_id = int(get_jwt_identity())

    if "photo" not in request.files:
        return jsonify({"error": "No photo file provided. Field name must be 'photo'."}), 400

    file = request.files["photo"]
    if not file.filename:
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename, current_app.config["ALLOWED_EXTENSIONS"]):
        return jsonify({"error": "File type not allowed. Use jpg or png."}), 400

    content = file.read()
    if not validate_image_content(content):
        return jsonify({"error": "File is not a valid image."}), 400

    user = db.session.get(User, user_id)

    # Delete previous person photo if it exists
    if user.profile_photo_filename:
        old_path = os.path.join(current_app.config["UPLOAD_FOLDER"], user.profile_photo_filename)
        try:
            if os.path.exists(old_path):
                os.remove(old_path)
        except OSError as exc:
            logger.warning("Could not delete old person photo %s: %s", old_path, exc)

        # Invalidate all existing try-on jobs for this user — person photo changed
        TryOnJob.query.filter_by(user_id=user_id).delete()
        db.session.flush()

    # Save new person photo
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"person_{user_id}_{uuid.uuid4().hex}.{ext}"
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, filename)

    with open(save_path, "wb") as f:
        f.write(content)

    user.profile_photo_filename = filename
    db.session.commit()

    logger.info("VTO: person photo saved for user %d → %s", user_id, filename)

    return jsonify({
        "message":   "Person photo saved.",
        "photo_url": _person_photo_url(filename),
        "filename":  filename,
    }), 201


# ─── GET /vto/person-photo ────────────────────────────────────────────────────

@vto_bp.route("/person-photo", methods=["GET"])
@jwt_required()
def get_person_photo():
    """Return whether the user has uploaded a person photo and its URL."""
    user_id = int(get_jwt_identity())
    user    = db.session.get(User, user_id)

    if not user.profile_photo_filename:
        return jsonify({"has_photo": False, "photo_url": None}), 200

    return jsonify({
        "has_photo": True,
        "photo_url": _person_photo_url(user.profile_photo_filename),
    }), 200


# ─── POST /vto/jobs ───────────────────────────────────────────────────────────

@vto_bp.route("/jobs", methods=["POST"])
@jwt_required()
def submit_tryon():
    """
    Submit a Virtual Try-On job.

    Body (JSON): { "item_id": <int> }

    Flow:
      1. Verify the user owns the item and has uploaded a person photo.
      2. Compute the person photo hash (cache key).
      3. If a completed job exists for (user, item, person_photo_hash) → return
         the cached result immediately (status: "ready").
      4. If a job is pending/processing → return the existing job (no duplicate).
      5. Otherwise → create a new job row, fire a background thread, return the
         job_id so the frontend can poll GET /vto/jobs/<id>.
    """
    user_id = int(get_jwt_identity())
    data    = request.get_json(silent=True) or {}
    item_id = data.get("item_id")

    if not item_id:
        return jsonify({"error": "item_id is required."}), 422

    # ── Ownership check ───────────────────────────────────────────────────────
    item = db.session.get(WardrobeItemDB, item_id)
    if item is None:
        return jsonify({"error": "Item not found."}), 404
    if item.user_id != user_id:
        return jsonify({"error": "Access forbidden."}), 403

    # ── Person photo check ────────────────────────────────────────────────────
    user = db.session.get(User, user_id)
    if not user.profile_photo_filename:
        return jsonify({
            "error":        "No person photo uploaded yet.",
            "needs_photo":  True,
        }), 422

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    person_path = os.path.join(upload_dir, user.profile_photo_filename)
    if not os.path.exists(person_path):
        # File missing — clear stale reference
        user.profile_photo_filename = None
        db.session.commit()
        return jsonify({
            "error":       "Person photo file not found. Please re-upload.",
            "needs_photo": True,
        }), 422

    garment_path = os.path.join(upload_dir, item.image_filename)
    if not os.path.exists(garment_path):
        return jsonify({"error": "Garment image file not found."}), 500

    # ── Compute cache key ─────────────────────────────────────────────────────
    with open(person_path, "rb") as f:
        person_hash = _photo_hash(f.read())

    # ── Cache lookup ──────────────────────────────────────────────────────────
    existing = (
        TryOnJob.query
        .filter_by(user_id=user_id, item_id=item_id, person_photo_hash=person_hash)
        .order_by(TryOnJob.created_at.desc())
        .first()
    )

    if existing:
        if existing.status == "ready":
            # Cache hit — instant result
            logger.info("VTO cache hit: job %d (user=%d, item=%d)", existing.id, user_id, item_id)
            return jsonify({**existing.to_dict(), "cached": True}), 200

        if existing.status in ("pending", "processing"):
            # Already running — return the existing job for polling
            return jsonify({**existing.to_dict(), "cached": False}), 202

        # Previous attempt failed — allow retry by falling through to create new job

    # ── Create job ────────────────────────────────────────────────────────────
    hf_token = current_app.config.get("HF_TOKEN", "")
    if not hf_token:
        return jsonify({
            "error": "HF_TOKEN not configured. Virtual Try-On is unavailable."
        }), 503

    job = TryOnJob(
        user_id           = user_id,
        item_id           = item_id,
        person_photo_hash = person_hash,
        status            = "pending",
    )
    db.session.add(job)
    db.session.commit()

    # ── Fire background thread ────────────────────────────────────────────────
    app = current_app._get_current_object()  # type: ignore[attr-defined]
    t = threading.Thread(
        target  = _run_tryon_job,
        args    = (app, job.id, person_path, garment_path, hf_token, upload_dir),
        daemon  = True,
        name    = f"vto-job-{job.id}",
    )
    t.start()

    logger.info("VTO job %d submitted (user=%d, item=%d)", job.id, user_id, item_id)

    return jsonify({**job.to_dict(), "cached": False}), 202


# ─── GET /vto/jobs/<id> ───────────────────────────────────────────────────────

@vto_bp.route("/jobs/<int:job_id>", methods=["GET"])
@jwt_required()
def get_job_status(job_id: int):
    """Poll the status of a try-on job."""
    user_id = int(get_jwt_identity())
    job     = db.session.get(TryOnJob, job_id)

    if job is None:
        return jsonify({"error": "Job not found."}), 404
    if job.user_id != user_id:
        return jsonify({"error": "Access forbidden."}), 403

    return jsonify(job.to_dict()), 200


# ─── Background worker ────────────────────────────────────────────────────────

def _run_tryon_job(
    app,
    job_id:       int,
    person_path:  str,
    garment_path: str,
    hf_token:     str,
    upload_dir:   str,
) -> None:
    """
    Background thread: calls IDM-VTON on HF Spaces and saves the result.

    Uses gradio_client to call the public yisol/IDM-VTON Space.
    The HF token ties the request to the user's free quota (3.5 min/day GPU)
    rather than the lower unauthenticated limit.

    Result image is copied to uploads/ and the job row is updated to 'ready'.
    On any failure the job is marked 'failed' with a descriptive error message.
    """
    with app.app_context():
        job = db.session.get(TryOnJob, job_id)
        if not job:
            return

        # Mark processing so the frontend can show a progress indicator
        job.status = "processing"
        db.session.commit()

        # Retry logic for rate-limited API
        max_retries = 3
        attempt = 0
        success = False

        import time

        while attempt < max_retries and not success:
            attempt += 1
            try:
                from gradio_client import Client, handle_file  # type: ignore[import]

                logger.info("VTO job %d: connecting to IDM-VTON Space (attempt %d/%d)...", job_id, attempt, max_retries)
                client = Client("yisol/IDM-VTON", token=hf_token or None)

                result = client.predict(
                    dict={
                        "background": handle_file(person_path),
                        "layers":     [],
                        "composite":  None,
                    },
                    garm_img      = handle_file(garment_path),
                    garment_des   = "clothing item",
                    is_checked     = True,
                    is_checked_crop= False,
                    denoise_steps  = 30,
                    seed           = 42,
                    api_name       = "/tryon",
                )

                # result is a tuple: (tryon_result_path, masked_person_image_path)
                # For yisol/IDM-VTON, index 0 is the final composite result.
                if isinstance(result, (list, tuple)) and len(result) > 0:
                    result_source = result[0]
                else:
                    result_source = result

                result_filename = f"tryon_{job_id}_{uuid.uuid4().hex[:8]}.png"
                result_path     = os.path.join(upload_dir, result_filename)
                
                # Ensure result_source is a string/path
                shutil.copy(str(result_source), result_path)

                job.status          = "ready"
                job.result_filename = result_filename
                job.completed_at    = datetime.now(timezone.utc)
                db.session.commit()
                success = True

                logger.info("VTO job %d: completed → %s", job_id, result_filename)

            except Exception as exc:
                error_str = str(exc)
                if "Too many requests" in error_str and attempt < max_retries:
                    wait_time = 5 * attempt
                    logger.warning("VTO job %d: Rate limited on attempt %d. Retrying in %ds...", job_id, attempt, wait_time)
                    time.sleep(wait_time)
                    continue
                
                job.status       = "failed"
                job.error_msg    = f"{type(exc).__name__}: {error_str}"[:500]
                job.completed_at = datetime.now(timezone.utc)
                db.session.commit()
                logger.error("VTO job %d failed: %s", job_id, exc)
                break
