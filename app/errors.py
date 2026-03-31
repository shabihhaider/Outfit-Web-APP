"""
app/errors.py
Global error handlers — ALL errors return JSON, never HTML.

Covers:
  - Engine exceptions (WeatherLocationError, WeatherAPIError, etc.)
  - Flask HTTP errors (404, 405, 413)
  - Pydantic ValidationError
  - Generic unhandled exceptions (logged, not exposed)
"""

from __future__ import annotations

import logging
import traceback

from flask import jsonify

logger = logging.getLogger(__name__)


def register_error_handlers(app) -> None:
    """Register all error handlers on the Flask app."""

    # ─── Engine exceptions ────────────────────────────────────────────────────

    @app.errorhandler(Exception)
    def handle_generic_exception(exc):
        from engine.models import (
            WeatherLocationError, WeatherAPIError,
            InsufficientWardrobeError, ModelNotLoadedError,
        )
        try:
            from pydantic import ValidationError
        except ImportError:
            ValidationError = None

        if isinstance(exc, WeatherLocationError):
            return jsonify({"error": "Location required. Provide lat/lon or enter temperature manually."}), 400

        if isinstance(exc, WeatherAPIError):
            return jsonify({"error": "Weather service unavailable. Please enter temperature manually."}), 503

        if isinstance(exc, InsufficientWardrobeError):
            return jsonify({"error": "Not enough wardrobe items to form an outfit for this occasion."}), 422

        if isinstance(exc, ModelNotLoadedError):
            logger.critical("ML models not loaded: %s", exc)
            return jsonify({"error": "ML models failed to load. Contact support."}), 500

        if ValidationError and isinstance(exc, ValidationError):
            return jsonify({"error": "Validation failed.", "details": exc.errors()}), 422

        # Unhandled — log the full traceback, never expose it
        logger.error("Unhandled exception:\n%s", traceback.format_exc())
        return jsonify({"error": "Internal server error."}), 500

    # ─── Flask HTTP errors ────────────────────────────────────────────────────

    @app.errorhandler(400)
    def handle_400(exc):
        return jsonify({"error": "Bad request.", "details": str(exc)}), 400

    @app.errorhandler(401)
    def handle_401(exc):
        return jsonify({"error": "Authentication required."}), 401

    @app.errorhandler(403)
    def handle_403(exc):
        return jsonify({"error": "Access forbidden."}), 403

    @app.errorhandler(404)
    def handle_404(exc):
        return jsonify({"error": "The requested resource was not found."}), 404

    @app.errorhandler(405)
    def handle_405(exc):
        return jsonify({"error": "Method not allowed."}), 405

    @app.errorhandler(413)
    def handle_413(exc):
        return jsonify({"error": "File too large. Maximum size is 10 MB."}), 413

    @app.errorhandler(422)
    def handle_422(exc):
        return jsonify({"error": "Unprocessable request.", "details": str(exc)}), 422

    @app.errorhandler(429)
    def handle_429(exc):
        return jsonify({"error": "Too many requests. Please slow down."}), 429

    @app.errorhandler(500)
    def handle_500(exc):
        logger.error("Internal server error: %s", traceback.format_exc())
        return jsonify({"error": "Internal server error."}), 500

    @app.errorhandler(503)
    def handle_503(exc):
        return jsonify({"error": "Service temporarily unavailable."}), 503
