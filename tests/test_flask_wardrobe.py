"""
tests/test_flask_wardrobe.py
Tests for:
  POST   /wardrobe/items       — upload
  GET    /wardrobe/items       — list
  DELETE /wardrobe/items/<id>  — delete
  GET    /uploads/<filename>   — serve image (ownership check)
"""

from __future__ import annotations

import io
import json

import numpy as np
import pytest


# ─── Upload ───────────────────────────────────────────────────────────────────

class TestUpload:
    def test_upload_success(self, client, auth_headers, minimal_png):
        data = {
            "image":    (io.BytesIO(minimal_png), "shirt.png", "image/png"),
            "formality": "casual",
            "gender":    "men",
        }
        resp = client.post(
            "/wardrobe/items",
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["category"] == "top"
        assert body["formality"] == "casual"
        assert body["gender"] == "men"
        assert body["image_url"].startswith("/uploads/")
        assert "id" in body

    def test_upload_requires_auth(self, client, minimal_png):
        data = {
            "image":    (io.BytesIO(minimal_png), "shirt.png", "image/png"),
            "formality": "casual",
            "gender":    "men",
        }
        resp = client.post(
            "/wardrobe/items",
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 401

    def test_upload_no_file(self, client, auth_headers):
        resp = client.post(
            "/wardrobe/items",
            data={"formality": "casual", "gender": "men"},
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_upload_invalid_extension(self, client, auth_headers):
        data = {
            "image":    (io.BytesIO(b"not an image"), "doc.pdf", "application/pdf"),
            "formality": "casual",
            "gender":    "men",
        }
        resp = client.post(
            "/wardrobe/items",
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_upload_invalid_formality(self, client, auth_headers, minimal_png):
        data = {
            "image":    (io.BytesIO(minimal_png), "shirt.png", "image/png"),
            "formality": "weekend",   # invalid
            "gender":    "men",
        }
        resp = client.post(
            "/wardrobe/items",
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 422

    def test_upload_unknown_gender_falls_back_to_unisex(self, client, auth_headers, minimal_png):
        # Gender is optional; unknown values fall back to "unisex".
        # Personal wardrobe does not gender-gate items — the field is kept
        # for future personalization features only.
        data = {
            "image":    (io.BytesIO(minimal_png), "shirt.png", "image/png"),
            "formality": "casual",
            "gender":    "alien",   # unknown → coerced to unisex
        }
        resp = client.post(
            "/wardrobe/items",
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        assert resp.get_json()["gender"] == "unisex"

    def test_upload_fake_image(self, client, auth_headers):
        """A text file with .jpg extension must be rejected by Pillow verify."""
        data = {
            "image":    (io.BytesIO(b"I am not a real image"), "fake.jpg", "image/jpeg"),
            "formality": "casual",
            "gender":    "men",
        }
        resp = client.post(
            "/wardrobe/items",
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_upload_stores_category_from_pipeline(self, client, flask_app, auth_headers, minimal_png):
        """Pipeline returns 'dress' — DB and response should show 'dress'."""
        flask_app.pipeline.classify_and_embed.return_value = (
            "dress",
            np.zeros(1280, dtype=np.float32),
            0.91,
        )
        data = {
            "image":    (io.BytesIO(minimal_png), "dress.png", "image/png"),
            "formality": "formal",
            "gender":    "women",
        }
        resp = client.post(
            "/wardrobe/items",
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        assert resp.get_json()["category"] == "dress"

    def test_upload_non_clothing_rejected(self, client, flask_app, auth_headers, minimal_png):
        """Pipeline raises ValueError (low confidence) → 422."""
        flask_app.pipeline.classify_and_embed.side_effect = ValueError(
            "Image does not appear to be a clothing item (confidence 0.20 < 0.45). "
            "Please upload a clear photo of a single clothing item."
        )
        data = {
            "image":    (io.BytesIO(minimal_png), "face.jpg", "image/jpeg"),
            "formality": "casual",
            "gender":    "men",
        }
        resp = client.post(
            "/wardrobe/items",
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 422
        assert "clothing" in resp.get_json()["error"].lower()
        flask_app.pipeline.classify_and_embed.side_effect = None  # reset

    def test_upload_confidence_stored(self, client, flask_app, auth_headers, minimal_png):
        """model_confidence from pipeline is stored and returned in the response."""
        flask_app.pipeline.classify_and_embed.return_value = (
            "top",
            np.zeros(1280, dtype=np.float32),
            0.87,
        )
        data = {
            "image":    (io.BytesIO(minimal_png), "shirt.png", "image/png"),
            "formality": "casual",
            "gender":    "men",
        }
        resp = client.post(
            "/wardrobe/items",
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert "model_confidence" in body
        assert abs(body["model_confidence"] - 0.87) < 0.001

    def test_upload_includes_tips(self, client, auth_headers, minimal_png):
        """201 response must include a non-empty 'tips' list."""
        data = {
            "image":    (io.BytesIO(minimal_png), "shirt.png", "image/png"),
            "formality": "casual",
            "gender":    "men",
        }
        resp = client.post(
            "/wardrobe/items",
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert "tips" in body
        assert isinstance(body["tips"], list)
        assert len(body["tips"]) > 0

    def test_upload_wardrobe_full(self, client, flask_app, auth_headers, minimal_png):
        """Returns 400 when wardrobe already has 50 items."""
        from app.extensions import db
        from app.models_db import WardrobeItemDB, User

        user = User.query.filter_by(email="test@example.com").first()
        for i in range(50):
            fake = WardrobeItemDB(
                user_id          = user.id,
                image_filename   = f"fake_{i}.png",
                category         = "top",
                formality        = "casual",
                gender           = "men",
                embedding        = json.dumps([0.0] * 1280),
                color_hue        = 0.0,
                color_sat        = 0.0,
                color_val        = 0.0,
                model_confidence = None,
            )
            db.session.add(fake)
        db.session.commit()

        data = {
            "image":    (io.BytesIO(minimal_png), "shirt.png", "image/png"),
            "formality": "casual",
            "gender":    "men",
        }
        resp = client.post(
            "/wardrobe/items",
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert "full" in resp.get_json()["error"].lower()


# ─── List ─────────────────────────────────────────────────────────────────────

class TestList:
    def test_list_empty(self, client, auth_headers):
        resp = client.get("/wardrobe/items", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["items"] == []
        assert body["count"] == 0

    def test_list_after_upload(self, client, auth_headers, upload_item):
        resp = client.get("/wardrobe/items", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers.get("Cache-Control") == "private, max-age=60, stale-while-revalidate=300"
        assert "Authorization" in (resp.headers.get("Vary") or "")
        body = resp.get_json()
        assert body["count"] == 1
        assert body["items"][0]["id"] == upload_item["id"]

    def test_list_requires_auth(self, client):
        resp = client.get("/wardrobe/items")
        assert resp.status_code == 401

    def test_list_isolation_between_users(self, client, auth_headers, minimal_png):
        """Items uploaded by user A must not appear in user B's list."""
        # Upload one item as user A (auth_headers)
        client.post(
            "/wardrobe/items",
            data={
                "image":    (io.BytesIO(minimal_png), "a.png", "image/png"),
                "formality": "casual",
                "gender":    "men",
            },
            headers=auth_headers,
            content_type="multipart/form-data",
        )

        # Register + login user B
        client.post(
            "/auth/register",
            json={
                "name": "User B",
                "email": "userb@example.com",
                "password": "password123",
                "gender": "women",
            },
        )
        login_resp = client.post(
            "/auth/login",
            json={"email": "userb@example.com", "password": "password123"},
        )
        token_b = login_resp.get_json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        resp = client.get("/wardrobe/items", headers=headers_b)
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 0


# ─── Delete ───────────────────────────────────────────────────────────────────

class TestDelete:
    def test_delete_success(self, client, auth_headers, upload_item):
        item_id = upload_item["id"]
        resp = client.delete(f"/wardrobe/items/{item_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert "deleted" in resp.get_json()["message"].lower()

        # Confirm it's gone
        list_resp = client.get("/wardrobe/items", headers=auth_headers)
        assert list_resp.get_json()["count"] == 0

    def test_delete_not_found(self, client, auth_headers):
        resp = client.delete("/wardrobe/items/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_forbidden(self, client, auth_headers, upload_item, minimal_png):
        """User B cannot delete user A's item."""
        item_id = upload_item["id"]

        # Register user B
        client.post(
            "/auth/register",
            json={
                "name": "User B",
                "email": "del_b@example.com",
                "password": "password123",
                "gender": "men",
            },
        )
        login_resp = client.post(
            "/auth/login",
            json={"email": "del_b@example.com", "password": "password123"},
        )
        token_b = login_resp.get_json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        resp = client.delete(f"/wardrobe/items/{item_id}", headers=headers_b)
        assert resp.status_code == 403

    def test_delete_requires_auth(self, client):
        resp = client.delete("/wardrobe/items/1")
        assert resp.status_code == 401


# ─── Serve uploads ────────────────────────────────────────────────────────────

class TestServeUpload:
    def test_serve_own_file(self, client, auth_headers, upload_item):
        image_url = upload_item["image_url"]   # e.g. /uploads/1_abc.png
        filename = image_url.split("/uploads/")[1]
        resp = client.get(f"/uploads/{filename}", headers=auth_headers)
        # File may not physically exist on disk in tests, but DB record exists → 200 or 404 from disk
        assert resp.status_code in (200, 404)

    def test_serve_upload_no_auth(self, client, upload_item):
        """After FIX 2: no JWT required — unauthenticated requests are allowed."""
        image_url = upload_item["image_url"]
        filename = image_url.split("/uploads/")[1]
        resp = client.get(f"/uploads/{filename}")
        if resp.status_code in (200, 302):
            assert resp.headers.get("Cache-Control") == "public, max-age=86400"
        # DB record exists, so not 401/403. File may not be on disk → 200 or 404.
        assert resp.status_code in (200, 404)

    def test_serve_upload_not_found(self, client):
        """Filename not in DB → 404 (no auth needed)."""
        resp = client.get("/uploads/nonexistent_file_xyz.jpg")
        assert resp.status_code == 404


# ─── Edit (PATCH) ─────────────────────────────────────────────────────────────

class TestEditItem:
    def test_patch_category(self, client, auth_headers, upload_item):
        """Valid category patch → 200 with updated category."""
        item_id = upload_item["id"]
        resp = client.patch(
            f"/wardrobe/items/{item_id}",
            json={"category": "bottom"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["category"] == "bottom"

    def test_patch_formality(self, client, auth_headers, upload_item):
        """Valid formality patch → 200 with updated formality."""
        item_id = upload_item["id"]
        resp = client.patch(
            f"/wardrobe/items/{item_id}",
            json={"formality": "formal"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["formality"] == "formal"

    def test_patch_invalid_category(self, client, auth_headers, upload_item):
        """Invalid category value → 422."""
        item_id = upload_item["id"]
        resp = client.patch(
            f"/wardrobe/items/{item_id}",
            json={"category": "hat"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_patch_wrong_user_forbidden(self, client, auth_headers, upload_item):
        """User B cannot patch user A's item → 403."""
        item_id = upload_item["id"]

        client.post(
            "/auth/register",
            json={
                "name": "User B",
                "email": "patch_b@example.com",
                "password": "password123",
                "gender": "men",
            },
        )
        login_resp = client.post(
            "/auth/login",
            json={"email": "patch_b@example.com", "password": "password123"},
        )
        headers_b = {"Authorization": f"Bearer {login_resp.get_json()['access_token']}"}
        resp = client.patch(
            f"/wardrobe/items/{item_id}",
            json={"category": "shoes"},
            headers=headers_b,
        )
        assert resp.status_code == 403

    def test_patch_empty_body(self, client, auth_headers, upload_item):
        """Empty JSON body (no fields) → 400."""
        item_id = upload_item["id"]
        resp = client.patch(
            f"/wardrobe/items/{item_id}",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 400


# ─── Archive ──────────────────────────────────────────────────────────────────

class TestArchiveItem:
    def test_archive_success(self, client, auth_headers, upload_item):
        """Archiving an item returns 200 and sets is_archived=True."""
        item_id = upload_item["id"]
        resp = client.patch(
            f"/wardrobe/items/{item_id}/archive",
            json={"archived": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["is_archived"] is True

    def test_unarchive_success(self, client, auth_headers, upload_item):
        """Unarchiving an item returns 200 and sets is_archived=False."""
        item_id = upload_item["id"]
        # Archive first
        client.patch(
            f"/wardrobe/items/{item_id}/archive",
            json={"archived": True},
            headers=auth_headers,
        )
        # Then unarchive
        resp = client.patch(
            f"/wardrobe/items/{item_id}/archive",
            json={"archived": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["is_archived"] is False

    def test_archive_not_found(self, client, auth_headers):
        """Non-existent item → 404."""
        resp = client.patch(
            "/wardrobe/items/99999/archive",
            json={"archived": True},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_archive_forbidden(self, client, auth_headers, upload_item):
        """User B cannot archive user A's item → 403."""
        item_id = upload_item["id"]
        client.post(
            "/auth/register",
            json={
                "name": "User B",
                "email": "archive_b@example.com",
                "password": "password123",
                "gender": "men",
            },
        )
        login_resp = client.post(
            "/auth/login",
            json={"email": "archive_b@example.com", "password": "password123"},
        )
        headers_b = {"Authorization": f"Bearer {login_resp.get_json()['access_token']}"}
        resp = client.patch(
            f"/wardrobe/items/{item_id}/archive",
            json={"archived": True},
            headers=headers_b,
        )
        assert resp.status_code == 403

    def test_archive_requires_auth(self, client, upload_item):
        """No JWT → 401."""
        item_id = upload_item["id"]
        resp = client.patch(
            f"/wardrobe/items/{item_id}/archive",
            json={"archived": True},
        )
        assert resp.status_code == 401

    def test_archive_invalid_body(self, client, auth_headers, upload_item):
        """Body with non-boolean 'archived' → 400."""
        item_id = upload_item["id"]
        resp = client.patch(
            f"/wardrobe/items/{item_id}/archive",
            json={"archived": "yes"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_archive_missing_body(self, client, auth_headers, upload_item):
        """Body without 'archived' key → 400."""
        item_id = upload_item["id"]
        resp = client.patch(
            f"/wardrobe/items/{item_id}/archive",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_unarchive_blocked_at_cap(self, client, auth_headers, upload_item):
        """Unarchiving when active items = 50 → 400."""
        from app.extensions import db
        from app.models_db import WardrobeItemDB, User

        item_id = upload_item["id"]
        # Archive the upload_item first
        client.patch(
            f"/wardrobe/items/{item_id}/archive",
            json={"archived": True},
            headers=auth_headers,
        )

        user = User.query.filter_by(email="test@example.com").first()
        # Fill wardrobe to cap with 50 active items
        for i in range(50):
            fake = WardrobeItemDB(
                user_id          = user.id,
                image_filename   = f"arc_fake_{i}.png",
                category         = "top",
                formality        = "casual",
                gender           = "men",
                embedding        = json.dumps([0.0] * 1280),
                color_hue        = 0.0,
                color_sat        = 0.0,
                color_val        = 0.0,
                model_confidence = None,
            )
            db.session.add(fake)
        db.session.commit()

        resp = client.patch(
            f"/wardrobe/items/{item_id}/archive",
            json={"archived": False},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "capacity" in resp.get_json()["error"].lower()

    def test_archived_items_excluded_from_active_list(self, client, auth_headers, upload_item):
        """Archived item does not appear in default (active) item list."""
        item_id = upload_item["id"]
        client.patch(
            f"/wardrobe/items/{item_id}/archive",
            json={"archived": True},
            headers=auth_headers,
        )
        resp = client.get("/wardrobe/items", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert all(not i["is_archived"] for i in body["items"])
        assert body["count"] == 0

    def test_archived_items_visible_in_archived_list(self, client, auth_headers, upload_item):
        """Archived item appears when ?archived=true is passed."""
        item_id = upload_item["id"]
        client.patch(
            f"/wardrobe/items/{item_id}/archive",
            json={"archived": True},
            headers=auth_headers,
        )
        resp = client.get("/wardrobe/items?archived=true", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["count"] == 1
        assert body["items"][0]["id"] == item_id
        assert body["items"][0]["is_archived"] is True

    def test_active_count_in_list_response(self, client, auth_headers, upload_item):
        """active_count in list response reflects only non-archived items."""
        resp = client.get("/wardrobe/items", headers=auth_headers)
        body = resp.get_json()
        assert "active_count" in body
        assert body["active_count"] == 1

        item_id = upload_item["id"]
        client.patch(
            f"/wardrobe/items/{item_id}/archive",
            json={"archived": True},
            headers=auth_headers,
        )
        resp2 = client.get("/wardrobe/items", headers=auth_headers)
        assert resp2.get_json()["active_count"] == 0

    def test_upload_allowed_when_archived_items_exist(self, client, auth_headers, upload_item, minimal_png):
        """Archived items don't count toward the 50-item cap."""
        item_id = upload_item["id"]
        # Archive the existing item — active count drops to 0
        client.patch(
            f"/wardrobe/items/{item_id}/archive",
            json={"archived": True},
            headers=auth_headers,
        )
        # A new upload should succeed (active count is 0, not 1)
        data = {
            "image":    (io.BytesIO(minimal_png), "shirt2.png", "image/png"),
            "formality": "casual",
            "gender":    "men",
        }
        resp = client.post(
            "/wardrobe/items",
            data=data,
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
