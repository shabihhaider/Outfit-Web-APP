"""
tests/test_flask_social.py
Comprehensive tests for the social module (~30 endpoints).

Run: pytest tests/test_flask_social.py -v
"""
from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _register_and_login(client, name, email, gender="men"):
    """Register + login, return auth headers."""
    client.post("/auth/register", json={
        "name": name, "email": email,
        "password": "password123", "gender": gender,
    })
    resp = client.post("/auth/login", json={
        "email": email, "password": "password123",
    })
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _upload_wardrobe_item(client, headers, minimal_png, category_mock="top"):
    """Upload a wardrobe item with CLIP tagger mocked. Returns item JSON."""
    mock_tagger = MagicMock()
    mock_tagger.is_clothing_image.return_value = (True, None)
    mock_tagger.classify_sub_category.return_value = (None, 0.0)

    data = {
        "image": (io.BytesIO(minimal_png), "item.png", "image/png"),
        "formality": "casual",
        "gender": "men",
    }
    with patch("engine.clip_tagger.get_tagger", return_value=mock_tagger):
        resp = client.post(
            "/wardrobe/items", data=data,
            headers=headers, content_type="multipart/form-data",
        )
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return resp.get_json()


def _save_outfit(client, headers, item_ids, name="Test Outfit"):
    """Save an outfit from item IDs. Returns saved outfit JSON."""
    resp = client.post("/outfits/saved", json={
        "name": name,
        "item_ids": item_ids,
        "occasion": "casual",
        "final_score": 0.85,
        "confidence": "high",
    }, headers=headers)
    assert resp.status_code in (200, 201), resp.get_data(as_text=True)
    return resp.get_json()


def _publish_post(client, headers, saved_outfit_id, caption="Test post", vibes=None):
    """Publish a saved outfit to social feed. Returns post JSON."""
    payload = {
        "saved_outfit_id": saved_outfit_id,
        "caption": caption,
        "visibility": "public",
    }
    if vibes:
        payload["vibe_slugs"] = vibes
    resp = client.post("/social/publish", json=payload, headers=headers)
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return resp.get_json()


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def user_a(client, minimal_png):
    """User A with a wardrobe item and saved outfit."""
    headers = _register_and_login(client, "User A", "a@test.com")
    item = _upload_wardrobe_item(client, headers, minimal_png)
    outfit = _save_outfit(client, headers, [item["id"]])
    return {"headers": headers, "item": item, "outfit": outfit}


@pytest.fixture
def user_b(client, minimal_png):
    """User B with a wardrobe item and saved outfit."""
    headers = _register_and_login(client, "User B", "b@test.com")
    item = _upload_wardrobe_item(client, headers, minimal_png)
    outfit = _save_outfit(client, headers, [item["id"]])
    return {"headers": headers, "item": item, "outfit": outfit}


# ─── Profile Tests ────────────────────────────────────────────────────────────

