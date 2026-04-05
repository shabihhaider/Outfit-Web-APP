"""
app/vto/routes.py
Virtual Try-On endpoints — OutfitAI Neural Fitting Engine.

Architecture: pre-generation + persistent cache.
  - First time (user, item, person_photo) is tried:  background thread calls
    the VTO inference API (~5-15 s), result is saved and cached forever.
  - Every subsequent request for the same combination:  result served instantly
    from the local uploads/ folder.  Zero external calls.

Engine priority:
  1. FASHN VTON v1.5 via HF Space (fast, free ZeroGPU — requires HF_TOKEN)
  2. IDM-VTON via HF Space (slower fallback — requires HF_TOKEN)

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
import time
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


def _get_daily_usage(user_id: int) -> int:
    """
    Counts how many NEW Virtual Try-On jobs this user has submitted 
    in the last 24 hours. Cache hits do not count.
    """
    from datetime import timedelta
    now     = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)
    
    # We count jobs that are ready, pending, or processing.
    # Failed jobs do NOT count toward the daily limit (user shouldn't pay for errors).
    return TryOnJob.query.filter(
        TryOnJob.user_id == user_id,
        TryOnJob.created_at >= since_24h,
        TryOnJob.status != "failed"
    ).count()


def _person_photo_url(filename: str) -> str:
    return f"/uploads/{filename}"


def _extract_output_source(output) -> str:
    """Normalize model output payload into a URL/path string."""
    if output is None:
        return ""

    if isinstance(output, str):
        return output

    if isinstance(output, (list, tuple)) and output:
        return str(output[-1])

    if isinstance(output, dict):
        for key in ("output", "image", "url"):
            value = output.get(key)
            if value:
                return str(value)

    url_attr = getattr(output, "url", None)
    if callable(url_attr):
        try:
            return str(url_attr())
        except Exception:
            pass
    elif isinstance(url_attr, str):
        return url_attr

    return str(output)


def _is_rate_limited_error(error_str: str) -> bool:
    msg = (error_str or "").lower()
    return (
        "too many requests" in msg
        or "rate limit" in msg
        or "429" in msg
        or "queue is full" in msg
    )


def _clean_secret(value: str | None) -> str:
    """Normalize env secrets so whitespace-only values are treated as missing."""
    return (value or "").strip()


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

    usage = _get_daily_usage(user_id)
    return jsonify({
        "has_photo": True,
        "photo_url": _person_photo_url(user.profile_photo_filename),
        "quota": {
            "current": usage,
            "limit": 5
        }
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

    # ── Quota lookup (NEW requests only) ──────────────────────────────────────
    usage = _get_daily_usage(user_id)
    limit = 5
    if usage >= limit:
        return jsonify({
            "error": f"Daily limit reached ({usage}/{limit}). Please try again tomorrow.",
            "quota": {"current": usage, "limit": limit}
        }), 429

    # ── Create job ────────────────────────────────────────────────────────────
    hf_token       = _clean_secret(current_app.config.get("HF_TOKEN", ""))
    fashn_space_id = _clean_secret(current_app.config.get("HF_FASHN_SPACE_ID", "fashn-ai/fashn-vton-1.5")) or "fashn-ai/fashn-vton-1.5"
    hf_space_id    = _clean_secret(current_app.config.get("HF_VTO_SPACE_ID", "yisol/IDM-VTON")) or "yisol/IDM-VTON"
    if not hf_token:
        return jsonify({
            "error": "Virtual Try-On is not configured. Contact the administrator."
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
        args    = (app, job.id, person_path, garment_path, hf_token, fashn_space_id, hf_space_id, upload_dir),
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
    job_id:          int,
    person_path:     str,
    garment_path:    str,
    hf_token:        str,
    fashn_space_id:  str,
    hf_space_id:     str,
    upload_dir:      str,
) -> None:
    """
    Background worker: OutfitAI VTO Engine (hybrid).
    1. Try FASHN VTON v1.5 via HF Space (fast, free ZeroGPU).
    2. Fallback to IDM-VTON via HF Space (slower, shared).
    """
    with app.app_context():
        # Get Job & Item
        job = db.session.get(TryOnJob, job_id)
        if not job:
            return
        
        item = db.session.get(WardrobeItemDB, job.item_id)
        if not item:
            job.status = "failed"
            job.error_msg = "Item not found."
            db.session.commit()
            return

        job.status = "processing"
        db.session.commit()

        # ── Step 1: FASHN VTON v1.5 (primary engine — free ZeroGPU) ─────────
        fashn_cat_map = {
            "top":      "tops",
            "outwear":  "tops",
            "bottom":   "bottoms",
            "dress":    "one-pieces",
            "jumpsuit": "one-pieces",
            "shoes":    "tops",
        }
        fashn_cat = fashn_cat_map.get(item.category, "tops")

        fashn_max_retries = 3
        fashn_attempt = 0

        while fashn_attempt < fashn_max_retries:
            fashn_attempt += 1
            try:
                from gradio_client import Client, handle_file
                logger.info(
                    "VTO job %d: trying FASHN engine %s (attempt %d/%d)...",
                    job_id, fashn_space_id, fashn_attempt, fashn_max_retries,
                )

                client = Client(fashn_space_id, token=hf_token or None)
                result = client.predict(
                    person_image=handle_file(person_path),
                    garment_image=handle_file(garment_path),
                    category=fashn_cat,
                    garment_photo_type="flat-lay",
                    num_timesteps=50,
                    guidance_scale=1.5,
                    seed=42,
                    segmentation_free=True,
                    api_name="/try_on",
                )

                # Result is a dict with 'path' key for local file
                if isinstance(result, dict):
                    result_source = result.get("path") or result.get("url") or ""
                else:
                    result_source = _extract_output_source(result)
                if not result_source:
                    raise RuntimeError("FASHN engine returned an empty response.")

                result_filename = f"tryon_{job_id}_{uuid.uuid4().hex[:8]}.png"
                result_path = os.path.join(upload_dir, result_filename)

                source_str = str(result_source)
                if source_str.startswith(("http://", "https://")):
                    import requests as _req
                    resp = _req.get(source_str, timeout=30)
                    resp.raise_for_status()
                    with open(result_path, "wb") as f:
                        f.write(resp.content)
                elif hasattr(result_source, "save") and callable(result_source.save):
                    result_source.save(result_path)
                else:
                    if not os.path.exists(source_str):
                        raise FileNotFoundError(f"FASHN output path not found: {source_str}")
                    shutil.copy(source_str, result_path)

                job.status          = "ready"
                job.result_filename = result_filename
                job.completed_at    = datetime.now(timezone.utc)
                db.session.commit()
                logger.info("VTO job %d: completed via FASHN engine.", job_id)
                return

            except Exception as fashn_exc:
                error_str = str(fashn_exc)
                logger.warning(
                    "VTO job %d: FASHN attempt %d/%d failed: %s",
                    job_id, fashn_attempt, fashn_max_retries, error_str,
                )
                if _is_rate_limited_error(error_str) and fashn_attempt < fashn_max_retries:
                    wait_time = 10 * fashn_attempt
                    logger.warning("VTO job %d: FASHN throttled. Waiting %ds...", job_id, wait_time)
                    time.sleep(wait_time)
                    continue
                if fashn_attempt >= fashn_max_retries:
                    break
                time.sleep(5)

        logger.warning("VTO job %d: FASHN engine exhausted. Falling back to IDM-VTON...", job_id)
        job.error_msg = "Primary engine temporarily unavailable. Using fallback engine."
        db.session.commit()

        # ── Step 2: IDM-VTON fallback engine ──────────────────────────────────
        max_retries = 4
        attempt = 0

        while attempt < max_retries:
            attempt += 1
            try:
                from gradio_client import Client, handle_file
                logger.info(
                    "VTO job %d: trying fallback engine %s (attempt %d/%d)...",
                    job_id,
                    hf_space_id,
                    attempt,
                    max_retries,
                )
                
                client = Client(hf_space_id, token=hf_token or None)
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
                    denoise_steps  = 25,
                    seed           = 42,
                    api_name       = "/tryon",
                )

                # IDM-VTON returns (output_filepath, masked_image_filepath).
                # We want the first element (the try-on result).
                if isinstance(result, (list, tuple)) and len(result) >= 1:
                    result_source = str(result[0])
                else:
                    result_source = _extract_output_source(result)
                if not result_source:
                    raise RuntimeError("Fallback engine returned an empty response.")
                result_filename = f"tryon_{job_id}_{uuid.uuid4().hex[:8]}.png"
                result_path     = os.path.join(upload_dir, result_filename)
                shutil.copy(result_source, result_path)

                job.status          = "ready"
                job.result_filename = result_filename
                job.completed_at    = datetime.now(timezone.utc)
                db.session.commit()
                logger.info("VTO job %d: completed via fallback engine.", job_id)
                return

            except Exception as hf_exc:
                error_str = str(hf_exc)
                if _is_rate_limited_error(error_str) and attempt < max_retries:
                    wait_time = 15 * attempt
                    logger.warning("VTO job %d: fallback throttled. Waiting %ds...", job_id, wait_time)
                    time.sleep(wait_time)
                    continue

                # Terminal Failure
                primary_err = (job.error_msg or "").strip()
                if _is_rate_limited_error(error_str):
                    error_str = (
                        "Try-on service is busy right now. Please retry in 1-2 minutes."
                    )
                else:
                    error_str = "Try-on service is temporarily unavailable. Please retry shortly."

                # Keep user-facing errors concise; detailed traces stay in logs.
                if "Using fallback engine" in primary_err:
                    user_error = error_str
                elif primary_err:
                    user_error = f"{primary_err} {error_str}"[:500]
                else:
                    user_error = error_str

                job.status       = "failed"
                job.error_msg    = user_error[:500]
                job.completed_at = datetime.now(timezone.utc)
                db.session.commit()
                logger.error("VTO job %d failed: %s", job_id, hf_exc)
                break
