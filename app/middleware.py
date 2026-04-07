"""
app/middleware.py
Request-level middleware for observability and security.

- Request ID: UUID attached to every request, propagated through logs and
  returned in the X-Request-ID response header.
- Security headers: CSP, X-Content-Type-Options, X-Frame-Options, etc.
- Structured JSON logging: replaces default text logs with machine-readable
  JSON lines (timestamp, level, request_id, user_id, message).
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone

from flask import Flask, g, request


# ── Request ID ────────────────────────────────────────────────────────────────

def _before_request():
    """Attach a unique request ID and start timer to flask.g."""
    g.request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
    g.request_start = time.monotonic()


def _after_request(response):
    """Inject request ID, security headers, and log the request."""
    req_id = getattr(g, "request_id", "-")
    response.headers["X-Request-ID"] = req_id

    # ── Security headers ──────────────────────────────────────────────────
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob: https:; "
        "connect-src 'self' https://*.hf.space https://nominatim.openstreetmap.org https://api.open-meteo.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    # Log completed request
    duration_ms = 0.0
    if hasattr(g, "request_start"):
        duration_ms = (time.monotonic() - g.request_start) * 1000

    # Skip logging for health/metrics to avoid noise
    if request.path not in ("/health", "/metrics"):
        logger = logging.getLogger("app.access")
        logger.info(
            "%s %s %s %.0fms",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            extra={
                "request_id": req_id,
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 1),
            },
        )

    return response


def init_middleware(app: Flask) -> None:
    """Register request lifecycle hooks on the Flask app."""
    app.before_request(_before_request)
    app.after_request(_after_request)


# ── Structured JSON Log Formatter ─────────────────────────────────────────────

class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        # Pull request context if available
        req_id = None
        user_id = None
        try:
            from flask import has_request_context
            if has_request_context():
                req_id = getattr(g, "request_id", None)
                # Try to get user from JWT (best-effort)
                try:
                    from flask_jwt_extended import get_jwt_identity
                    user_id = get_jwt_identity()
                except Exception:
                    pass
        except Exception:
            pass

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if req_id:
            entry["request_id"] = req_id
        if user_id:
            entry["user_id"] = user_id

        # Merge any structured extras from the log call
        for key in ("method", "path", "status", "duration_ms", "engine", "job_id"):
            val = getattr(record, key, None)
            if val is not None:
                entry[key] = val

        if record.exc_info and record.exc_info[0]:
            entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(entry, default=str)


def configure_logging(app: Flask) -> None:
    """
    Set up structured JSON logging for the application.

    In production (not DEBUG), all app.* loggers emit JSON lines to stderr.
    In debug mode, keep human-readable logs for developer convenience.
    """
    if app.debug:
        # Keep default readable format in dev
        logging.basicConfig(level=logging.INFO)
        return

    # Production: JSON to stderr
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Reduce noise from libraries
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
