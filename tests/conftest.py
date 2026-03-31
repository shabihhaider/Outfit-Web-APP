"""
tests/conftest.py
Shared pytest fixtures for Phase 4 engine tests AND Phase 5 Flask tests.
"""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock

import numpy as np
import pytest

from engine.models import (
    WardrobeItem, Category, Formality, Gender,
    OutfitTemplate, TEMPLATE_CATEGORIES,
)


# ─── Engine helpers ────────────────────────────────────────────────────────────

def _make_embedding(seed: int = 0) -> list[float]:
    """Return a deterministic 1280-dim embedding for testing."""
    rng = np.random.default_rng(seed)
    return rng.random(1280).astype(np.float32).tolist()


def _make_item(
    item_id:      int,
    category:     Category,
    formality:    Formality = Formality.BOTH,
    gender:       Gender    = Gender.UNISEX,
    dominant_hue: float     = 0.0,
    dominant_sat: float     = 0.8,
    dominant_val: float     = 0.7,
    seed:         int       = 0,
) -> WardrobeItem:
    return WardrobeItem(
        item_id      = item_id,
        category     = category,
        formality    = formality,
        gender       = gender,
        embedding    = _make_embedding(seed),
        dominant_hue = dominant_hue,
        dominant_sat = dominant_sat,
        dominant_val = dominant_val,
    )


# ─── Phase 4 fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def top_item():
    return _make_item(1, Category.TOP, dominant_hue=30.0, seed=1)

@pytest.fixture
def bottom_item():
    return _make_item(2, Category.BOTTOM, dominant_hue=210.0, seed=2)  # ~complementary to 30°

@pytest.fixture
def shoes_item():
    return _make_item(3, Category.SHOES, dominant_hue=0.0, dominant_sat=0.05, seed=3)  # neutral

@pytest.fixture
def outwear_item():
    return _make_item(4, Category.OUTWEAR, dominant_hue=30.0, seed=4)

@pytest.fixture
def dress_item():
    return _make_item(5, Category.DRESS, dominant_hue=120.0, seed=5)

@pytest.fixture
def jumpsuit_item():
    return _make_item(6, Category.JUMPSUIT, dominant_hue=240.0, seed=6)


@pytest.fixture
def valid_outfit_abc(top_item, bottom_item, shoes_item):
    """Template A: top + bottom + shoes."""
    return [top_item, bottom_item, shoes_item]


@pytest.fixture
def small_wardrobe(top_item, bottom_item, shoes_item, outwear_item, dress_item):
    """5-item wardrobe covering multiple templates."""
    return [top_item, bottom_item, shoes_item, outwear_item, dress_item]


@pytest.fixture
def casual_item():
    return _make_item(10, Category.TOP, formality=Formality.CASUAL, seed=10)

@pytest.fixture
def formal_item():
    return _make_item(11, Category.TOP, formality=Formality.FORMAL, seed=11)


# ─── Phase 5 Flask fixtures ────────────────────────────────────────────────────

def _make_minimal_png() -> bytes:
    """Return a minimal valid 1×1 white PNG as bytes."""
    import struct, zlib

    def _pack_chunk(chunk_type: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        return length + chunk_type + data + crc

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr = _pack_chunk(b"IHDR", ihdr_data)
    raw_row = b"\x00\xff\xff\xff"  # filter byte 0 + white RGB pixel
    idat = _pack_chunk(b"IDAT", zlib.compress(raw_row))
    iend = _pack_chunk(b"IEND", b"")
    return signature + ihdr + idat + iend


@pytest.fixture
def flask_app():
    """Create a Flask test application with in-memory SQLite and mocked pipeline."""
    from app import create_app

    app = create_app("testing")

    # Attach a mock pipeline so routes don't need real TensorFlow models
    mock_pipeline = MagicMock()
    mock_pipeline.classify_and_embed.return_value = (
        "top",
        np.zeros(1280, dtype=np.float32),
        0.95,  # model_confidence
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
def client(flask_app):
    """Flask test client."""
    return flask_app.test_client()


@pytest.fixture
def auth_headers(client):
    """
    Register + login a test user; return Authorization headers.
    The registered user has gender='men'.
    """
    client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "password123",
            "gender": "men",
        },
    )
    resp = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def minimal_png() -> bytes:
    return _make_minimal_png()


@pytest.fixture
def upload_item(client, auth_headers, minimal_png):
    """
    Upload one wardrobe item and return the parsed JSON response dict.
    Category will be whatever the mock pipeline returns ("top").
    """
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
    assert resp.status_code == 201, resp.get_data(as_text=True)
    return resp.get_json()
