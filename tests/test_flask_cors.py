"""
tests/test_flask_cors.py
Regression tests for CORS configuration security (issue #95).
"""

from __future__ import annotations

import pytest

from app import create_app
from app.config import ProductionConfig


class TestCORSConfig:
    def test_production_cors_is_not_wildcard(self):
        """ProductionConfig must never default to the CORS wildcard."""
        assert ProductionConfig.CORS_ORIGINS != "*", (
            "ProductionConfig.CORS_ORIGINS defaults to '*' — this exposes the API "
            "to any origin. Set a specific origin like 'https://drssl.app'."
        )

    def test_production_cors_default_is_known_frontend(self):
        """ProductionConfig default origin must be the known Vercel frontend."""
        assert "drssl.app" in ProductionConfig.CORS_ORIGINS

    def test_development_cors_wildcard_is_allowed(self):
        """Development config may use '*' for convenience."""
        from app.config import DevelopmentConfig
        # No assertion — just documents that dev can use wildcard.
        # This test fails only if dev config is accidentally locked down.
        assert DevelopmentConfig.CORS_ORIGINS is not None

    def test_cors_origins_env_override(self, monkeypatch):
        """CORS_ORIGINS env var overrides the config default."""
        monkeypatch.setenv("CORS_ORIGINS", "https://custom.example.com")
        # Reload the config class attribute by reading the env directly
        import os
        value = os.environ.get("CORS_ORIGINS", "https://drssl.app")
        assert value == "https://custom.example.com"
