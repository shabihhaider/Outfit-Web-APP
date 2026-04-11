"""
tests/test_flask_observability.py
Tests for Phase 5 observability endpoints: /health and /metrics.
"""

import pytest

from app import create_app
from app.extensions import db


@pytest.fixture()
def client():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def auth_headers(client):
    client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": "metrics@example.com",
            "password": "password123",
            "gender": "men",
        },
    )
    resp = client.post(
        "/auth/login",
        json={"email": "metrics@example.com", "password": "password123"},
    )
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "healthy"
        assert data["components"]["database"] == "ok"

    def test_health_has_component_keys(self, client):
        resp = client.get("/health")
        data = resp.get_json()
        components = data["components"]
        assert "database" in components
        assert "ml_pipeline" in components
        assert "vto_engine" in components

    def test_health_ml_pipeline_not_loaded_in_testing(self, client):
        resp = client.get("/health")
        data = resp.get_json()
        assert data["components"]["ml_pipeline"] == "not_loaded"


class TestMetricsEndpoint:
    def test_metrics_requires_auth(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 401

    def test_metrics_returns_ok(self, client, auth_headers):
        resp = client.get("/metrics", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "users_total" in data
        assert "wardrobe_items_total" in data
        assert "vto_jobs" in data
        assert "recommendation_cache" in data
        assert "query_time_ms" in data

    def test_metrics_empty_db(self, client, auth_headers):
        resp = client.get("/metrics", headers=auth_headers)
        data = resp.get_json()
        assert data["wardrobe_items_total"] == 0

    def test_metrics_cache_stats(self, client, auth_headers):
        resp = client.get("/metrics", headers=auth_headers)
        data = resp.get_json()
        cache = data["recommendation_cache"]
        assert "entries" in cache
        assert "hits" in cache
        assert "misses" in cache
        assert "hit_rate" in cache


class TestRequestIdMiddleware:
    def test_response_has_request_id_header(self, client):
        resp = client.get("/health")
        assert "X-Request-ID" in resp.headers
        assert len(resp.headers["X-Request-ID"]) == 32  # hex UUID without dashes

    def test_custom_request_id_propagated(self, client):
        resp = client.get("/health", headers={"X-Request-ID": "test-req-123"})
        assert resp.headers["X-Request-ID"] == "test-req-123"
