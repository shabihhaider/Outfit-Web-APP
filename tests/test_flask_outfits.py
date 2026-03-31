"""
tests/test_flask_outfits.py
Tests for Phase 5.5 features:
  - GET  /outfits/history
  - POST /outfits/saved
  - GET  /outfits/saved
  - DELETE /outfits/saved/<id>
  - POST /outfits/<history_id>/feedback
  - POST /recommendations/around-item/<item_id>

Covers all 11 test cases from Section 8 of PHASE5_5_ENGINEERING_PLAN.md.
"""

from __future__ import annotations

import io
import json

import numpy as np
import pytest

from engine.models import (
    OutfitCandidate, OutfitTemplate, WardrobeItem,
    Category, Formality, Gender, InsufficientWardrobeError,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_embedding(seed: int = 0) -> list[float]:
    rng = np.random.default_rng(seed)
    return rng.random(1280).astype(np.float32).tolist()


def _make_wardrobe_item(item_id: int, category: Category) -> WardrobeItem:
    return WardrobeItem(
        item_id      = item_id,
        category     = category,
        formality    = Formality.BOTH,
        gender       = Gender.UNISEX,
        embedding    = _make_embedding(item_id),
        dominant_hue = 30.0,
        dominant_sat = 0.8,
        dominant_val = 0.7,
    )


def _make_outfit(item_ids: list[int], categories: list[Category],
                 template: OutfitTemplate = OutfitTemplate.A) -> OutfitCandidate:
    """Create an OutfitCandidate for mock pipeline returns."""
    items = [_make_wardrobe_item(iid, cat) for iid, cat in zip(item_ids, categories)]
    return OutfitCandidate(
        items          = items,
        template_id    = template,
        final_score    = 0.82,
        model2_score   = 0.78,
        color_score    = 0.90,
        weather_score  = 0.85,
        cohesion_score = 0.80,
        confidence     = "high",
    )


def _upload_item(client, auth_headers, flask_app, minimal_png: bytes,
                 category: str = "top") -> dict:
    """Upload one wardrobe item with the given category (via mock pipeline)."""
    flask_app.pipeline.classify_and_embed.return_value = (
        category, np.zeros(1280, dtype=np.float32), 0.95
    )
    resp = client.post(
        "/wardrobe/items",
        data={
            "image":     (io.BytesIO(minimal_png), "item.png", "image/png"),
            "formality": "both",
            "gender":    "unisex",
        },
        headers=auth_headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return resp.get_json()


def _register_user_b(client) -> dict:
    """Register a second user and return their auth headers."""
    client.post(
        "/auth/register",
        json={
            "name": "User B",
            "email": "userb_outfits@example.com",
            "password": "password123",
            "gender": "men",
        },
    )
    resp = client.post(
        "/auth/login",
        json={"email": "userb_outfits@example.com", "password": "password123"},
    )
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _post_recommendation(client, auth_headers, flask_app,
                         item_ids: list[int], categories: list[Category]) -> None:
    """
    POST /recommendations returning a single outfit composed of the given items.
    Used by tests that need a history entry to exist.
    """
    outfit = _make_outfit(item_ids, categories)
    flask_app.pipeline.recommend.return_value = [outfit]
    resp = client.post(
        "/recommendations",
        json={"occasion": "casual", "temp_celsius": 28.0},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)


# ─── Test 1: History auto-logged after recommendation ─────────────────────────

class TestHistoryAutoLogged:
    def test_history_logged_after_recommendation(
        self, client, flask_app, auth_headers, minimal_png
    ):
        """POST /recommendations → GET /outfits/history has new entry."""
        top_item    = _upload_item(client, auth_headers, flask_app, minimal_png, "top")
        bottom_item = _upload_item(client, auth_headers, flask_app, minimal_png, "bottom")
        shoes_item  = _upload_item(client, auth_headers, flask_app, minimal_png, "shoes")

        item_ids   = [top_item["id"], bottom_item["id"], shoes_item["id"]]
        categories = [Category.TOP, Category.BOTTOM, Category.SHOES]

        _post_recommendation(client, auth_headers, flask_app, item_ids, categories)

        resp = client.get("/outfits/history", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["count"] >= 1
        entry = body["history"][0]
        assert entry["occasion"] == "casual"
        assert entry["temperature_used"] == 28.0
        assert entry["confidence"] == "high"
        assert len(entry["items"]) == 3

    def test_history_empty_initially(self, client, auth_headers):
        resp = client.get("/outfits/history", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 0


# ─── Test 2: History returns only own entries ─────────────────────────────────

class TestHistoryIsolation:
    def test_history_isolation_between_users(
        self, client, flask_app, auth_headers, minimal_png
    ):
        """User A's history is invisible to User B."""
        top_item    = _upload_item(client, auth_headers, flask_app, minimal_png, "top")
        bottom_item = _upload_item(client, auth_headers, flask_app, minimal_png, "bottom")
        shoes_item  = _upload_item(client, auth_headers, flask_app, minimal_png, "shoes")

        item_ids   = [top_item["id"], bottom_item["id"], shoes_item["id"]]
        categories = [Category.TOP, Category.BOTTOM, Category.SHOES]
        _post_recommendation(client, auth_headers, flask_app, item_ids, categories)

        headers_b = _register_user_b(client)
        resp = client.get("/outfits/history", headers=headers_b)
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 0


# ─── Test 3: Save outfit ──────────────────────────────────────────────────────

class TestSaveOutfit:
    def test_save_and_list_outfit(self, client, auth_headers, minimal_png, flask_app):
        """POST /outfits/saved → GET /outfits/saved shows it."""
        item = _upload_item(client, auth_headers, flask_app, minimal_png, "top")

        payload = {
            "name":        "Office Monday",
            "occasion":    "formal",
            "item_ids":    [item["id"]],
            "final_score": 0.84,
            "confidence":  "high",
        }
        resp = client.post("/outfits/saved", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["name"] == "Office Monday"
        assert "id" in body

        list_resp = client.get("/outfits/saved", headers=auth_headers)
        assert list_resp.status_code == 200
        saved_body = list_resp.get_json()
        assert saved_body["count"] == 1
        assert saved_body["saved"][0]["name"] == "Office Monday"

    def test_save_missing_required_fields(self, client, auth_headers):
        resp = client.post(
            "/outfits/saved",
            json={"name": "Test"},  # missing occasion, item_ids, final_score, confidence
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_save_requires_auth(self, client):
        resp = client.post("/outfits/saved", json={})
        assert resp.status_code == 401


# ─── Test 4: Delete saved outfit ─────────────────────────────────────────────

class TestDeleteSaved:
    def _create_saved(self, client, auth_headers) -> int:
        resp = client.post(
            "/outfits/saved",
            json={
                "name": "Delete Me",
                "occasion": "casual",
                "item_ids": [1],
                "final_score": 0.5,
                "confidence": "medium",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        return resp.get_json()["id"]

    def test_delete_success(self, client, auth_headers):
        saved_id = self._create_saved(client, auth_headers)
        resp = client.delete(f"/outfits/saved/{saved_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert "removed" in resp.get_json()["message"].lower()

        # Confirm it's gone
        list_resp = client.get("/outfits/saved", headers=auth_headers)
        ids = [s["id"] for s in list_resp.get_json()["saved"]]
        assert saved_id not in ids

    def test_delete_other_user_forbidden(self, client, auth_headers):
        saved_id = self._create_saved(client, auth_headers)
        headers_b = _register_user_b(client)
        resp = client.delete(f"/outfits/saved/{saved_id}", headers=headers_b)
        assert resp.status_code == 403

    def test_delete_not_found(self, client, auth_headers):
        resp = client.delete("/outfits/saved/99999", headers=auth_headers)
        assert resp.status_code == 404


# ─── Test 5: Duplicate name rejected ─────────────────────────────────────────

class TestDuplicateName:
    def test_duplicate_name_returns_409(self, client, auth_headers):
        payload = {
            "name": "Weekend Casual",
            "occasion": "casual",
            "item_ids": [1, 2],
            "final_score": 0.75,
            "confidence": "high",
        }
        resp1 = client.post("/outfits/saved", json=payload, headers=auth_headers)
        assert resp1.status_code == 201
        resp2 = client.post("/outfits/saved", json=payload, headers=auth_headers)
        assert resp2.status_code == 409
        assert "already exists" in resp2.get_json()["error"].lower()


# ─── Tests 6 & 7: Feedback thumbs up and thumbs down ─────────────────────────

class TestFeedback:
    def _create_history_entry(self, client, auth_headers, flask_app, minimal_png) -> int:
        """Create one recommendation history entry and return its ID."""
        top    = _upload_item(client, auth_headers, flask_app, minimal_png, "top")
        bottom = _upload_item(client, auth_headers, flask_app, minimal_png, "bottom")
        shoes  = _upload_item(client, auth_headers, flask_app, minimal_png, "shoes")

        ids = [top["id"], bottom["id"], shoes["id"]]
        cats = [Category.TOP, Category.BOTTOM, Category.SHOES]
        _post_recommendation(client, auth_headers, flask_app, ids, cats)

        history_resp = client.get("/outfits/history", headers=auth_headers)
        return history_resp.get_json()["history"][0]["id"]

    def test_thumbs_up(self, client, auth_headers, flask_app, minimal_png):
        history_id = self._create_history_entry(client, auth_headers, flask_app, minimal_png)
        resp = client.post(
            f"/outfits/{history_id}/feedback",
            json={"rating": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert "recorded" in resp.get_json()["message"].lower()

    def test_thumbs_down(self, client, auth_headers, flask_app, minimal_png):
        history_id = self._create_history_entry(client, auth_headers, flask_app, minimal_png)
        resp = client.post(
            f"/outfits/{history_id}/feedback",
            json={"rating": -1},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    def test_invalid_rating_rejected(self, client, auth_headers, flask_app, minimal_png):
        history_id = self._create_history_entry(client, auth_headers, flask_app, minimal_png)
        resp = client.post(
            f"/outfits/{history_id}/feedback",
            json={"rating": 0},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_feedback_not_found(self, client, auth_headers):
        resp = client.post(
            "/outfits/99999/feedback",
            json={"rating": 1},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    # ─── Test 8: Double feedback rejected ─────────────────────────────────────

    def test_double_feedback_rejected(self, client, auth_headers, flask_app, minimal_png):
        """Second rating on the same history entry → 409."""
        history_id = self._create_history_entry(client, auth_headers, flask_app, minimal_png)
        client.post(
            f"/outfits/{history_id}/feedback",
            json={"rating": 1},
            headers=auth_headers,
        )
        resp2 = client.post(
            f"/outfits/{history_id}/feedback",
            json={"rating": -1},
            headers=auth_headers,
        )
        assert resp2.status_code == 409
        assert "already rated" in resp2.get_json()["error"].lower()


# ─── Tests 9–11: Anchor-item endpoint ────────────────────────────────────────

class TestAnchorEndpoint:

    # ─── Test 9: All returned outfits contain the anchor item ─────────────────

    def test_anchor_item_included_in_all_outfits(
        self, client, flask_app, auth_headers, minimal_png
    ):
        """POST /recommendations/around-item/<id>: all outfits contain the anchor item."""
        anchor = _upload_item(client, auth_headers, flask_app, minimal_png, "top")
        bottom = _upload_item(client, auth_headers, flask_app, minimal_png, "bottom")
        shoes  = _upload_item(client, auth_headers, flask_app, minimal_png, "shoes")

        anchor_id  = anchor["id"]
        item_ids   = [anchor_id, bottom["id"], shoes["id"]]
        categories = [Category.TOP, Category.BOTTOM, Category.SHOES]

        # Mock pipeline returns outfit containing the anchor item
        outfit = _make_outfit(item_ids, categories)
        flask_app.pipeline.recommend.return_value = [outfit]

        resp = client.post(
            f"/recommendations/around-item/{anchor_id}",
            json={"occasion": "casual", "temp_celsius": 30.0},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["outfits"]) == 1

        # Verify anchor item ID appears in returned outfit items
        returned_ids = [item["id"] for item in body["outfits"][0]["items"]]
        assert anchor_id in returned_ids

        # Verify pipeline.recommend was called with the anchor_item_id kwarg
        call_kwargs = flask_app.pipeline.recommend.call_args.kwargs
        assert call_kwargs.get("anchor_item_id") == anchor_id

    # ─── Test 10: Anchor endpoint — wrong user's item → 403 ──────────────────

    def test_anchor_wrong_user_forbidden(
        self, client, flask_app, auth_headers, minimal_png
    ):
        """Using another user's item as anchor → 403."""
        # Upload item as user A
        anchor = _upload_item(client, auth_headers, flask_app, minimal_png, "top")
        anchor_id = anchor["id"]

        # Request as user B
        headers_b = _register_user_b(client)
        resp = client.post(
            f"/recommendations/around-item/{anchor_id}",
            json={"occasion": "casual", "temp_celsius": 28.0},
            headers=headers_b,
        )
        assert resp.status_code == 403

    # ─── Test 11: Anchor endpoint — insufficient wardrobe → 422 ──────────────

    def test_anchor_insufficient_wardrobe_returns_422(
        self, client, flask_app, auth_headers, minimal_png
    ):
        """InsufficientWardrobeError from the engine → 422."""
        anchor = _upload_item(client, auth_headers, flask_app, minimal_png, "top")
        flask_app.pipeline.recommend.side_effect = InsufficientWardrobeError("not enough")

        resp = client.post(
            f"/recommendations/around-item/{anchor['id']}",
            json={"occasion": "casual", "temp_celsius": 28.0},
            headers=auth_headers,
        )
        assert resp.status_code == 422
        assert "wardrobe" in resp.get_json()["error"].lower()

    def test_anchor_item_not_found_returns_404(self, client, auth_headers):
        resp = client.post(
            "/recommendations/around-item/99999",
            json={"occasion": "casual", "temp_celsius": 28.0},
            headers=auth_headers,
        )
        assert resp.status_code == 404
