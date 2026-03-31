"""
engine/preview_generator.py
Server-side Pillow mosaic generator for outfit posts.

Generates an 800×800 JPEG composite of 2–6 cleaned wardrobe item images.
Called once at publish time; result is stored in uploads/ and served statically.

Grid layouts:
  2 items → 1×2
  3 items → 1×3
  4 items → 2×2
  5 items → 3 top + 2 bottom (centered)
  6 items → 2×3
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

CANVAS_SIZE = (800, 800)
BG_COLOR    = (245, 244, 240)   # warm off-white — matches Atelier palette
CARD_COLOR  = (255, 255, 255)
PADDING     = 14


def generate_outfit_preview(
    item_image_paths: list[str],
    output_path: str,
    canvas_size: tuple[int, int] = CANVAS_SIZE,
    background_color: tuple = BG_COLOR,
    card_color: tuple = CARD_COLOR,
    padding: int = PADDING,
) -> bool:
    """
    Compose a mosaic preview image from 2–6 cleaned wardrobe item images.

    Parameters
    ----------
    item_image_paths : list of absolute file paths
        Only paths that exist on disk are used.
    output_path : str
        Absolute path for the output JPEG.

    Returns
    -------
    True on success, False on any error (non-fatal — post still publishes).
    """
    try:
        from PIL import Image

        paths = [p for p in item_image_paths if os.path.isfile(p)]
        if len(paths) < 2:
            logger.warning("Preview generator: fewer than 2 valid image paths, skipping.")
            return False

        # Use at most 6 items
        paths = paths[:6]
        n = len(paths)

        # Grid dimensions
        cols = 2 if n == 4 else min(n, 3)
        rows = (n + cols - 1) // cols

        canvas_w, canvas_h = canvas_size
        cell_w = (canvas_w - padding * (cols + 1)) // cols
        cell_h = (canvas_h - padding * (rows + 1)) // rows

        canvas = Image.new("RGB", canvas_size, background_color)

        for idx, path in enumerate(paths):
            row = idx // cols
            col = idx % cols

            # Centre items in a non-full last row
            row_item_count = min(cols, n - row * cols)
            if row_item_count < cols:
                row_start_x = (canvas_w - row_item_count * (cell_w + padding) + padding) // 2
            else:
                row_start_x = padding

            x = row_start_x + col * (cell_w + padding)
            y = padding + row * (cell_h + padding)

            # White card per item
            canvas.paste(Image.new("RGB", (cell_w, cell_h), card_color), (x, y))

            # Load item image — already clean white-background PNG from Atelier pipeline
            try:
                item_img = Image.open(path).convert("RGB")
            except Exception as exc:
                logger.warning("Preview generator: cannot open %s (%s), skipping cell.", path, exc)
                continue

            item_img.thumbnail((cell_w - 10, cell_h - 10), Image.LANCZOS)

            # Centre within cell
            paste_x = x + (cell_w - item_img.width) // 2
            paste_y = y + (cell_h - item_img.height) // 2
            canvas.paste(item_img, (paste_x, paste_y))

        canvas.save(output_path, "JPEG", quality=85, optimize=True)
        logger.debug("Preview saved → %s", output_path)
        return True

    except Exception as exc:
        logger.error("Preview generation failed: %s", exc, exc_info=True)
        return False
