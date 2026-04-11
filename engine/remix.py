"""
engine/remix.py
Three-signal remix matching engine.

For each item in a source outfit, finds the top-K closest items in a target
user's wardrobe using:

  match_score = embedding_similarity × 0.40   (visual: shape, texture, pattern)
              + color_similarity      × 0.35   (HSV — what humans notice first)
              + formality_match       × 0.25   (casual stays casual, formal stays formal)

Hard constraint: same category only (top→top, shoes→shoes, etc.)
Returns top-2 candidates per slot so the user can choose.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

TOP_K = 2          # candidates returned per category slot
COVERAGE_THRESHOLD = 0.50   # minimum fraction of slots matched to allow remix


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class RemixCandidate:
    item_id:          int
    final_score:      float
    embedding_score:  float
    color_score:      float
    formality_score:  float
    category:         str
    image_url:        str | None = None


@dataclass
class RemixMatch:
    source_item_id:  int
    source_category: str
    candidates:      list[RemixCandidate]   # top-K, sorted by final_score desc


@dataclass
class RemixResult:
    matches:             list[RemixMatch]
    coverage:            float       # fraction of categories that have ≥1 candidate
    missing_categories:  list[str]
    can_remix:           bool        # True if coverage ≥ COVERAGE_THRESHOLD


# ── Internal helpers ──────────────────────────────────────────────────────────

def _cosine_batch(vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """vec (D,) vs matrix (N, D) → (N,).  Both are assumed L2-normalised."""
    return matrix @ vec


def _color_sim(
    hue_a: float, sat_a: float, val_a: float,
    hue_b: float, sat_b: float, val_b: float,
) -> float:
    """HSV colour similarity — hue is circular (0–360)."""
    hue_diff = min(abs(hue_a - hue_b), 360.0 - abs(hue_a - hue_b)) / 180.0
    sat_diff = abs(sat_a - sat_b)
    val_diff = abs(val_a - val_b)
    # Hue 60%, brightness 25%, saturation 15%
    distance = 0.60 * hue_diff + 0.25 * val_diff + 0.15 * sat_diff
    return float(max(0.0, 1.0 - distance))


def _formality_score(fa: str, fb: str) -> float:
    if fa == fb:
        return 1.0
    if "both" in (fa, fb):
        return 0.5
    return 0.0   # casual vs formal — incompatible


# ── Public API ────────────────────────────────────────────────────────────────

def remix_outfit(
    source_item_ids: list[int],
    user_b_wardrobe: list,   # list of WardrobeItemDB
) -> RemixResult:
    """
    Match each item in the source outfit against user B's wardrobe.

    Parameters
    ----------
    source_item_ids:
        IDs of the items in the outfit being remixed.
    user_b_wardrobe:
        All WardrobeItemDB objects belonging to the remixing user.

    Returns
    -------
    RemixResult with per-category matches and coverage metrics.
    """
    from app.models_db import WardrobeItemDB

    # Resolve source items (ignore deleted ones)
    source_items = [
        WardrobeItemDB.query.get(iid)
        for iid in source_item_ids
    ]
    source_items = [i for i in source_items if i is not None]

    if not source_items:
        return RemixResult(matches=[], coverage=0.0, missing_categories=[], can_remix=False)

    # ── Pre-index user B's wardrobe by category ────────────────────────────────
    cat_items:  dict[str, list] = {}
    cat_matrix: dict[str, np.ndarray] = {}

    for item in user_b_wardrobe:
        if item.embedding is None:
            continue
        try:
            emb = np.array(json.loads(item.embedding), dtype=np.float32)
        except (json.JSONDecodeError, ValueError):
            continue
        norm = np.linalg.norm(emb)
        if norm < 1e-9:
            continue
        emb = emb / norm

        cat = item.category
        if cat not in cat_items:
            cat_items[cat] = []
            cat_matrix[cat] = []
        cat_items[cat].append(item)
        cat_matrix[cat].append(emb)

    for cat in cat_matrix:
        cat_matrix[cat] = np.stack(cat_matrix[cat])  # (N, 1280)

    # ── Score each source item ─────────────────────────────────────────────────
    matches: list[RemixMatch] = []

    for src in source_items:
        cat = src.category

        if cat not in cat_items or src.embedding is None:
            matches.append(RemixMatch(
                source_item_id=src.id,
                source_category=cat,
                candidates=[],
            ))
            continue

        try:
            src_emb = np.array(json.loads(src.embedding), dtype=np.float32)
        except (json.JSONDecodeError, ValueError):
            matches.append(RemixMatch(source_item_id=src.id, source_category=cat, candidates=[]))
            continue

        src_norm = np.linalg.norm(src_emb)
        if src_norm < 1e-9:
            matches.append(RemixMatch(source_item_id=src.id, source_category=cat, candidates=[]))
            continue

        src_emb = src_emb / src_norm
        emb_scores = _cosine_batch(src_emb, cat_matrix[cat])   # (N,)

        scored: list[RemixCandidate] = []
        for i, cand in enumerate(cat_items[cat]):
            c_score    = float(emb_scores[i])
            col_score  = _color_sim(
                src.color_hue or 0.0, src.color_sat or 0.0, src.color_val or 0.0,
                cand.color_hue or 0.0, cand.color_sat or 0.0, cand.color_val or 0.0,
            )
            form_score = _formality_score(src.formality, cand.formality)
            final      = c_score * 0.40 + col_score * 0.35 + form_score * 0.25

            scored.append(RemixCandidate(
                item_id=cand.id,
                final_score=round(final, 3),
                embedding_score=round(c_score, 3),
                color_score=round(col_score, 3),
                formality_score=round(form_score, 3),
                category=cat,
                image_url=f"/uploads/{cand.image_filename}",
            ))

        scored.sort(key=lambda x: x.final_score, reverse=True)

        if scored:
            logger.debug(
                "Remix %s id=%d → best id=%d score=%.3f (emb=%.2f col=%.2f form=%.2f)",
                cat, src.id,
                scored[0].item_id, scored[0].final_score,
                scored[0].embedding_score, scored[0].color_score, scored[0].formality_score,
            )

        matches.append(RemixMatch(
            source_item_id=src.id,
            source_category=cat,
            candidates=scored[:TOP_K],
        ))

    # ── Coverage ───────────────────────────────────────────────────────────────
    matched  = sum(1 for m in matches if m.candidates)
    total    = len(matches)
    coverage = round(matched / total, 2) if total else 0.0
    missing  = [m.source_category for m in matches if not m.candidates]

    return RemixResult(
        matches=matches,
        coverage=coverage,
        missing_categories=missing,
        can_remix=coverage >= COVERAGE_THRESHOLD,
    )
