"""
app/auth/routes.py
Authentication endpoints: register, login, refresh, consent, privacy.
"""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone, timedelta

import requests as _requests

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db, bcrypt, limiter
from app.models_db import User, UserConsent, WardrobeItemDB, OutfitHistory, SavedOutfit, OutfitFeedback, PasswordResetToken
from app.audit import log_action
from app.storage import get_public_url as _img_url

auth_bp = Blueprint("auth", __name__)

VALID_GENDERS = {"men", "women", "unisex"}


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("3/minute")
def register():
    """
    POST /auth/register
    Body: {name, email, password, gender}
    Returns 201 on success, 400 if email taken, 422 if validation fails.
    """
    data = request.get_json(silent=True) or {}

    # Validate required fields
    for field in ("name", "email", "password", "gender"):
        if not data.get(field):
            return jsonify({"error": f"'{field}' is required."}), 422

    name     = str(data["name"]).strip()
    email    = str(data["email"]).strip().lower()
    password = str(data["password"])
    gender   = str(data["gender"]).strip().lower()

    if not name or len(name) > 80:
        return jsonify({"error": "Name must be 1–80 characters."}), 422
    if "@" not in email or len(email) > 120:
        return jsonify({"error": "Invalid email address."}), 422
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 422
    if gender not in VALID_GENDERS:
        return jsonify({"error": f"gender must be one of: {', '.join(VALID_GENDERS)}."}), 422

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email already exists."}), 400

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    user = User(name=name, email=email, password_hash=password_hash, gender=gender)
    db.session.add(user)
    db.session.commit()

    log_action("register", user_id=user.id, detail=f"email={email}")
    return jsonify({"message": "Account created.", "user_id": user.id}), 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5/minute")
def login():
    """
    POST /auth/login
    Body: {email, password}
    Returns JWT access token on success, 401 on bad credentials.
    """
    data = request.get_json(silent=True) or {}

    email    = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email or not password:
        return jsonify({"error": "email and password are required."}), 422

    user = None
    fallback_row = None

    try:
        user = User.query.filter_by(email=email).first()
    except SQLAlchemyError as exc:
        # Fallback for schema drift in local databases (e.g., missing newly added columns).
        current_app.logger.error("Auth login ORM lookup failed; using fallback query: %s", exc)
        db.session.rollback()
        fallback_row = db.session.execute(
            text(
                "SELECT id, name, gender, password_hash "
                "FROM users WHERE email = :email LIMIT 1"
            ),
            {"email": email},
        ).mappings().first()

    password_hash = user.password_hash if user is not None else (fallback_row["password_hash"] if fallback_row else None)
    if not password_hash or not bcrypt.check_password_hash(password_hash, password):
        log_action("login_failed", detail=f"email={email}")
        return jsonify({"error": "Invalid email or password."}), 401

    user_id = user.id if user is not None else int(fallback_row["id"])
    name = user.name if user is not None else str(fallback_row["name"])
    gender = user.gender if user is not None else str(fallback_row["gender"])

    access_token = create_access_token(identity=str(user_id))
    log_action("login", user_id=user_id, detail=f"email={email}")
    return jsonify({
        "access_token": access_token,
        "user_id":      user_id,
        "name":         name,
        "gender":       gender,
        "avatar_url":   _img_url(user.avatar_filename) if user is not None and user.avatar_filename else None,
    }), 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required()
def refresh():
    """
    POST /auth/refresh
    Requires valid (non-expired) JWT in Authorization header.
    Returns a fresh access token.

    Note: This is a simple re-issue, not full refresh-token rotation.
    Suitable for FYP scope.
    """
    user_id = get_jwt_identity()  # str
    new_token = create_access_token(identity=user_id)
    return jsonify({"access_token": new_token}), 200


# ── Consent types ──────────────────────────────────────────────────────────────

CONSENT_TYPES = {
    "data_training": "Allow your wardrobe data and outfit preferences to be used for model improvement.",
    "analytics":     "Allow anonymous usage analytics to help us improve the app experience.",
}

CURRENT_POLICY_VERSION = "1.0"


@auth_bp.route("/consent", methods=["GET"])
@jwt_required()
def get_consent():
    """
    GET /auth/consent
    Returns the user's current consent status for all consent types.
    """
    user_id = int(get_jwt_identity())

    result = {}
    for ctype, description in CONSENT_TYPES.items():
        consent = (
            UserConsent.query
            .filter_by(user_id=user_id, consent_type=ctype)
            .order_by(UserConsent.id.desc())
            .first()
        )
        result[ctype] = {
            "granted":     consent.granted if consent else False,
            "version":     consent.version if consent else CURRENT_POLICY_VERSION,
            "granted_at":  consent.granted_at.isoformat() if consent and consent.granted else None,
            "revoked_at":  consent.revoked_at.isoformat() if consent and consent.revoked_at else None,
            "description": description,
        }

    return jsonify({"consents": result}), 200


