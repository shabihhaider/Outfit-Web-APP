"""
tests/test_flask_score_outfit.py
Tests for POST /recommendations/score-outfit (Phase 7C).
Run: pytest tests/test_flask_score_outfit.py -v
"""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from tests.conftest import _make_minimal_png


def _mock_model2(fixed_score: float = 0.75) -> MagicMock:
    """Return a mock Keras model that always predicts fixed_score."""
    model = MagicMock()
    model.predict.return_value = np.array([[fixed_score]])
    return model


def _upload_item(client, headers, png, category="top", formality="casual"):
    """Upload a wardrobe item with a specific category mock and return JSON."""
    mock_pipeline = MagicMock()
    mock_pipeline.classify_and_embed.return_value = (
        category,
        np.random.default_rng(42).random(1280).astype(np.float32),
        0.95,
    )
    mock_pipeline.extract_color.return_value = (30.0, 0.8, 0.7)

    from flask import current_app
    old_pipeline = current_app.pipeline
    current_app.pipeline = mock_pipeline

    data = {
        "image": (io.BytesIO(png), "item.png", "image/png"),
        "formality": formality,
        "gender": "men",
    }
    resp = client.post(
        "/wardrobe/items", data=data, headers=headers,
        content_type="multipart/form-data",
    )
    current_app.pipeline = old_pipeline
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return resp.get_json()


@pytest.fixture
def setup_wardrobe(flask_app, client, auth_headers, minimal_png):
    """Upload top, bottom, shoes items and attach a mock model2."""
    with flask_app.app_context():
        top = _upload_item(client, auth_headers, minimal_png, "top", "casual")
        bottom = _upload_item(client, auth_headers, minimal_png, "bottom", "casual")
        shoes = _upload_item(client, auth_headers, minimal_png, "shoes", "casual")
        outwear = _upload_item(client, auth_headers, minimal_png, "outwear", "casual")
        dress = _upload_item(client, auth_headers, minimal_png, "dress", "formal")

        flask_app.pipeline.model2 = _mock_model2(0.75)
        return {
            "top": top, "bottom": bottom, "shoes": shoes,
            "outwear": outwear, "dress": dress,
        }


class TestScoreOutfitValid:
    """Tests for valid outfit scoring."""

    def test_score_valid_outfit(self, client, auth_headers, setup_wardrobe):
        """Score a valid top + bottom + shoes outfit."""
        ids = [
            setup_wardrobe["top"]["id"],
            setup_wardrobe["bottom"]["id"],
            setup_wardrobe["shoes"]["id"],
        ]
        resp = client.post(
            "/recommendations/score-outfit",
            json={"item_ids": ids, "occasion": "casual", "temp_celsius": 25},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["valid"] is True
        assert body["final_score"] is not None
        assert body["confidence"] in ["high", "medium", "low"]
        assert "breakdown" in body
        assert "model2_score" in body["breakdown"]
        assert "color_score" in body["breakdown"]
        assert "weather_score" in body["breakdown"]
        assert "weights" in body["breakdown"]
        assert body["rule_violations"] == []

    def test_score_with_temperature(self, client, auth_headers, setup_wardrobe):
        """Custom temperature affects weather score."""
        ids = [
            setup_wardrobe["top"]["id"],
            setup_wardrobe["bottom"]["id"],
            setup_wardrobe["shoes"]["id"],
        ]
        resp = client.post(
            "/recommendations/score-outfit",
            json={"item_ids": ids, "occasion": "casual", "temp_celsius": 5},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["valid"] is True
        # Should still have a score, weather might be low at 5°C for light outfit
        assert body["final_score"] is not None

    def test_suggestions_field_present(self, client, auth_headers, setup_wardrobe):
        """Suggestions field always present in response."""
        ids = [
            setup_wardrobe["top"]["id"],
            setup_wardrobe["bottom"]["id"],
            setup_wardrobe["shoes"]["id"],
        ]
        resp = client.post(
            "/recommendations/score-outfit",
            json={"item_ids": ids, "occasion": "casual"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert "suggestions" in body
        assert isinstance(body["suggestions"], list)


class TestScoreOutfitRuleViolations:
    """Tests for hard rule violations."""

    def test_dress_with_top_violation(self, client, auth_headers, setup_wardrobe):
        """Dress + top should fail hard rules."""
        ids = [
            setup_wardrobe["dress"]["id"],
            setup_wardrobe["top"]["id"],
        ]
        resp = client.post(
            "/recommendations/score-outfit",
            json={"item_ids": ids, "occasion": "casual"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["valid"] is False
        assert body["final_score"] is None
        assert len(body["rule_violations"]) > 0
        assert any("dress" in v.lower() for v in body["rule_violations"])

    def test_occasion_mismatch(self, client, auth_headers, setup_wardrobe):
        """Casual items with formal occasion should show mismatches."""
        ids = [
            setup_wardrobe["top"]["id"],
            setup_wardrobe["bottom"]["id"],
            setup_wardrobe["shoes"]["id"],
        ]
        resp = client.post(
            "/recommendations/score-outfit",
            json={"item_ids": ids, "occasion": "formal"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body["occasion_mismatches"]) > 0


class TestScoreOutfitValidation:
    """Tests for input validation."""

    def test_less_than_2_items(self, client, auth_headers):
        """Must have at least 2 item IDs."""
        resp = client.post(
            "/recommendations/score-outfit",
            json={"item_ids": [1], "occasion": "casual"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_empty_item_ids(self, client, auth_headers):
        """Empty item_ids should fail."""
        resp = client.post(
            "/recommendations/score-outfit",
            json={"item_ids": [], "occasion": "casual"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_no_item_ids(self, client, auth_headers):
        """Missing item_ids should fail."""
        resp = client.post(
            "/recommendations/score-outfit",
            json={"occasion": "casual"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_invalid_occasion(self, client, auth_headers, setup_wardrobe):
        """Invalid occasion should return 422."""
        ids = [setup_wardrobe["top"]["id"], setup_wardrobe["bottom"]["id"]]
        resp = client.post(
            "/recommendations/score-outfit",
            json={"item_ids": ids, "occasion": "party"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_invalid_temperature(self, client, auth_headers, setup_wardrobe):
        """Non-numeric temp should return 422."""
        ids = [setup_wardrobe["top"]["id"], setup_wardrobe["bottom"]["id"]]
        resp = client.post(
            "/recommendations/score-outfit",
            json={"item_ids": ids, "occasion": "casual", "temp_celsius": "hot"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_items_not_owned(self, client, auth_headers):
        """Items not belonging to user should return 403."""
        resp = client.post(
            "/recommendations/score-outfit",
            json={"item_ids": [9999, 9998], "occasion": "casual"},
            headers=auth_headers,
        )
        assert resp.status_code == 403

    def test_no_auth(self, client):
        """Request without JWT should return 401."""
        resp = client.post(
            "/recommendations/score-outfit",
            json={"item_ids": [1, 2], "occasion": "casual"},
        )
        assert resp.status_code == 401

    def test_default_occasion(self, client, auth_headers, setup_wardrobe):
        """Missing occasion defaults to casual."""
        ids = [
            setup_wardrobe["top"]["id"],
            setup_wardrobe["bottom"]["id"],
            setup_wardrobe["shoes"]["id"],
        ]
        resp = client.post(
            "/recommendations/score-outfit",
            json={"item_ids": ids},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["valid"] is True