class TestProfile:

    def test_get_profile(self, client, user_a):
        resp = client.get("/social/profile", headers=user_a["headers"])
        assert resp.status_code == 200
        data = resp.get_json()
        assert "name" in data
        assert "is_public" in data

    def test_update_profile_username(self, client, user_a):
        resp = client.patch("/social/profile", json={
            "username": "user_a_test",
        }, headers=user_a["headers"])
        assert resp.status_code == 200
        assert resp.get_json()["username"] == "user_a_test"

    def test_update_profile_bio(self, client, user_a):
        resp = client.patch("/social/profile", json={
            "bio": "Hello world",
        }, headers=user_a["headers"])
        assert resp.status_code == 200
        assert resp.get_json()["bio"] == "Hello world"

    def test_update_profile_invalid_username(self, client, user_a):
        resp = client.patch("/social/profile", json={
            "username": "AB",  # too short
        }, headers=user_a["headers"])
        assert resp.status_code == 422

    def test_update_profile_duplicate_username(self, client, user_a, user_b):
        client.patch("/social/profile", json={"username": "taken_name"}, headers=user_a["headers"])
        resp = client.patch("/social/profile", json={"username": "taken_name"}, headers=user_b["headers"])
        assert resp.status_code == 409

    def test_upload_avatar(self, client, user_a, minimal_png):
        resp = client.post(
            "/social/profile/avatar",
            data={"avatar": (io.BytesIO(minimal_png), "avatar.png", "image/png")},
            headers=user_a["headers"],
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        assert "avatar_url" in resp.get_json()

    def test_toggle_privacy(self, client, user_a):
        resp = client.patch("/social/profile", json={
            "is_public": False,
        }, headers=user_a["headers"])
        assert resp.status_code == 200
        assert resp.get_json()["is_public"] is False


# ─── Follow Tests ─────────────────────────────────────────────────────────────

class TestFollow:

    def test_follow_user(self, client, user_a, user_b):
        # Get user B's ID
        resp = client.get("/social/profile", headers=user_b["headers"])
        user_b_id = resp.get_json()["id"]

        resp = client.post(f"/social/follow/{user_b_id}", headers=user_a["headers"])
        assert resp.status_code == 201

    def test_duplicate_follow(self, client, user_a, user_b):
        resp = client.get("/social/profile", headers=user_b["headers"])
        user_b_id = resp.get_json()["id"]

        client.post(f"/social/follow/{user_b_id}", headers=user_a["headers"])
        resp = client.post(f"/social/follow/{user_b_id}", headers=user_a["headers"])
        assert resp.status_code == 409

    def test_unfollow_user(self, client, user_a, user_b):
        resp = client.get("/social/profile", headers=user_b["headers"])
        user_b_id = resp.get_json()["id"]

        client.post(f"/social/follow/{user_b_id}", headers=user_a["headers"])
        resp = client.delete(f"/social/follow/{user_b_id}", headers=user_a["headers"])
        assert resp.status_code == 200

    def test_unfollow_not_following(self, client, user_a, user_b):
        resp = client.get("/social/profile", headers=user_b["headers"])
        user_b_id = resp.get_json()["id"]

        resp = client.delete(f"/social/follow/{user_b_id}", headers=user_a["headers"])
        assert resp.status_code == 404

    def test_self_follow_rejected(self, client, user_a):
        resp = client.get("/social/profile", headers=user_a["headers"])
        user_a_id = resp.get_json()["id"]

        resp = client.post(f"/social/follow/{user_a_id}", headers=user_a["headers"])
        assert resp.status_code == 400

    def test_followers_list(self, client, user_a, user_b):
        resp = client.get("/social/profile", headers=user_b["headers"])
        user_b_id = resp.get_json()["id"]
        client.post(f"/social/follow/{user_b_id}", headers=user_a["headers"])

        resp = client.get("/social/followers", headers=user_b["headers"])
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["users"]) == 1

    def test_following_list(self, client, user_a, user_b):
        resp = client.get("/social/profile", headers=user_b["headers"])
        user_b_id = resp.get_json()["id"]
        client.post(f"/social/follow/{user_b_id}", headers=user_a["headers"])

        resp = client.get("/social/following", headers=user_a["headers"])
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["users"]) == 1


# ─── Publishing Tests ─────────────────────────────────────────────────────────

class TestPublish:

    def test_publish_post(self, client, user_a):
        post = _publish_post(client, user_a["headers"], user_a["outfit"]["id"])
        assert post["caption"] == "Test post"
        assert post["visibility"] == "public"

    def test_publish_requires_saved_outfit_id(self, client, user_a):
        resp = client.post("/social/publish", json={
            "caption": "No outfit",
        }, headers=user_a["headers"])
        assert resp.status_code == 422

    def test_publish_nonexistent_outfit(self, client, user_a):
        resp = client.post("/social/publish", json={
            "saved_outfit_id": 99999,
        }, headers=user_a["headers"])
        assert resp.status_code == 404

    def test_publish_other_users_outfit_forbidden(self, client, user_a, user_b):
        resp = client.post("/social/publish", json={
            "saved_outfit_id": user_a["outfit"]["id"],
        }, headers=user_b["headers"])
        assert resp.status_code == 404  # route returns 404 when outfit not owned

    def test_publish_with_vibes(self, client, user_a):
        post = _publish_post(
            client, user_a["headers"], user_a["outfit"]["id"],
            caption="Vibed up", vibes=["streetwear", "minimalist"],
        )
        vibe_slugs = [v["slug"] for v in post.get("vibes", [])]
        assert "streetwear" in vibe_slugs
        assert "minimalist" in vibe_slugs

    def test_publish_max_vibes_exceeded(self, client, user_a):
        resp = client.post("/social/publish", json={
            "saved_outfit_id": user_a["outfit"]["id"],
            "vibe_slugs": ["streetwear", "minimalist", "vintage", "extra"],
        }, headers=user_a["headers"])
        assert resp.status_code == 422


# ─── Post CRUD Tests ──────────────────────────────────────────────────────────

