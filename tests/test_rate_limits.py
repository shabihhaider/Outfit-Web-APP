"""
tests/test_rate_limits.py
Integration tests that verify flask-limiter correctly rejects over-limit requests.

Uses the "rate_limit_testing" config which enables rate limiting with in-memory
storage. The main TestingConfig keeps RATELIMIT_ENABLED=False so unit tests
stay fast and don't interfere with each other.

Limits under test:
  POST /auth/register       — 3/minute
  POST /auth/login          — 5/minute
  POST /auth/forgot-password — 3/minute
  POST /wardrobe/items      — 10/minute
"""

from __future__ import annotations

import io
from unittest.mock import MagicMock

import numpy as np
import pytest


# ─── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture
def rl_app():
    """Flask app with rate limiting ENABLED (in-memory storage, SQLite)."""
    from app import create_app

    app = create_app("rate_limit_testing")

    mock_pipeline = MagicMock()
    mock_pipeline.classify_and_embed.return_value = (
        "top",
        np.zeros(1280, dtype=np.float32),
        0.95,
    )
    mock_pipeline.extract_color.return_value = (30.0, 0.8, 0.7)
    mock_pipeline.get_temperature.return_value = 28.0
    mock_pipeline.recommend.return_value = []
    app.pipeline = mock_pipeline

    with app.app_context():
        from app.extensions import db
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def rl_client(rl_app):
    return rl_app.test_client()


@pytest.fixture
def rl_auth_headers(rl_client):
    """Register + login; return auth headers."""
    rl_client.post(
        "/auth/register",
        json={
            "name": "RL User",
            "email": "rl@example.com",
            "password": "password123",
            "gender": "men",
        },
    )
    resp = rl_client.post(
        "/auth/login",
        json={"email": "rl@example.com", "password": "password123"},
    )
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ─── Auth rate limits ──────────────────────────────────────────────────────────

class TestRegisterRateLimit:
    def test_register_blocked_after_limit(self, rl_client):
        """POST /auth/register — limit 3/minute: 4th request → 429."""
        payload = lambda i: {
            "name": f"User {i}",
            "email": f"newuser{i}@example.com",
            "password": "password123",
            "gender": "men",
        }
        # First 3 requests must not be rate-limited (201 or 409)
        for i in range(3):
            r = rl_client.post("/auth/register", json=payload(i))
            assert r.status_code != 429, f"Request {i} unexpectedly rate-limited"

        # 4th request must be rate-limited
        r = rl_client.post("/auth/register", json=payload(99))
        assert r.status_code == 429


class TestLoginRateLimit:
    def test_login_blocked_after_limit(self, rl_client):
        """POST /auth/login — limit 5/minute: 6th request → 429."""
        bad = {"email": "nobody@example.com", "password": "wrongpassword"}

        # First 5 requests must not be rate-limited (401 for bad credentials is fine)
        for i in range(5):
            r = rl_client.post("/auth/login", json=bad)
            assert r.status_code != 429, f"Request {i} unexpectedly rate-limited"

        # 6th request must be rate-limited
        r = rl_client.post("/auth/login", json=bad)
        assert r.status_code == 429


class TestForgotPasswordRateLimit:
    def test_forgot_password_blocked_after_limit(self, rl_client):
        """POST /auth/forgot-password — limit 3/minute: 4th request → 429."""
        payload = {"email": "nobody@example.com"}

        for i in range(3):
            r = rl_client.post("/auth/forgot-password", json=payload)
            assert r.status_code != 429, f"Request {i} unexpectedly rate-limited"

        r = rl_client.post("/auth/forgot-password", json=payload)
        assert r.status_code == 429


# ─── Wardrobe rate limit ───────────────────────────────────────────────────────

class TestWardrobeUploadRateLimit:
    def _make_png(self) -> bytes:
        import struct, zlib
        def chunk(t, d):
            return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
        raw = b"\x00\xff\xff\xff"
        return (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b"")
        )

    def test_upload_blocked_after_limit(self, rl_client, rl_auth_headers):
        """POST /wardrobe/items — limit 10/minute: 11th request → 429."""
        png = self._make_png()

        for i in range(10):
            r = rl_client.post(
                "/wardrobe/items",
                data={
                    "image": (io.BytesIO(png), "shirt.png", "image/png"),
                    "formality": "casual",
                    "gender": "men",
                },
                headers=rl_auth_headers,
                content_type="multipart/form-data",
            )
            assert r.status_code != 429, f"Upload {i} unexpectedly rate-limited"

        r = rl_client.post(
            "/wardrobe/items",
            data={
                "image": (io.BytesIO(png), "shirt.png", "image/png"),
                "formality": "casual",
                "gender": "men",
            },
            headers=rl_auth_headers,
            content_type="multipart/form-data",
        )
        assert r.status_code == 429
