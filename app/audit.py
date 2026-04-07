"""
app/audit.py
Audit logging helper — records security-relevant actions.

Usage:
    from app.audit import log_action
    log_action("login", user_id=1, detail="email login")
    log_action("login_failed", detail="bad password for test@example.com")
"""

from __future__ import annotations

import logging

from flask import request

from app.extensions import db
from app.models_db import AuditLog

logger = logging.getLogger(__name__)

# Actions that are recorded
ACTIONS = {
    "login",
    "login_failed",
    "register",
    "upload_item",
    "delete_item",
    "delete_account",
    "consent_granted",
    "consent_revoked",
    "data_export",
    "vto_job_submitted",
    "password_changed",
}


def log_action(action: str, user_id: int | None = None, detail: str | None = None) -> None:
    """
    Write an audit log entry. Fire-and-forget — never raises.

    Args:
        action: one of the ACTIONS constants (e.g. "login", "upload_item")
        user_id: authenticated user ID, or None for anonymous actions
        detail: optional human-readable context (truncated to 500 chars)
    """
    try:
        ip = request.remote_addr if request else None
    except RuntimeError:
        ip = None

    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            detail=(detail or "")[:500] or None,
            ip_address=ip,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception as exc:
        logger.warning("Audit log write failed: %s", exc)
        db.session.rollback()