@auth_bp.route("/consent", methods=["PATCH"])
@jwt_required()
def update_consent():
    """
    PATCH /auth/consent
    Body: { "data_training": true, "analytics": false }
    Updates consent for the specified types. Creates audit trail entries.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    if not data:
        return jsonify({"error": "Request body must contain consent type(s)."}), 422

    ip = request.remote_addr
    updated = []

    for ctype, granted in data.items():
        if ctype not in CONSENT_TYPES:
            return jsonify({"error": f"Unknown consent type: '{ctype}'."}), 422
        if not isinstance(granted, bool):
            return jsonify({"error": f"Value for '{ctype}' must be true or false."}), 422

        # Get the latest consent record for this type
        existing = (
            UserConsent.query
            .filter_by(user_id=user_id, consent_type=ctype)
            .order_by(UserConsent.id.desc())
            .first()
        )

        if existing and existing.granted == granted:
            # No change needed
            updated.append(ctype)
            continue

        if existing and existing.granted and not granted:
            # Revoking: update the existing record
            existing.granted = False
            existing.revoked_at = datetime.now(timezone.utc)
            log_action("consent_revoked", user_id=user_id, detail=f"type={ctype} version={existing.version}")
        else:
            # Granting (new or re-grant after revoke): create a new record
            consent = UserConsent(
                user_id=user_id,
                consent_type=ctype,
                granted=True,
                version=CURRENT_POLICY_VERSION,
                ip_address=ip,
            )
            db.session.add(consent)
            log_action("consent_granted", user_id=user_id, detail=f"type={ctype} version={CURRENT_POLICY_VERSION}")

        updated.append(ctype)

    db.session.commit()
    return jsonify({"message": "Consent updated.", "updated": updated}), 200


@auth_bp.route("/privacy-summary", methods=["GET"])
@jwt_required()
def privacy_summary():
    """
    GET /auth/privacy-summary
    Returns a summary of the user's data footprint for the privacy dashboard.
    """
    user_id = int(get_jwt_identity())

    item_count = WardrobeItemDB.query.filter_by(user_id=user_id).count()
    outfit_count = OutfitHistory.query.filter_by(user_id=user_id).count()
    saved_count = SavedOutfit.query.filter_by(user_id=user_id).count()
    feedback_count = OutfitFeedback.query.filter_by(user_id=user_id).count()

    user = db.session.get(User, user_id)

    return jsonify({
        "user_id": user_id,
        "email": user.email,
        "account_created": user.created_at.isoformat() if user.created_at else None,
        "data_summary": {
            "wardrobe_items": item_count,
            "outfit_history": outfit_count,
            "saved_outfits": saved_count,
            "feedback_given": feedback_count,
            "has_person_photo": bool(user.profile_photo_filename),
        },
    }), 200


@auth_bp.route("/data-export", methods=["GET"])
@jwt_required()
def data_export():
    """
    GET /auth/data-export
    Returns all user data as a JSON download (GDPR-style data portability).
    """
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    items = WardrobeItemDB.query.filter_by(user_id=user_id).all()
    history = OutfitHistory.query.filter_by(user_id=user_id).all()
    saved = SavedOutfit.query.filter_by(user_id=user_id).all()
    feedback = OutfitFeedback.query.filter_by(user_id=user_id).all()
    consents = UserConsent.query.filter_by(user_id=user_id).all()

    export = {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "gender": user.gender,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "wardrobe_items": [
            {
                "id": i.id,
                "category": i.category,
                "sub_category": i.sub_category,
                "formality": i.formality,
                "gender": i.gender,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in items
        ],
        "outfit_history": [
            {
                "id": h.id,
                "occasion": h.occasion,
                "temperature": h.temperature_used,
                "item_ids": json.loads(h.item_ids) if h.item_ids else [],
                "score": h.final_score,
                "logged_at": h.logged_at.isoformat() if h.logged_at else None,
            }
            for h in history
        ],
        "saved_outfits": [
            {
                "id": s.id,
                "name": s.name,
                "occasion": s.occasion,
                "item_ids": json.loads(s.item_ids) if s.item_ids else [],
                "score": s.final_score,
                "saved_at": s.saved_at.isoformat() if s.saved_at else None,
            }
            for s in saved
        ],
        "feedback": [
            {
                "id": f.id,
                "history_id": f.history_id,
                "rating": f.rating,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in feedback
        ],
        "consents": [c.to_dict() for c in consents],
    }

    log_action("data_export", user_id=user_id)

    response = jsonify(export)
    response.headers["Content-Disposition"] = f"attachment; filename=outfitai_data_{user_id}.json"
    return response, 200


@auth_bp.route("/account", methods=["DELETE"])
@jwt_required()
@limiter.limit("5/minute")
def delete_account():
    """
    DELETE /auth/account
    Permanently deletes the user account and all associated data.
    Requires password confirmation in the request body.
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    password = str(data.get("password", ""))
    if not password:
        return jsonify({"error": "Password confirmation is required."}), 422

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    if not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "Incorrect password."}), 401

    log_action("delete_account", user_id=user_id, detail=f"email={user.email}")

    # Cascade delete handles wardrobe_items, outfit_history, saved_outfits, etc.
    db.session.delete(user)
    db.session.commit()

    return jsonify({"message": "Account permanently deleted."}), 200


