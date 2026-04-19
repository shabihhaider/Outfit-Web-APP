"""
tests/test_image_processing.py
Tests for app.utils image helpers:
  normalize_upload()          — EXIF+resize+JPEG fallback normalisation
  process_image_for_atelier() — max_side default reduced to 800
"""

from __future__ import annotations

import os
import struct
import tempfile
import zlib

import pytest
from PIL import Image


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_png(width: int, height: int) -> bytes:
    """Return a minimal valid PNG of the given dimensions (white RGB)."""
    img = Image.new("RGB", (width, height), (255, 255, 255))
    buf = __import__("io").BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _make_jpeg(width: int, height: int) -> bytes:
    img = Image.new("RGB", (width, height), (200, 150, 100))
    buf = __import__("io").BytesIO()
    img.save(buf, "JPEG", quality=80)
    return buf.getvalue()


def _write_tmp(data: bytes, suffix: str) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    with open(path, "wb") as f:
        f.write(data)
    return path


# ─── normalize_upload ─────────────────────────────────────────────────────────

class TestNormalizeUpload:
    """normalize_upload() must EXIF-correct, resize, and convert to JPEG in-place."""

    def test_large_png_is_shrunk_to_800(self, tmp_path):
        """A 1600×1200 PNG must be shrunk so longest side ≤ 800."""
        from app.utils import normalize_upload

        path = str(tmp_path / "large.png")
        Image.new("RGB", (1600, 1200), (100, 100, 100)).save(path, "PNG")

        normalize_upload(path, max_side=800)

        # Original path is gone; a .jpg should exist
        jpg_path = str(tmp_path / "large.jpg")
        assert os.path.exists(jpg_path), "Expected .jpg output"
        img = Image.open(jpg_path)
        assert max(img.size) <= 800

    def test_small_image_unchanged_dimensions(self, tmp_path):
        """An image already within 800px must not be upscaled."""
        from app.utils import normalize_upload

        path = str(tmp_path / "small.png")
        Image.new("RGB", (400, 300), (50, 50, 50)).save(path, "PNG")

        normalize_upload(path, max_side=800)

        jpg_path = str(tmp_path / "small.jpg")
        img = Image.open(jpg_path)
        assert img.size == (400, 300)

    def test_aspect_ratio_preserved(self, tmp_path):
        """Resize must preserve aspect ratio (no stretching)."""
        from app.utils import normalize_upload

        path = str(tmp_path / "wide.png")
        Image.new("RGB", (2000, 500), (80, 80, 80)).save(path, "PNG")

        normalize_upload(path, max_side=800)

        jpg_path = str(tmp_path / "wide.jpg")
        img = Image.open(jpg_path)
        w, h = img.size
        # Original ratio: 4:1 → after cap: 800×200
        assert w == 800
        assert h == 200

    def test_rgba_converted_to_rgb(self, tmp_path):
        """RGBA images must be converted to RGB (JPEG cannot encode alpha)."""
        from app.utils import normalize_upload

        path = str(tmp_path / "rgba.png")
        Image.new("RGBA", (100, 100), (255, 0, 0, 128)).save(path, "PNG")

        normalize_upload(path, max_side=800)

        jpg_path = str(tmp_path / "rgba.jpg")
        img = Image.open(jpg_path)
        assert img.mode == "RGB"

    def test_corrupt_file_does_not_raise(self, tmp_path):
        """normalize_upload must silently no-op on corrupt input."""
        from app.utils import normalize_upload

        path = str(tmp_path / "bad.png")
        with open(path, "wb") as f:
            f.write(b"not an image at all")

        # Must not raise
        normalize_upload(path, max_side=800)


# ─── process_image_for_atelier max_side default ───────────────────────────────

class TestProcessImageAtelierMaxSide:
    """process_image_for_atelier() default max_side must be 800 (not 1500)."""

    def test_default_max_side_is_800(self, tmp_path):
        """A 1600px image processed with defaults must produce ≤ 800px output."""
        from app.utils import process_image_for_atelier

        src = str(tmp_path / "big.png")
        dst = str(tmp_path / "big_atelier.png")
        Image.new("RGB", (1600, 1200), (200, 200, 200)).save(src, "PNG")

        ok, _ = process_image_for_atelier(src, dst)

        assert ok is True
        img = Image.open(dst)
        assert max(img.size) <= 800, f"Expected ≤800 but got {img.size}"

    def test_explicit_max_side_override(self, tmp_path):
        """max_side parameter must be respected when passed explicitly."""
        from app.utils import process_image_for_atelier

        src = str(tmp_path / "big2.png")
        dst = str(tmp_path / "big2_atelier.png")
        Image.new("RGB", (600, 400), (100, 100, 100)).save(src, "PNG")

        ok, _ = process_image_for_atelier(src, dst, max_side=300)

        assert ok is True
        img = Image.open(dst)
        assert max(img.size) <= 300