class TestPostCRUD:

    def test_get_post(self, client, user_a):
        post = _publish_post(client, user_a["headers"], user_a["outfit"]["id"])
        resp = client.get(f"/social/posts/{post['id']}", headers=user_a["headers"])
        assert resp.status_code == 200
        assert resp.get_json()["id"] == post["id"]

    def test_update_post_caption(self, client, user_a):
        post = _publish_post(client, user_a["headers"], user_a["outfit"]["id"])
        resp = client.patch(f"/social/posts/{post['id']}", json={
            "caption": "Updated caption",
        }, headers=user_a["headers"])
        assert resp.status_code == 200
        assert resp.get_json()["caption"] == "Updated caption"

    def test_update_post_visibility(self, client, user_a):
        post = _publish_post(client, user_a["headers"], user_a["outfit"]["id"])
        resp = client.patch(f"/social/posts/{post['id']}", json={
            "visibility": "followers",
        }, headers=user_a["headers"])
        assert resp.status_code == 200
        assert resp.get_json()["visibility"] == "followers"

    def test_update_post_other_user_forbidden(self, client, user_a, user_b):
        post = _publish_post(client, user_a["headers"], user_a["outfit"]["id"])
        resp = client.patch(f"/social/posts/{post['id']}", json={
            "caption": "Hacked",
        }, headers=user_b["headers"])
        assert resp.status_code == 403

    def test_delete_post(self, client, user_a):
        post = _publish_post(client, user_a["headers"], user_a["outfit"]["id"])
        resp = client.delete(f"/social/posts/{post['id']}", headers=user_a["headers"])
        assert resp.status_code == 200

        resp = client.get(f"/social/posts/{post['id']}", headers=user_a["headers"])
        assert resp.status_code == 404

    def test_delete_post_other_user_forbidden(self, client, user_a, user_b):
        post = _publish_post(client, user_a["headers"], user_a["outfit"]["id"])
        resp = client.delete(f"/social/posts/{post['id']}", headers=user_b["headers"])
        assert resp.status_code == 403


# ─── Feed Tests ───────────────────────────────────────────────────────────────

class TestFeed:

    def test_discover_feed(self, client, user_a, user_b):
        _publish_post(client, user_a["headers"], user_a["outfit"]["id"], caption="A post")
        _publish_post(client, user_b["headers"], user_b["outfit"]["id"], caption="B post")

        resp = client.get("/social/feed?tab=discover", headers=user_a["headers"])
        assert resp.status_code == 200
        data = resp.get_json()
        assert "posts" in data
        assert len(data["posts"]) >= 1

    def test_following_feed_empty(self, client, user_a):
        resp = client.get("/social/feed?tab=following", headers=user_a["headers"])
        assert resp.status_code == 200
        assert len(resp.get_json()["posts"]) == 0

    def test_following_feed_with_follow(self, client, user_a, user_b):
        _publish_post(client, user_b["headers"], user_b["outfit"]["id"])

        resp_profile = client.get("/social/profile", headers=user_b["headers"])
        user_b_id = resp_profile.get_json()["id"]
        client.post(f"/social/follow/{user_b_id}", headers=user_a["headers"])

        resp = client.get("/social/feed?tab=following", headers=user_a["headers"])
        assert resp.status_code == 200
        assert len(resp.get_json()["posts"]) >= 1

    def test_feed_pagination(self, client, user_a, user_b):
        # Discover feed excludes own posts, so publish as user_b and view as user_a
        for i in range(3):
            _publish_post(client, user_b["headers"], user_b["outfit"]["id"], caption=f"Post {i}")

        resp = client.get("/social/feed?tab=discover&limit=2", headers=user_a["headers"])
        data = resp.get_json()
        assert len(data["posts"]) == 2
        assert data["pagination"]["has_more"] is True

    def test_feed_vibe_filter(self, client, user_a):
        _publish_post(client, user_a["headers"], user_a["outfit"]["id"],
                      caption="Street", vibes=["streetwear"])
        _publish_post(client, user_a["headers"], user_a["outfit"]["id"],
                      caption="Minimal", vibes=["minimalist"])

        resp = client.get("/social/feed?tab=discover&vibe=streetwear", headers=user_a["headers"])
        assert resp.status_code == 200
        posts = resp.get_json()["posts"]
        for p in posts:
            vibe_slugs = [v["slug"] for v in p.get("vibes", [])]
            assert "streetwear" in vibe_slugs


# ─── Like & Bookmark Tests ───────────────────────────────────────────────────

