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
    Background worker: Hybrid VTO Engine.
    1. Try Replicate (High speed, stable, uses student credits).
    2. Fallback to HF Spaces (Shared, free, slower).
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

        # ── Step 1: Attempt Replicate (The "Express" Lane) ───────────────────
        # Using cuuupid/idm-vton:0513734a452173b8173e907e3a59d19a36266e55b48528559432bd21c7d7e985
        replicate_token = current_app.config.get("REPLICATE_API_TOKEN")
        if replicate_token:
            try:
                import replicate
                logger.info("VTO job %d: attempting Replicate (cuuupid/idm-vton)...", job_id)
                
                # REPLICATE_API_TOKEN is usually picked up automatically from ENV
                # But we can also set it explicitly just in case HF config didn't export it
                import os
                os.environ["REPLICATE_API_TOKEN"] = replicate_token

                # Map categories: upper_body, lower_body, dresses
                rep_cat = "upper_body"
                cat_map = {
                    "top":      "upper_body",
                    "outwear":  "upper_body",
                    "bottom":   "lower_body",
                    "dress":    "dresses",
                    "jumpsuit": "dresses",
                    "shoes":    "upper_body" # Fallback
                }
                rep_cat = cat_map.get(item.category, "upper_body")

                with open(person_path, "rb") as p_file, open(garment_path, "rb") as g_file:
                    output = replicate.run(
                        "cuuupid/idm-vton:0513734a452173b8173e907e3a59d19a36266e55b48528559432bd21c7d7e985",
                        input={
                            "human_img":   p_file,
                            "garm_img":    g_file,
                            "garment_des": f"{item.category} clothing",
                            "category":    rep_cat
                        }
                    )

                # Result is a URL
                if output:
                    import requests
                    image_url = str(output)
                    resp = requests.get(image_url, timeout=30)
                    resp.raise_for_status()
                    
                    result_filename = f"tryon_{job_id}_{uuid.uuid4().hex[:8]}.png"
                    result_path     = os.path.join(upload_dir, result_filename)
                    with open(result_path, "wb") as f:
                        f.write(resp.content)

                    job.status          = "ready"
                    job.result_filename = result_filename
                    job.completed_at    = datetime.now(timezone.utc)
                    db.session.commit()
                    logger.info("VTO job %d: completed via Replicate!", job_id)
                    return # SUCCESS - Exit Early

            except Exception as rep_exc:
                logger.warning("VTO job %d: Replicate failed (%s). Falling back to HF...", job_id, rep_exc)
                # Fail through to Step 2
        else:
            logger.info("VTO job %d: REPLICATE_API_TOKEN missing. Using free HF fallback.", job_id)

        # ── Step 2: Fallback to Hugging Face (The "Economy" Lane) ──────────────
        max_retries = 3
        attempt = 0
        import time

        while attempt < max_retries:
            attempt += 1
            try:
                from gradio_client import Client, handle_file
                logger.info("VTO job %d: trying HF Space (attempt %d/%d)...", job_id, attempt, max_retries)
                
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
                    denoise_steps  = 25,
                    seed           = 42,
                    api_name       = "/tryon",
                )

                # Fetch result image
                result_source = result[0] if isinstance(result, (list, tuple)) else result
                result_filename = f"tryon_{job_id}_{uuid.uuid4().hex[:8]}.png"
                result_path     = os.path.join(upload_dir, result_filename)
                shutil.copy(str(result_source), result_path)

                job.status          = "ready"
                job.result_filename = result_filename
                job.completed_at    = datetime.now(timezone.utc)
                db.session.commit()
                logger.info("VTO job %d: completed via HF Fallback!", job_id)
                return

            except Exception as hf_exc:
                error_str = str(hf_exc)
                if "Too many requests" in error_str and attempt < max_retries:
                    wait_time = 8 * attempt
                    logger.warning("VTO job %d: HF throttled. Waiting %ds...", job_id, wait_time)
                    time.sleep(wait_time)
                    continue
                
                # Terminal Failure
                job.status       = "failed"
                job.error_msg    = f"HF Error: {error_str}"[:500]
                job.completed_at = datetime.now(timezone.utc)
                db.session.commit()
                logger.error("VTO job %d failed: %s", job_id, hf_exc)
                break
