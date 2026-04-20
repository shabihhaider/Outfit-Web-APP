"""
tests/test_flask_stats_ootd.py
Tests for:
  GET /wardrobe/stats            — wardrobe statistics
  GET /recommendations/ootd      — outfit of the day
"""

from __future__ import annotations

import io
import json
from datetime import datetime, timezone

import numpy as np
import pytest
from unittest.mock import MagicMock

from engine.models import (
    WardrobeItem, Category, Formality, Gender,
    OutfitTemplate, OutfitCandidate,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _upload_item(client, auth_headers, minimal_png, formality="casual", gender="men", category="top"):
    """Upload a wardrobe item. Mock pipeline returns the given category."""
    from flask import current_app
    current_app.pipeline.classify_and_embed.return_value = (
        category,
        np.zeros(1280, dtype=np.float32),
        0.95,
    )
    data = {
        "image":     (io.BytesIO(minimal_png), "item.png", "image/png"),
        "formality": formality,
        "gender":    gender,
    }
    resp = client.post(
        "/wardrobe/items",
        data=data,
        headers=auth_headers,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return resp.get_json()


def _make_mock_outfit(item_ids, score=0.78, confidence="high"):
    """Create a mock OutfitCandidate-like object for pipeline.recommend return."""
    mock = MagicMock()
    mock.final_score = score
    mock.confidence = confidence
    mock.model2_score = 0.82
    mock.color_score = 0.71
    mock.weather_score = 0.85
    mock.cohesion_score = 0.76
    mock.synergy_score = 0.75  # Added required synergy_score field
    mock.template_id = OutfitTemplate.B

    items = []
    categories = [Category.TOP, Category.BOTTOM, Category.SHOES]
    for i, item_id in enumerate(item_ids):
        item_mock = MagicMock()
        item_mock.item_id = item_id
        item_mock.category = categories[i % len(categories)]
        items.append(item_mock)
    mock.items = items
    return mock


# ─── Wardrobe Stats ─────────────────────────────────────────────────────────

class TestWardrobeStats:
    def test_stats_empty_wardrobe(self, client, auth_headers):
        resp = client.get("/wardrobe/stats", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers.get("Cache-Control") == "private, max-age=60, stale-while-revalidate=300"
        assert "Authorization" in (resp.headers.get("Vary") or "")
        body = resp.get_json()

        assert body["wardrobe"]["total_items"] == 0
        assert body["wardrobe"]["capacity"] == 50
        assert body["wardrobe"]["categories"]["top"] == 0
        assert body["activity"]["total_recommendations"] == 0
        assert body["activity"]["avg_score"] is None
        assert body["insights"]["never_used_item_ids"] == []
        assert body["insights"]["most_common_occasion"] is None

    def test_stats_with_items(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            _upload_item(client, auth_headers, minimal_png, category="top")
            _upload_item(client, auth_headers, minimal_png, category="bottom")
            _upload_item(client, auth_headers, minimal_png, category="shoes")

        resp = client.get("/wardrobe/stats", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.get_json()

        assert body["wardrobe"]["total_items"] == 3
        assert body["wardrobe"]["categories"]["top"] == 1
        assert body["wardrobe"]["categories"]["bottom"] == 1
        assert body["wardrobe"]["categories"]["shoes"] == 1
        assert len(body["wardrobe"]["colors"]) == 3

    def test_stats_category_distribution(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            for cat in ["top", "top", "bottom", "shoes", "shoes", "shoes"]:
                _upload_item(client, auth_headers, minimal_png, category=cat)

        resp = client.get("/wardrobe/stats", headers=auth_headers)
        body = resp.get_json()

        assert body["wardrobe"]["categories"]["top"] == 2
        assert body["wardrobe"]["categories"]["bottom"] == 1
        assert body["wardrobe"]["categories"]["shoes"] == 3
        assert body["wardrobe"]["total_items"] == 6

    def test_stats_formality_distribution(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            _upload_item(client, auth_headers, minimal_png, formality="casual")
            _upload_item(client, auth_headers, minimal_png, formality="formal")
            _upload_item(client, auth_headers, minimal_png, formality="both")

        resp = client.get("/wardrobe/stats", headers=auth_headers)
        body = resp.get_json()

        assert body["wardrobe"]["formality"]["casual"] == 1
        assert body["wardrobe"]["formality"]["formal"] == 1
        assert body["wardrobe"]["formality"]["both"] == 1

    def test_stats_never_used_items(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            item1 = _upload_item(client, auth_headers, minimal_png, category="top")
            item2 = _upload_item(client, auth_headers, minimal_png, category="bottom")

        # No recommendations made → both items never used
        resp = client.get("/wardrobe/stats", headers=auth_headers)
        body = resp.get_json()

        assert item1["id"] in body["insights"]["never_used_item_ids"]
        assert item2["id"] in body["insights"]["never_used_item_ids"]

    def test_stats_activity_with_history(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            from app.models_db import OutfitHistory
            from app.extensions import db

            item = _upload_item(client, auth_headers, minimal_png)

            # Manually add history entries
            for score in [0.7, 0.8, 0.9]:
                entry = OutfitHistory(
                    user_id=1, occasion="casual", temperature_used=25.0,
                    item_ids=json.dumps([item["id"]]), final_score=score,
                    confidence="high", template="B",
                )
                db.session.add(entry)
            db.session.commit()

        resp = client.get("/wardrobe/stats", headers=auth_headers)
        body = resp.get_json()

        assert body["activity"]["total_recommendations"] == 3
        assert body["activity"]["avg_score"] == pytest.approx(0.8, abs=0.01)
        assert body["insights"]["most_common_occasion"] == "casual"
        # item was used in history → not in never_used
        assert item["id"] not in body["insights"]["never_used_item_ids"]

    def test_stats_feedback_counts(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            from app.models_db import OutfitHistory, OutfitFeedback
            from app.extensions import db

            item = _upload_item(client, auth_headers, minimal_png)

            h1 = OutfitHistory(
                user_id=1, occasion="casual", temperature_used=25.0,
                item_ids=json.dumps([item["id"]]), final_score=0.8,
                confidence="high", template="B",
            )
            h2 = OutfitHistory(
                user_id=1, occasion="formal", temperature_used=20.0,
                item_ids=json.dumps([item["id"]]), final_score=0.7,
                confidence="medium", template="A",
            )
            db.session.add_all([h1, h2])
            db.session.flush()

            db.session.add(OutfitFeedback(user_id=1, history_id=h1.id, rating=1))
            db.session.add(OutfitFeedback(user_id=1, history_id=h2.id, rating=-1))
            db.session.commit()

        resp = client.get("/wardrobe/stats", headers=auth_headers)
        body = resp.get_json()

        assert body["activity"]["feedback"]["thumbs_up"] == 1
        assert body["activity"]["feedback"]["thumbs_down"] == 1

    def test_stats_requires_auth(self, client):
        resp = client.get("/wardrobe/stats")
        assert resp.status_code == 401

    def test_stats_balance_tip(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            # 4 tops, 1 bottom → should suggest more bottoms
            for _ in range(4):
                _upload_item(client, auth_headers, minimal_png, category="top")
            _upload_item(client, auth_headers, minimal_png, category="bottom")
            _upload_item(client, auth_headers, minimal_png, category="shoes")

        resp = client.get("/wardrobe/stats", headers=auth_headers)
        body = resp.get_json()

        tip = body["insights"]["wardrobe_balance"]
        assert tip is not None
        assert "bottom" in tip.lower() or "top" in tip.lower()

    def test_stats_balance_tip_pluralizes_shoes(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            for _ in range(6):
                _upload_item(client, auth_headers, minimal_png, category="top")
            for _ in range(3):
                _upload_item(client, auth_headers, minimal_png, category="bottom")
            for _ in range(2):
                _upload_item(client, auth_headers, minimal_png, category="shoes")

        resp = client.get("/wardrobe/stats", headers=auth_headers)
        body = resp.get_json()
        tip = (body["insights"].get("wardrobe_balance") or "").lower()

        assert "shoes" in tip
        assert "shoess" not in tip

    def test_stats_balance_tip_pluralizes_dresses(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            for _ in range(9):
                _upload_item(client, auth_headers, minimal_png, category="dress")
            _upload_item(client, auth_headers, minimal_png, category="top")
            _upload_item(client, auth_headers, minimal_png, category="bottom")
            _upload_item(client, auth_headers, minimal_png, category="shoes")

        resp = client.get("/wardrobe/stats", headers=auth_headers)
        body = resp.get_json()
        tip = (body["insights"].get("wardrobe_balance") or "").lower()

        assert "dresses" in tip
        assert "dresss" not in tip


# ─── OOTD ────────────────────────────────────────────────────────────────────

class TestOOTD:
    def test_ootd_empty_wardrobe(self, client, auth_headers):
        resp = client.get("/recommendations/ootd", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers.get("Cache-Control") == "private, max-age=60, stale-while-revalidate=300"
        assert "Authorization" in (resp.headers.get("Vary") or "")
        body = resp.get_json()

        assert body["outfit"] is None
        assert "empty" in body["reason"].lower() or "upload" in body["reason"].lower()
        assert body["stats"]["items_available"] == 0

    def test_ootd_with_items(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            item1 = _upload_item(client, auth_headers, minimal_png, category="top")
            item2 = _upload_item(client, auth_headers, minimal_png, category="bottom")
            item3 = _upload_item(client, auth_headers, minimal_png, category="shoes")

            # Mock pipeline to return an outfit
            mock_outfit = _make_mock_outfit([item1["id"], item2["id"], item3["id"]])
            flask_app.pipeline.recommend.return_value = [mock_outfit]

        resp = client.get("/recommendations/ootd", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.get_json()

        assert body["outfit"] is not None
        assert body["outfit"]["final_score"] > 0
        assert body["outfit"]["confidence"] == "high"
        assert len(body["outfit"]["items"]) == 3
        assert body["outfit"]["occasion"] == "casual"  # default
        assert body["stats"]["items_available"] == 3

    def test_ootd_with_temp_param(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            _upload_item(client, auth_headers, minimal_png, category="top")
            flask_app.pipeline.recommend.return_value = []

        resp = client.get("/recommendations/ootd?temp_celsius=15", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        # Should not error — returns null outfit gracefully
        assert body["outfit"] is None

    def test_ootd_invalid_temp(self, client, auth_headers):
        resp = client.get("/recommendations/ootd?temp_celsius=abc", headers=auth_headers)
        assert resp.status_code == 422

    def test_ootd_requires_auth(self, client):
        resp = client.get("/recommendations/ootd")
        assert resp.status_code == 401

    def test_ootd_uses_most_common_occasion(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            from app.models_db import OutfitHistory
            from app.extensions import db

            item = _upload_item(client, auth_headers, minimal_png, category="top")

            # Create history: 3 formal, 1 casual → should pick formal
            for _ in range(3):
                db.session.add(OutfitHistory(
                    user_id=1, occasion="formal", temperature_used=22.0,
                    item_ids=json.dumps([item["id"]]), final_score=0.75,
                    confidence="high", template="B",
                ))
            db.session.add(OutfitHistory(
                user_id=1, occasion="casual", temperature_used=25.0,
                item_ids=json.dumps([item["id"]]), final_score=0.70,
                confidence="medium", template="A",
            ))
            db.session.commit()

            mock_outfit = _make_mock_outfit([item["id"]])
            flask_app.pipeline.recommend.return_value = [mock_outfit]

        resp = client.get("/recommendations/ootd", headers=auth_headers)
        body = resp.get_json()

        assert body["outfit"]["occasion"] == "formal"
        assert body["stats"]["preferred_occasion"] == "formal"

    def test_ootd_prefers_fresh_items(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            from app.models_db import OutfitHistory
            from app.extensions import db

            item1 = _upload_item(client, auth_headers, minimal_png, category="top")
            item2 = _upload_item(client, auth_headers, minimal_png, category="bottom")
            item3 = _upload_item(client, auth_headers, minimal_png, category="shoes")
            item4 = _upload_item(client, auth_headers, minimal_png, category="top")
            item5 = _upload_item(client, auth_headers, minimal_png, category="bottom")
            item6 = _upload_item(client, auth_headers, minimal_png, category="shoes")

            # Mark items 1,2,3 as recently worn
            db.session.add(OutfitHistory(
                user_id=1, occasion="casual", temperature_used=25.0,
                item_ids=json.dumps([item1["id"], item2["id"], item3["id"]]),
                final_score=0.80, confidence="high", template="B",
            ))
            db.session.commit()

            # Return two outfits: first uses worn items, second uses entirely fresh items
            worn_outfit = _make_mock_outfit([item1["id"], item2["id"], item3["id"]], score=0.85)
            fresh_outfit = _make_mock_outfit([item4["id"], item5["id"], item6["id"]], score=0.75)
            flask_app.pipeline.recommend.return_value = [worn_outfit, fresh_outfit]

        resp = client.get("/recommendations/ootd", headers=auth_headers)
        body = resp.get_json()

        # Should prefer the fresh outfit even though it has lower score
        assert body["outfit"] is not None
        assert body["outfit"]["is_fresh"] is True

    def test_ootd_insufficient_wardrobe(self, flask_app, client, auth_headers, minimal_png):
        from engine.models import InsufficientWardrobeError

        with flask_app.app_context():
            _upload_item(client, auth_headers, minimal_png, category="top")
            flask_app.pipeline.recommend.side_effect = InsufficientWardrobeError("Not enough")

        resp = client.get("/recommendations/ootd", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["outfit"] is None
        assert "not enough" in body["reason"].lower() or "upload" in body["reason"].lower()

    def test_ootd_color_data_in_outfit(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            item = _upload_item(client, auth_headers, minimal_png, category="top")
            mock_outfit = _make_mock_outfit([item["id"]])
            flask_app.pipeline.recommend.return_value = [mock_outfit]

        resp = client.get("/recommendations/ootd", headers=auth_headers)
        body = resp.get_json()

        assert "model2_score" in body["outfit"]
        assert "color_score" in body["outfit"]
        assert "weather_score" in body["outfit"]
        assert "synergy_score" in body["outfit"]  # Added synergy score validation


# ─── Color naming unit tests ──────────────────────────────────────────────────

class TestNearestColorName:
    """Unit tests for _nearest_color_name — no Flask context required."""

    def setup_method(self):
        from app.wardrobe.routes import _nearest_color_name
        self._fn = _nearest_color_name

    def _hsv(self, r, g, b):
        """Convert RGB (0-255) to HSV (hue 0-360, sat/val 0-1)."""
        import colorsys
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        return h * 360, s, v

    def test_beige(self):
        assert self._fn(*self._hsv(245, 245, 220)) == "Beige"

    def test_navy(self):
        assert self._fn(*self._hsv(0, 0, 128)) == "Navy"

    def test_black(self):
        assert self._fn(*self._hsv(0, 0, 0)) == "Black"

    def test_white(self):
        assert self._fn(*self._hsv(255, 255, 255)) == "White"

    def test_red(self):
        assert self._fn(*self._hsv(220, 20, 60)) == "Red"


class TestStatsColorNames:
    """Integration: /wardrobe/stats returns color objects with a `name` field."""

    def test_stats_colors_have_name(self, flask_app, client, auth_headers, minimal_png):
        with flask_app.app_context():
            _upload_item(client, auth_headers, minimal_png, category="top")

        resp = client.get("/wardrobe/stats", headers=auth_headers)
        assert resp.status_code == 200
        colors = resp.get_json()["wardrobe"]["colors"]
        assert len(colors) == 1
        assert "name" in colors[0]
        assert isinstance(colors[0]["name"], str)
        assert len(colors[0]["name"]) > 0
