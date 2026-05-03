"""
tests/test_flask_recommendations.py
Tests for POST /recommendations.

The ML pipeline and weather API are fully mocked — no TensorFlow or network.
"""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from engine.models import (
    OutfitCandidate, OutfitTemplate, WardrobeItem,
    Category, Formality, Gender,
    InsufficientWardrobeError, WeatherAPIError, WeatherLocationError,
)


def _make_embedding(seed: int = 0) -> list[float]:
    rng = np.random.default_rng(seed)
    return rng.random(1280).astype(np.float32).tolist()


def _make_outfit_candidate(
    items: list[WardrobeItem],
    template_id: OutfitTemplate = OutfitTemplate.A,
    final_score: float = 0.82,
) -> OutfitCandidate:
    return OutfitCandidate(
        items          = items,
        template_id    = template_id,
        final_score    = final_score,
        model2_score   = 0.78,
        color_score    = 0.90,
        weather_score  = 0.85,
        cohesion_score = 0.80,
        synergy_score  = 0.50,
        confidence     = "high",
    )


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


# ─── Helper: upload N items to the test wardrobe ──────────────────────────────

def _upload_items(client, auth_headers, flask_app, n: int, minimal_png: bytes):
    categories = ["top", "bottom", "shoes", "outwear", "dress", "jumpsuit"]
    ids = []
    for i in range(n):
        cat = categories[i % len(categories)]
        flask_app.pipeline.classify_and_embed.return_value = (
            cat, np.zeros(1280, dtype=np.float32), 0.95
        )
        resp = client.post(
            "/wardrobe/items",
            data={
                "image":    (io.BytesIO(minimal_png), f"item{i}.png", "image/png"),
                "formality": "both",
                "gender":    "unisex",
            },
            headers=auth_headers,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201, resp.get_data(as_text=True)
        ids.append(resp.get_json()["id"])
    return ids


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestRecommendations:
    def test_path_b_manual_temperature(self, client, flask_app, auth_headers, minimal_png):
        """Path B: caller provides temp_celsius directly."""
        ids = _upload_items(client, auth_headers, flask_app, 3, minimal_png)

        # Build mock outfit using the uploaded item IDs
        eng_items = [
            _make_wardrobe_item(ids[0], Category.TOP),
            _make_wardrobe_item(ids[1], Category.BOTTOM),
            _make_wardrobe_item(ids[2], Category.SHOES),
        ]
        flask_app.pipeline.recommend.return_value = [
            _make_outfit_candidate(eng_items)
        ]

        resp = client.post(
            "/recommendations",
            json={"occasion": "casual", "temp_celsius": 28.0},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.headers.get("Cache-Control") == "private, max-age=60, stale-while-revalidate=300"
        assert "Authorization" in (resp.headers.get("Vary") or "")
        body = resp.get_json()
        assert body["occasion"] == "casual"
        assert body["temperature_used"] == 28.0
        assert len(body["outfits"]) == 1
        outfit = body["outfits"][0]
        assert outfit["rank"] == 1
        assert outfit["confidence"] == "high"
        assert len(outfit["items"]) == 3

    def test_path_a_auto_weather(self, client, flask_app, auth_headers, minimal_png):
        """Path A: lat/lon provided → pipeline.get_temperature called."""
        _upload_items(client, auth_headers, flask_app, 3, minimal_png)
        flask_app.pipeline.get_temperature.return_value = 31.5
        flask_app.pipeline.recommend.return_value = []

        resp = client.post(
            "/recommendations",
            json={"occasion": "casual", "lat": 31.52, "lon": 74.36},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["temperature_used"] == 31.5
        flask_app.pipeline.get_temperature.assert_called_once_with(31.52, 74.36)

    def test_neither_temp_nor_latlon_returns_400(self, client, auth_headers):
        resp = client.post(
            "/recommendations",
            json={"occasion": "casual"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_invalid_occasion_returns_422(self, client, auth_headers):
        resp = client.post(
            "/recommendations",
            json={"occasion": "birthday", "temp_celsius": 25.0},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_insufficient_wardrobe_returns_422(self, client, flask_app, auth_headers):
        """InsufficientWardrobeError → 422."""
        flask_app.pipeline.recommend.side_effect = InsufficientWardrobeError("not enough")

        resp = client.post(
            "/recommendations",
            json={"occasion": "formal", "temp_celsius": 25.0},
            headers=auth_headers,
        )
        assert resp.status_code == 422
        error_msg = resp.get_json()["error"].lower()
        assert "outfit" in error_msg or "missing" in error_msg

    def test_weather_api_error_returns_503(self, client, flask_app, auth_headers):
        """WeatherAPIError → 503."""
        flask_app.pipeline.get_temperature.side_effect = WeatherAPIError("down")

        resp = client.post(
            "/recommendations",
            json={"occasion": "casual", "lat": 31.52, "lon": 74.36},
            headers=auth_headers,
        )
        assert resp.status_code == 503

    def test_weather_location_error_returns_400(self, client, flask_app, auth_headers):
        """WeatherLocationError → 400."""
        flask_app.pipeline.get_temperature.side_effect = WeatherLocationError("no coords")

        resp = client.post(
            "/recommendations",
            json={"occasion": "casual", "lat": 31.52, "lon": 74.36},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_requires_auth(self, client):
        resp = client.post(
            "/recommendations",
            json={"occasion": "casual", "temp_celsius": 25.0},
        )
        assert resp.status_code == 401

    def test_empty_wardrobe_returns_empty_outfits(self, client, flask_app, auth_headers):
        """No wardrobe items → pipeline returns [] → response has outfits=[]."""
        flask_app.pipeline.recommend.return_value = []

        resp = client.post(
            "/recommendations",
            json={"occasion": "casual", "temp_celsius": 25.0},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["outfits"] == []

    def test_has_low_confidence_flag(self, client, flask_app, auth_headers, minimal_png):
        """When any outfit has confidence 'low', has_low_confidence must be True."""
        ids = _upload_items(client, auth_headers, flask_app, 3, minimal_png)
        eng_items = [
            _make_wardrobe_item(ids[0], Category.TOP),
            _make_wardrobe_item(ids[1], Category.BOTTOM),
            _make_wardrobe_item(ids[2], Category.SHOES),
        ]
        low_conf_outfit = OutfitCandidate(
            items          = eng_items,
            template_id    = OutfitTemplate.A,
            final_score    = 0.35,
            model2_score   = 0.30,
            color_score    = 0.40,
            weather_score  = 0.35,
            cohesion_score = 0.40,
            synergy_score  = 0.30,
            confidence     = "low",
        )
        flask_app.pipeline.recommend.return_value = [low_conf_outfit]

        resp = client.post(
            "/recommendations",
            json={"occasion": "casual", "temp_celsius": 25.0},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["has_low_confidence"] is True
        assert body["warning"] is not None

    def test_response_includes_template(self, client, flask_app, auth_headers, minimal_png):
        ids = _upload_items(client, auth_headers, flask_app, 3, minimal_png)
        eng_items = [
            _make_wardrobe_item(ids[0], Category.TOP),
            _make_wardrobe_item(ids[1], Category.BOTTOM),
            _make_wardrobe_item(ids[2], Category.SHOES),
        ]
        flask_app.pipeline.recommend.return_value = [
            _make_outfit_candidate(eng_items, template_id=OutfitTemplate.A)
        ]

        resp = client.post(
            "/recommendations",
            json={"occasion": "casual", "temp_celsius": 25.0},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["outfits"][0]["template"] == "A"

    def test_top_n_propagated_to_pipeline(self, client, flask_app, auth_headers):
        """top_n from request body must be forwarded to pipeline.recommend()."""
        flask_app.pipeline.recommend.reset_mock()
        flask_app.pipeline.recommend.return_value = []

        # 11°C → bucket 10 (unique across all tests)
        client.post(
            "/recommendations",
            json={"occasion": "casual", "temp_celsius": 11.0, "top_n": 9},
            headers=auth_headers,
        )

        assert flask_app.pipeline.recommend.call_args is not None, \
            "pipeline.recommend was not called — likely a cache hit from a prior test"
        call_kwargs = flask_app.pipeline.recommend.call_args.kwargs
        assert call_kwargs.get("top_n") == 9

    def test_top_n_capped_at_12(self, client, flask_app, auth_headers):
        """top_n values above 12 must be clamped to 12."""
        flask_app.pipeline.recommend.reset_mock()
        flask_app.pipeline.recommend.return_value = []

        # 42°C → bucket 40 (unique across all tests)
        client.post(
            "/recommendations",
            json={"occasion": "casual", "temp_celsius": 42.0, "top_n": 999},
            headers=auth_headers,
        )

        assert flask_app.pipeline.recommend.call_args is not None, \
            "pipeline.recommend was not called — likely a cache hit from a prior test"
        call_kwargs = flask_app.pipeline.recommend.call_args.kwargs
        assert call_kwargs.get("top_n") == 12

    def test_top_n_defaults_to_6(self, client, flask_app, auth_headers):
        """Omitting top_n in the request body must default to 6."""
        flask_app.pipeline.recommend.reset_mock()
        flask_app.pipeline.recommend.return_value = []

        # 53°C → bucket 55 (unique across all tests)
        client.post(
            "/recommendations",
            json={"occasion": "casual", "temp_celsius": 53.0},
            headers=auth_headers,
        )

        assert flask_app.pipeline.recommend.call_args is not None, \
            "pipeline.recommend was not called — likely a cache hit from a prior test"
        call_kwargs = flask_app.pipeline.recommend.call_args.kwargs
        assert call_kwargs.get("top_n") == 6