@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
@limiter.limit("5/minute")
def change_password():
    """
    POST /auth/change-password
    Body: { "current_password": "...", "new_password": "..." }
    """
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    current_pw = str(data.get("current_password", ""))
    new_pw = str(data.get("new_password", ""))

    if not current_pw or not new_pw:
        return jsonify({"error": "current_password and new_password are required."}), 422
    if len(new_pw) < 8:
        return jsonify({"error": "New password must be at least 8 characters."}), 422

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404
    if not bcrypt.check_password_hash(user.password_hash, current_pw):
        return jsonify({"error": "Current password is incorrect."}), 401

    user.password_hash = bcrypt.generate_password_hash(new_pw).decode("utf-8")
    db.session.commit()

    log_action("password_changed", user_id=user_id)
    return jsonify({"message": "Password changed successfully."}), 200


# ── Password reset ─────────────────────────────────────────────────────────────

_RESET_TTL_HOURS = 1


def _send_reset_email(to_email: str, reset_url: str) -> bool:
    """Send password reset email via Resend API. Returns True on success."""
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    from_addr = os.environ.get("RESEND_FROM_EMAIL", "OutfitAI <noreply@drssl.app>").strip()
    if not api_key:
        current_app.logger.warning("RESEND_API_KEY not set — password reset email not sent")
        return False

    payload = {
        "from": from_addr,
        "to": [to_email],
        "subject": "Reset your OutfitAI password",
        "html": f"""
<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px">
  <h2 style="color:#1a1a1a">Reset your password</h2>
  <p style="color:#555">We received a request to reset your OutfitAI password.
     Click the button below — this link expires in {_RESET_TTL_HOURS} hour.</p>
  <a href="{reset_url}"
     style="display:inline-block;margin:24px 0;padding:12px 28px;
            background:#1a1a1a;color:#fff;text-decoration:none;
            border-radius:8px;font-weight:600">
    Reset Password
  </a>
  <p style="color:#999;font-size:12px">
    If you didn't request this, you can safely ignore this email.
    Your password will not change.
  </p>
</div>
""",
    }
    try:
        resp = _requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=10,
        )
        if not resp.ok:
            current_app.logger.warning("Resend API error %d: %s", resp.status_code, resp.text[:200])
        return resp.ok
    except Exception as exc:  # nosec B110
        current_app.logger.warning("Resend request failed: %s", exc)
        return False


@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("3/minute")
def forgot_password():
    """
    POST /auth/forgot-password
    Body: { "email": "..." }
    Generates a one-time token and sends a reset link via email.
    Always returns 200 to avoid email enumeration.
    """
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()

    if not email:
        return jsonify({"error": "email is required."}), 422

    user = User.query.filter_by(email=email).first()
    if user:
        # Invalidate any existing unused tokens for this user
        PasswordResetToken.query.filter_by(user_id=user.id, used=False).delete()

        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=_RESET_TTL_HOURS)
        db.session.add(PasswordResetToken(user_id=user.id, token=token, expires_at=expires))
        db.session.commit()

        frontend_url = os.environ.get("FRONTEND_URL", "https://drssl.app").rstrip("/")
        reset_url = f"{frontend_url}/reset-password?token={token}"
        _send_reset_email(user.email, reset_url)
        log_action("forgot_password", user_id=user.id, detail=f"email={email}")

    # Always 200 — don't reveal whether email exists
    return jsonify({"message": "If that email is registered, a reset link has been sent."}), 200


@auth_bp.route("/reset-password", methods=["POST"])
@limiter.limit("5/minute")
def reset_password():
    """
    POST /auth/reset-password
    Body: { "token": "...", "password": "..." }
    Validates the token and updates the user's password.
    """
    data = request.get_json(silent=True) or {}
    token_value = str(data.get("token", "")).strip()
    new_password = str(data.get("password", ""))

    if not token_value or not new_password:
        return jsonify({"error": "token and password are required."}), 422
    if len(new_password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 422

    record = PasswordResetToken.query.filter_by(token=token_value, used=False).first()

    if not record:
        return jsonify({"error": "Invalid or expired reset link."}), 400

    now = datetime.now(timezone.utc)
    expires = record.expires_at
    # Make expires_at timezone-aware if stored as naive datetime
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if now > expires:
        return jsonify({"error": "Reset link has expired. Please request a new one."}), 400

    user = db.session.get(User, record.user_id)
    if not user:
        return jsonify({"error": "Invalid or expired reset link."}), 400

    user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    record.used = True
    db.session.commit()

    log_action("password_reset", user_id=user.id)
    return jsonify({"message": "Password reset successfully. You can now log in."}), 200