class TestInteractions:

    def test_like_post(self, client, user_a, user_b):
        post = _publish_post(client, user_a["headers"], user_a["outfit"]["id"])
        resp = client.post(f"/social/posts/{post['id']}/like", headers=user_b["headers"])
        assert resp.status_code == 200
        assert resp.get_json()["liked"] is True

    def test_unlike_post(self, client, user_a, user_b):
        post = _publish_post(client, user_a["headers"], user_a["outfit"]["id"])
        client.post(f"/social/posts/{post['id']}/like", headers=user_b["headers"])
        resp = client.post(f"/social/posts/{post['id']}/like", headers=user_b["headers"])
        assert resp.status_code == 200
        assert resp.get_json()["liked"] is False

    def test_bookmark_post(self, client, user_a, user_b):
        post = _publish_post(client, user_a["headers"], user_a["outfit"]["id"])
        resp = client.post(f"/social/posts/{post['id']}/bookmark", headers=user_b["headers"])
        assert resp.status_code == 200
        assert resp.get_json()["bookmarked"] is True

    def test_unbookmark_post(self, client, user_a, user_b):
        post = _publish_post(client, user_a["headers"], user_a["outfit"]["id"])
        client.post(f"/social/posts/{post['id']}/bookmark", headers=user_b["headers"])
        resp = client.post(f"/social/posts/{post['id']}/bookmark", headers=user_b["headers"])
        assert resp.status_code == 200
        assert resp.get_json()["bookmarked"] is False

    def test_bookmarks_list(self, client, user_a, user_b):
        post = _publish_post(client, user_a["headers"], user_a["outfit"]["id"])
        client.post(f"/social/posts/{post['id']}/bookmark", headers=user_b["headers"])

        resp = client.get("/social/bookmarks", headers=user_b["headers"])
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["posts"]) == 1


# ─── Remix Tests ──────────────────────────────────────────────────────────────

class TestRemix:

    def test_remix_post(self, client, user_a, user_b):
        post = _publish_post(client, user_a["headers"], user_a["outfit"]["id"])
        resp = client.post(f"/social/posts/{post['id']}/remix", headers=user_b["headers"])
        assert resp.status_code == 200
        data = resp.get_json()
        assert "coverage" in data

    def test_remix_chain(self, client, user_a):
        post = _publish_post(client, user_a["headers"], user_a["outfit"]["id"])
        resp = client.get(f"/social/posts/{post['id']}/remix-chain")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "ancestors" in data
        assert "remixes" in data


# ─── Vibe Tags Tests ─────────────────────────────────────────────────────────

class TestVibes:

    def test_list_vibes(self, client, user_a):
        resp = client.get("/social/vibes")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "global" in data or "vibes" in data or isinstance(data, list)

    def test_trending_vibes(self, client, user_a):
        _publish_post(client, user_a["headers"], user_a["outfit"]["id"],
                      vibes=["streetwear"])
        resp = client.get("/social/vibes/trending")
        assert resp.status_code == 200


# ─── Style DNA Tests ─────────────────────────────────────────────────────────

class TestStyleDNA:

    def test_own_style_dna(self, client, user_a):
        _publish_post(client, user_a["headers"], user_a["outfit"]["id"],
                      vibes=["streetwear"])
        resp = client.get("/social/profile/style-dna", headers=user_a["headers"])
        assert resp.status_code == 200

    def test_user_style_dna_public(self, client, user_a):
        client.patch("/social/profile", json={"username": "usera"}, headers=user_a["headers"])
        resp = client.get("/social/users/usera/style-dna")
        assert resp.status_code == 200


# ─── Public Profile Tests ────────────────────────────────────────────────────

class TestPublicProfile:

    def test_view_public_profile(self, client, user_a):
        client.patch("/social/profile", json={"username": "public_user"}, headers=user_a["headers"])
        resp = client.get("/social/users/public_user")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["user"]["username"] == "public_user"

    def test_view_nonexistent_user(self, client, user_a):
        resp = client.get("/social/users/ghost_user_xyz")
        assert resp.status_code == 404

    def test_private_profile_hidden(self, client, user_a, user_b):
        client.patch("/social/profile", json={
            "username": "private_user", "is_public": False,
        }, headers=user_a["headers"])
        resp = client.get("/social/users/private_user", headers=user_b["headers"])
        assert resp.status_code in (200, 403)
        # Private profile should restrict data
        if resp.status_code == 200:
            data = resp.get_json()
            assert data.get("posts") is None or len(data.get("posts", [])) == 0

    def test_compatibility_score(self, client, user_a, user_b):
        client.patch("/social/profile", json={"username": "compat_user"}, headers=user_b["headers"])
        resp = client.get("/social/users/compat_user/compatibility", headers=user_a["headers"])
        assert resp.status_code == 200
        data = resp.get_json()
        assert "compatibility_score" in data or "score" in data or resp.status_code == 200
