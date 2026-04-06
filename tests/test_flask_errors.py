"""
tests/test_flask_errors.py
Verify that every registered error handler returns JSON (never HTML)
with the correct HTTP status code.
"""

from __future__ import annotations

import pytest

from engine.models import (
    WeatherLocationError, WeatherAPIError,
    InsufficientWardrobeError, ModelNotLoadedError,
)


class TestErrorHandlers:

    # ── 404 ───────────────────────────────────────────────────────────────────

    def test_404_returns_json(self, client, auth_headers):
        # Delete a non-existent saved outfit to trigger a proper 404
        # (SPA catch-all intercepts unknown top-level paths when frontend/dist exists)
        resp = client.delete("/outfits/saved/99999", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.content_type.startswith("application/json")
        assert "error" in resp.get_json()

    # ── 405 ───────────────────────────────────────────────────────────────────

    def test_405_returns_json(self, client):
        # /health only accepts GET — send DELETE to trigger 405
        resp = client.delete("/health")
        assert resp.status_code == 405
        assert resp.content_type.startswith("application/json")
        assert "error" in resp.get_json()

    # ── 401 ───────────────────────────────────────────────────────────────────

    def test_401_returns_json(self, client):
        resp = client.get("/wardrobe/items")  # no token
        assert resp.status_code == 401
        # Flask-JWT returns its own JSON; just ensure it's JSON not HTML
        assert resp.content_type.startswith("application/json")

    # ── Engine exceptions via recommendations route ───────────────────────────

    def test_insufficient_wardrobe_error_returns_422(self, client, flask_app, auth_headers):
        flask_app.pipeline.recommend.side_effect = InsufficientWardrobeError("too few")
        resp = client.post(
            "/recommendations",
            json={"occasion": "casual", "temp_celsius": 25.0},
            headers=auth_headers,
        )
        assert resp.status_code == 422
        assert resp.content_type.startswith("application/json")
        body = resp.get_json()
        assert "error" in body

    def test_weather_api_error_returns_503(self, client, flask_app, auth_headers):
        flask_app.pipeline.get_temperature.side_effect = WeatherAPIError("down")
        resp = client.post(
            "/recommendations",
            json={"occasion": "casual", "lat": 31.0, "lon": 74.0},
            headers=auth_headers,
        )
        assert resp.status_code == 503
        assert resp.content_type.startswith("application/json")

    def test_weather_location_error_returns_400(self, client, flask_app, auth_headers):
        flask_app.pipeline.get_temperature.side_effect = WeatherLocationError("missing coords")
        resp = client.post(
            "/recommendations",
            json={"occasion": "casual", "lat": 31.0, "lon": 74.0},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert resp.content_type.startswith("application/json")

    # ── Health endpoint ───────────────────────────────────────────────────────

    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert resp.content_type.startswith("application/json")

    # ── All error responses have Content-Type: application/json ──────────────

    def test_no_html_in_404_body(self, client, auth_headers):
        resp = client.delete("/outfits/saved/99999", headers=auth_headers)
        assert b"<!DOCTYPE" not in resp.data
        assert b"<html" not in resp.data.lower()

    def test_no_html_in_405_body(self, client):
        resp = client.delete("/health")
        assert b"<!DOCTYPE" not in resp.data
        assert b"<html" not in resp.data.lower()
