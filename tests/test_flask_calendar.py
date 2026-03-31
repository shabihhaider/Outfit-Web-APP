"""
tests/test_flask_calendar.py
Tests for:
  GET    /calendar/plans?month=YYYY-MM  — list plans
  POST   /calendar/plans               — create plan
  PATCH  /calendar/plans/<id>          — update plan
  DELETE /calendar/plans/<id>          — delete plan
"""

from __future__ import annotations

import io
import json

import numpy as np
import pytest


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _upload_item(client, auth_headers, minimal_png):
    data = {
        "image":     (io.BytesIO(minimal_png), "item.png", "image/png"),
        "formality": "casual",
        "gender":    "men",
    }
    resp = client.post(
        "/wardrobe/items", data=data, headers=auth_headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201
    return resp.get_json()


def _save_outfit(client, auth_headers, item_ids):
    resp = client.post("/outfits/saved", json={
        "name": f"Test Outfit {len(item_ids)} {id(item_ids)}",
        "occasion": "casual",
        "item_ids": item_ids,
        "final_score": 0.78,
        "confidence": "high",
    }, headers=auth_headers)
    assert resp.status_code == 201
    return resp.get_json()


def _create_plan(client, auth_headers, **kwargs):
    payload = {"plan_date": "2026-04-15", "item_ids": [1], **kwargs}
    return client.post("/calendar/plans", json=payload, headers=auth_headers)


# ─── GET /calendar/plans ────────────────────────────────────────────────────

class TestGetPlans:
    def test_empty_month(self, client, auth_headers):
        resp = client.get("/calendar/plans?month=2026-04", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["plans"] == []
        assert body["count"] == 0
        assert body["month"] == "2026-04"

    def test_plans_filtered_by_month(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            item = _upload_item(client, auth_headers, minimal_png)

            # Create plans in April and May
            client.post("/calendar/plans", json={
                "plan_date": "2026-04-10", "item_ids": [item["id"]], "notes": "April plan",
            }, headers=auth_headers)
            client.post("/calendar/plans", json={
                "plan_date": "2026-05-01", "item_ids": [item["id"]], "notes": "May plan",
            }, headers=auth_headers)

        # Query April only
        resp = client.get("/calendar/plans?month=2026-04", headers=auth_headers)
        body = resp.get_json()
        assert body["count"] == 1
        assert body["plans"][0]["notes"] == "April plan"

    def test_missing_month_param(self, client, auth_headers):
        resp = client.get("/calendar/plans", headers=auth_headers)
        assert resp.status_code == 400

    def test_invalid_month_format(self, client, auth_headers):
        resp = client.get("/calendar/plans?month=abc", headers=auth_headers)
        assert resp.status_code == 400

    def test_requires_auth(self, client):
        resp = client.get("/calendar/plans?month=2026-04")
        assert resp.status_code == 401


# ─── POST /calendar/plans ───────────────────────────────────────────────────

class TestCreatePlan:
    def test_create_with_item_ids(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            item = _upload_item(client, auth_headers, minimal_png)

        resp = client.post("/calendar/plans", json={
            "plan_date": "2026-04-15",
            "occasion": "casual",
            "item_ids": [item["id"]],
            "notes": "Test plan",
        }, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["plan_date"] == "2026-04-15"
        assert body["occasion"] == "casual"
        assert body["notes"] == "Test plan"
        assert "id" in body

    def test_create_with_saved_outfit(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            item = _upload_item(client, auth_headers, minimal_png)
            saved = _save_outfit(client, auth_headers, [item["id"]])

        resp = client.post("/calendar/plans", json={
            "plan_date": "2026-04-20",
            "saved_outfit_id": saved["id"],
        }, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["saved_outfit_id"] == saved["id"]
        assert body["saved_outfit"]["name"] is not None

    def test_duplicate_date_returns_409(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            item = _upload_item(client, auth_headers, minimal_png)

        # First plan
        resp1 = client.post("/calendar/plans", json={
            "plan_date": "2026-04-25", "item_ids": [item["id"]],
        }, headers=auth_headers)
        assert resp1.status_code == 201

        # Duplicate
        resp2 = client.post("/calendar/plans", json={
            "plan_date": "2026-04-25", "item_ids": [item["id"]],
        }, headers=auth_headers)
        assert resp2.status_code == 409

    def test_missing_date(self, client, auth_headers):
        resp = client.post("/calendar/plans", json={
            "item_ids": [1],
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_missing_items_and_outfit(self, client, auth_headers):
        resp = client.post("/calendar/plans", json={
            "plan_date": "2026-04-15",
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_invalid_occasion(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            item = _upload_item(client, auth_headers, minimal_png)

        resp = client.post("/calendar/plans", json={
            "plan_date": "2026-04-15",
            "occasion": "party",
            "item_ids": [item["id"]],
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_invalid_date_format(self, client, auth_headers):
        resp = client.post("/calendar/plans", json={
            "plan_date": "15-04-2026", "item_ids": [1],
        }, headers=auth_headers)
        assert resp.status_code == 400

    def test_notes_too_long(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            item = _upload_item(client, auth_headers, minimal_png)

        resp = client.post("/calendar/plans", json={
            "plan_date": "2026-04-15",
            "item_ids": [item["id"]],
            "notes": "x" * 201,
        }, headers=auth_headers)
        assert resp.status_code == 422

    def test_saved_outfit_not_found(self, client, auth_headers):
        resp = client.post("/calendar/plans", json={
            "plan_date": "2026-04-15", "saved_outfit_id": 9999,
        }, headers=auth_headers)
        assert resp.status_code == 404

    def test_items_not_owned(self, flask_app, client, auth_headers):
        # Item ID 9999 doesn't exist
        resp = client.post("/calendar/plans", json={
            "plan_date": "2026-04-15", "item_ids": [9999],
        }, headers=auth_headers)
        assert resp.status_code == 403

    def test_requires_auth(self, client):
        resp = client.post("/calendar/plans", json={
            "plan_date": "2026-04-15", "item_ids": [1],
        })
        assert resp.status_code == 401


# ─── PATCH /calendar/plans/<id> ──────────────────────────────────────────────

class TestUpdatePlan:
    def test_update_notes(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            item = _upload_item(client, auth_headers, minimal_png)
            resp = client.post("/calendar/plans", json={
                "plan_date": "2026-04-15", "item_ids": [item["id"]], "notes": "old",
            }, headers=auth_headers)
            plan_id = resp.get_json()["id"]

        resp = client.patch(f"/calendar/plans/{plan_id}", json={
            "notes": "updated notes",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["notes"] == "updated notes"

    def test_update_occasion(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            item = _upload_item(client, auth_headers, minimal_png)
            resp = client.post("/calendar/plans", json={
                "plan_date": "2026-04-16", "item_ids": [item["id"]], "occasion": "casual",
            }, headers=auth_headers)
            plan_id = resp.get_json()["id"]

        resp = client.patch(f"/calendar/plans/{plan_id}", json={
            "occasion": "formal",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["occasion"] == "formal"

    def test_update_not_found(self, client, auth_headers):
        resp = client.patch("/calendar/plans/9999", json={"notes": "x"}, headers=auth_headers)
        assert resp.status_code == 404

    def test_update_not_owner(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            item = _upload_item(client, auth_headers, minimal_png)
            resp = client.post("/calendar/plans", json={
                "plan_date": "2026-04-17", "item_ids": [item["id"]],
            }, headers=auth_headers)
            plan_id = resp.get_json()["id"]

        # Register second user
        client.post("/auth/register", json={
            "name": "User2", "email": "user2@test.com", "password": "password123", "gender": "women",
        })
        resp2 = client.post("/auth/login", json={"email": "user2@test.com", "password": "password123"})
        headers2 = {"Authorization": f"Bearer {resp2.get_json()['access_token']}"}

        resp = client.patch(f"/calendar/plans/{plan_id}", json={"notes": "hacked"}, headers=headers2)
        assert resp.status_code == 403


# ─── DELETE /calendar/plans/<id> ─────────────────────────────────────────────

class TestDeletePlan:
    def test_delete_plan(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            item = _upload_item(client, auth_headers, minimal_png)
            resp = client.post("/calendar/plans", json={
                "plan_date": "2026-04-18", "item_ids": [item["id"]],
            }, headers=auth_headers)
            plan_id = resp.get_json()["id"]

        resp = client.delete(f"/calendar/plans/{plan_id}", headers=auth_headers)
        assert resp.status_code == 200

        # Verify gone
        resp = client.get("/calendar/plans?month=2026-04", headers=auth_headers)
        assert resp.get_json()["count"] == 0

    def test_delete_not_found(self, client, auth_headers):
        resp = client.delete("/calendar/plans/9999", headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_not_owner(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            item = _upload_item(client, auth_headers, minimal_png)
            resp = client.post("/calendar/plans", json={
                "plan_date": "2026-04-19", "item_ids": [item["id"]],
            }, headers=auth_headers)
            plan_id = resp.get_json()["id"]

        client.post("/auth/register", json={
            "name": "User3", "email": "user3@test.com", "password": "password123", "gender": "men",
        })
        resp2 = client.post("/auth/login", json={"email": "user3@test.com", "password": "password123"})
        headers2 = {"Authorization": f"Bearer {resp2.get_json()['access_token']}"}

        resp = client.delete(f"/calendar/plans/{plan_id}", headers=headers2)
        assert resp.status_code == 403


# ─── Edge Cases ──────────────────────────────────────────────────────────────

class TestCalendarEdgeCases:
    def test_plan_includes_item_images(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            item = _upload_item(client, auth_headers, minimal_png)
            client.post("/calendar/plans", json={
                "plan_date": "2026-04-22", "item_ids": [item["id"]],
            }, headers=auth_headers)

        resp = client.get("/calendar/plans?month=2026-04", headers=auth_headers)
        plan = resp.get_json()["plans"][0]
        assert len(plan["items"]) == 1
        assert plan["items"][0]["image_url"].startswith("/uploads/")

    def test_plan_with_saved_outfit_shows_items(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            item = _upload_item(client, auth_headers, minimal_png)
            saved = _save_outfit(client, auth_headers, [item["id"]])

            client.post("/calendar/plans", json={
                "plan_date": "2026-04-23", "saved_outfit_id": saved["id"],
            }, headers=auth_headers)

        resp = client.get("/calendar/plans?month=2026-04", headers=auth_headers)
        plan = resp.get_json()["plans"][0]
        assert len(plan["items"]) >= 1

    def test_cascade_delete_user(self, flask_app, client, auth_headers, minimal_png):
        """When a user is deleted, their plans should also be deleted."""
        with flask_app.app_context():
            from app.models_db import User, OutfitPlan
            from app.extensions import db

            item = _upload_item(client, auth_headers, minimal_png)
            client.post("/calendar/plans", json={
                "plan_date": "2026-04-24", "item_ids": [item["id"]],
            }, headers=auth_headers)

            # Verify plan exists
            assert OutfitPlan.query.filter_by(user_id=1).count() == 1

            # Delete user
            user = db.session.get(User, 1)
            db.session.delete(user)
            db.session.commit()

            # Plans should be gone
            assert OutfitPlan.query.filter_by(user_id=1).count() == 0
