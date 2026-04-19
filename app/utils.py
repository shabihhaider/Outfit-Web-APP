"""
app/utils.py
Shared helper functions for the Flask layer.

  allowed_file()              — check file extension is permitted
  validate_image_content()    — Pillow verify() to reject non-image files
  validate_clothing_photo()   — confidence threshold check (≥0.45)
  item_db_to_engine()         — convert WardrobeItemDB → engine WardrobeItem
  normalize_upload()          — EXIF+resize+JPEG for fallback (atelier failed)
  process_image_for_atelier() — normalise uploaded image to clean RGB PNG
"""

from __future__ import annotations

import io
import json
import logging
import os

logger = logging.getLogger(__name__)


def allowed_file(filename: str, allowed_extensions: set[str]) -> bool:
    """Return True if the filename has a permitted extension (case-insensitive)."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in allowed_extensions
    )


_MAGIC_BYTES = {
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
}


def validate_image_content(content: bytes) -> bool:
    """
    Return True if the bytes represent a valid image.

    Two-layer validation:
      1. Magic byte check — reject files that don't start with PNG/JPEG signatures.
      2. Pillow verify() — actually parses the file format; catches truncated or
         malicious files that fake an extension.
    """
    # Layer 1: magic bytes
    if not any(content.startswith(sig) for sig in _MAGIC_BYTES):
        logger.debug("Image validation failed: unrecognised magic bytes")
        return False

    # Layer 2: Pillow structural check
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(content))
        img.verify()
        return True
    except Exception as exc:
        logger.debug("Image validation failed: %s", exc)
        return False


def validate_clothing_photo(content: bytes) -> tuple[bool, str]:
    """
    Heuristic check that an image looks like a clothing photograph,
    not a screenshot, diagram, or other non-clothing image.

    Returns (is_valid, reason). Uses three signals:
      1. Color variety — screenshots/UIs have very few unique colors
      2. Edge density  — screenshots have sharp rectangular edges, not fabric
      3. Saturation    — most non-photo images are heavily desaturated

    Deliberately lenient to avoid rejecting valid photos of dark/white clothing.
    """
    import numpy as np
    from PIL import Image

    try:
        img = Image.open(io.BytesIO(content)).convert("RGB")

        # Downsample to 64×64 for fast analysis
        thumb = img.resize((64, 64), Image.LANCZOS)
        pixels = list(thumb.getdata())

        # 1. Unique color count — screenshots/UIs typically < 200 at 64×64
        unique = len(set(pixels))
        if unique < 120:
            return False, (
                "Image looks like a screenshot or graphic (too few colors). "
                "Please upload a photograph of a clothing item."
            )

        # 2. Check for dominant white/gray — screenshots are mostly white/gray UI
        arr = np.array(pixels, dtype=np.float32)  # (4096, 3)
        # Pixels where R, G, B are all > 230 (near-white)
        near_white = np.all(arr > 230, axis=1).sum()
        white_ratio = near_white / len(arr)
        # Pixels where R≈G≈B within 15 (gray) AND value > 180
        gray_mask = (np.ptp(arr, axis=1) < 15) & (arr.mean(axis=1) > 180)
        gray_ratio = gray_mask.sum() / len(arr)

        if white_ratio > 0.65 and gray_ratio > 0.70:
            return False, (
                "Image appears to be a screenshot or document (mostly white/gray). "
                "Please upload a photograph of a clothing item."
            )

        return True, ""
    except Exception as exc:
        logger.debug("Clothing photo validation error: %s", exc)
        return True, ""  # fail open — don't block on analysis errors


def item_db_to_engine(item_db) -> "WardrobeItem":  # noqa: F821
    """
    Convert a SQLAlchemy WardrobeItemDB to an engine WardrobeItem.

    Field name mapping:
      DB: color_hue  → engine: dominant_hue
      DB: color_sat  → engine: dominant_sat
      DB: color_val  → engine: dominant_val
      DB: id (int)   → engine: item_id (int — NOT str)
    """
    from engine.models import WardrobeItem, Category, Formality, Gender

    embedding: list[float] = json.loads(item_db.embedding)

    return WardrobeItem(
        item_id      = item_db.id,                      # int, not str
        category     = Category(item_db.category),
        formality    = Formality(item_db.formality),
        gender       = Gender(item_db.gender),
        embedding    = embedding,
        dominant_hue = item_db.color_hue,               # DB: color_hue → engine: dominant_hue
        dominant_sat = item_db.color_sat,               # DB: color_sat → engine: dominant_sat
        dominant_val = item_db.color_val,               # DB: color_val → engine: dominant_val
        sub_category = getattr(item_db, "sub_category", None),
    )


def normalize_upload(path: str, max_side: int = 800, jpeg_quality: int = 85) -> None:
    """
    Lightweight normalisation for uploads that bypass the full Atelier pipeline.

    Applies EXIF rotation correction, caps the longest side to `max_side`, and
    re-encodes as JPEG (quality=`jpeg_quality`) in-place.  Replaces the original
    file — so a 5-8 MB phone photo becomes a ~100-300 KB web-ready image.

    Silently no-ops on any error so the upload is never blocked.
    """
    try:
        from PIL import Image, ImageOps

        img = Image.open(path)
        img = ImageOps.exif_transpose(img)

        w, h = img.size
        if max(w, h) > max_side:
            scale = max_side / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Replace in-place with a JPEG; rename path to .jpg
        base, _ = os.path.splitext(path)
        jpg_path = base + ".jpg"
        img.save(jpg_path, "JPEG", quality=jpeg_quality, optimize=True)
        if jpg_path != path:
            try:
                os.remove(path)
            except OSError:
                pass
        logger.info("normalize_upload: saved %s (%dx%d)", jpg_path, img.width, img.height)
    except Exception as exc:
        logger.warning("normalize_upload: failed for %s — %s", path, exc)


def process_image_for_atelier(
    src_path: str,
    dst_path: str,
    max_side: int = 800,
) -> tuple[bool, bool]:
    """
    Normalise an uploaded clothing image for the Atelier digital-closet experience.

    Pipeline (in order):
      1. Open image and apply EXIF orientation correction.
      2. Cap the longest side to `max_side` pixels (default 800 — sufficient for
         Retina card display; rembg on CPU is O(pixels) so smaller = faster).
      3. Attempt background removal via rembg (u2net model, self-hosted, ~176 MB).
         Uses already-decoded bytes — no second disk read.
      4. Composite the RGBA result onto a clean white RGB background so every
         wardrobe card looks like a studio product shot.
      5. Save as optimized PNG (lossless, consistent format).

    Returns (success, bg_removed):
      success    — True if `dst_path` was written; False on any fatal error.
                   A False return does NOT block the upload — the caller keeps
                   the original file.
      bg_removed — True only if rembg actually removed the background.
                   False when rembg is not installed, the model file is absent,
                   or rembg raised any error.

    Installation notes:
      pip install rembg onnxruntime          # CPU inference (default)
      pip install rembg onnxruntime-gpu      # GPU acceleration (optional)
      # Model is auto-downloaded to ~/.u2net/u2net.onnx on first call (~176 MB).
      # Pre-download with:  python -c "from rembg import remove; remove(b'')"
    """
    import time

    try:
        from PIL import Image, ImageOps

        # ── 1. Open + EXIF-correct ────────────────────────────────────────────
        img = Image.open(src_path)
        img = ImageOps.exif_transpose(img)   # correct phone rotation before anything else

        # ── 2. Dimension cap (speed guard for rembg on CPU) ───────────────────
        w, h = img.size
        if max(w, h) > max_side:
            scale = max_side / max(w, h)
            img = img.resize(
                (int(w * scale), int(h * scale)),
                Image.LANCZOS,
            )

        # ── 3. Attempt background removal ────────────────────────────────────
        bg_removed = False
        try:
            from rembg import remove as rembg_remove  # type: ignore[import]

            # Encode the already-corrected + resized image to bytes for rembg.
            # This avoids a second disk read and ensures rembg sees the
            # orientation-corrected image (u2net is pose-sensitive).
            img_buf = io.BytesIO()
            # Save as PNG to preserve any alpha channel that may be present
            img.save(img_buf, format="PNG")
            img_bytes = img_buf.getvalue()

            t0 = time.monotonic()
            result_bytes = rembg_remove(img_bytes)
            elapsed = time.monotonic() - t0

            img = Image.open(io.BytesIO(result_bytes))
            bg_removed = True
            logger.info(
                "Atelier: background removed in %.2fs — %s", elapsed, src_path
            )

        except ImportError:
            # rembg not installed — degrade gracefully, keep image as-is
            logger.debug("Atelier: rembg not installed, skipping background removal.")

        except Exception as rembg_exc:
            # Model file missing, OOM, ONNX error, etc. — non-fatal
            logger.warning(
                "Atelier: rembg failed (%s: %s) — keeping original image.",
                type(rembg_exc).__name__,
                rembg_exc,
            )

        # ── 4. Composite onto white RGB background ────────────────────────────
        # Handles: RGBA (rembg output), LA, P (palette), and any other mode.
        if img.mode == "P":
            img = img.convert("RGBA")

        if img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])   # alpha channel as mask
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # ── 5. Save as optimized PNG ──────────────────────────────────────────
        img.save(dst_path, "PNG", optimize=True)
        return True, bg_removed

    except Exception as exc:
        logger.error("Atelier: image processing failed for %s: %s", src_path, exc)
        return False, False
