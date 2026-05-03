"""
engine/outfit_generator.py
Orchestrator that generates and scores outfit candidates from a user's wardrobe.

Pipeline:
  1. Gender filter
  2. Gate 2 — occasion filter (item-level)
  3. Wardrobe minimum check
  4. Group items by category
  5. Enumerate combinations per template
  6. Gate 1 — hard rules check per candidate
  7. Gate 3 — score each valid candidate
  8. Return top N by final_score (always returns N, attaches confidence flag)
"""

from __future__ import annotations

import itertools
from collections import defaultdict
from typing import Union

import logging

from engine.models import (
    WardrobeItem, OutfitCandidate, OutfitTemplate, Occasion,
    Gender, InsufficientWardrobeError,
)
import numpy as np

from engine.hard_rules import passes_hard_rules
from engine.occasion_filter import filter_by_occasion
from engine.scorer import score_outfit, build_pair_vectors, model2_score_from_predictions

logger = logging.getLogger(__name__)


# 6 outfit templates keyed by OutfitTemplate enum (preserves plan constants)
TEMPLATES: dict[str, list[str]] = {
    "A": ["top", "bottom", "shoes"],
    "B": ["top", "bottom", "outwear", "shoes"],
    "C": ["dress", "shoes"],
    "D": ["dress", "outwear", "shoes"],
    "E": ["jumpsuit", "shoes"],
    "F": ["jumpsuit", "outwear", "shoes"],
    "G": ["top", "bottom"],
    "H": ["top", "bottom", "outwear"],
    "I": ["dress"],
    "J": ["dress", "outwear"],
    "K": ["jumpsuit"],
    "L": ["jumpsuit", "outwear"],
}

# Safety cap — prevents combinatorial explosion on large wardrobes
MAX_CANDIDATES_PER_TEMPLATE = 500


# ─── Private helpers ──────────────────────────────────────────────────────────

def _apply_gender_filter(
    items: list[WardrobeItem],
    gender_filter: Union[Gender, str],
) -> list[WardrobeItem]:
    """
    No-op. Retained for API compatibility with callers and tests.

    OutfitAI is a personal wardrobe app: every item the user uploaded is theirs
    to wear. Filtering by the gendered marketing label of a garment is the wrong
    abstraction here — that belongs in shared-inventory apps (e.g. Rent the Runway),
    not in a wardrobe where all items already belong to one person.

    Profile gender (users.gender) is preserved for future personalization features
    (silhouette guidance, fit recommendations). It no longer acts as a hard filter.
    """
    return items


def _check_wardrobe_minimum(items: list[WardrobeItem]) -> None:
    """
    Raise InsufficientWardrobeError if the items cannot form even one valid outfit.
    Minimum requirement: (top + bottom + shoes) OR (dress + shoes) OR (jumpsuit + shoes).
    """
    by_cat: dict[str, list[WardrobeItem]] = defaultdict(list)
    for item in items:
        by_cat[item.category].append(item)

    can_make_outfit = (
        (by_cat["top"] and by_cat["bottom"])
        or by_cat["dress"]
        or by_cat["jumpsuit"]
    )
    if not can_make_outfit:
        raise InsufficientWardrobeError(
            "Not enough items for this occasion. You need at minimum: "
            "(top + bottom + shoes) OR (dress + shoes) OR (jumpsuit + shoes)."
        )


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_recommendations(
    wardrobe: list[WardrobeItem],
    occasion: Union[Occasion, str],
    temp_celsius: float,
    gender_filter: Union[Gender, str],
    model2,                # Loaded Keras Model 2
    top_n: int = 3,
    anchor_item_id: int | None = None,
) -> list[OutfitCandidate]:
    """
    Generate top_n scored outfit recommendations from the user's wardrobe.

    When anchor_item_id is provided, only templates that include the anchor
    item's category are considered, and that category slot is pinned to the
    anchor item exclusively.

    Applies all three gates in sequence and always returns top_n results
    regardless of score threshold (GAP-05 fix). Confidence flags indicate
    result quality: high ≥ 0.70, medium ≥ 0.40, low < 0.40.

    Raises:
        InsufficientWardrobeError: If no valid outfit can be formed after filtering.
    """
    # Step 1: Gender filter (disabled — personal wardrobe, all items are the user's)
    items = _apply_gender_filter(wardrobe, gender_filter)
    logger.info("Wardrobe: %d items — %s", len(items),
                {cat: sum(1 for i in items if i.category == cat)
                 for cat in ["top", "bottom", "outwear", "shoes", "dress", "jumpsuit"]})

    # Step 2: Gate 2 — occasion filter (item-level, reduces candidate space)
    items = filter_by_occasion(items, occasion)
    logger.info("After occasion filter (%s): %d items — %s",
                occasion, len(items),
                {cat: sum(1 for i in items if i.category == cat)
                 for cat in ["top", "bottom", "outwear", "shoes", "dress", "jumpsuit"]})

    # Step 3: Ensure at least one valid outfit template is achievable
    _check_wardrobe_minimum(items)

    # Step 4: Group items by category for fast template lookup
    by_category: dict[str, list[WardrobeItem]] = defaultdict(list)
    for item in items:
        by_category[item.category].append(item)

    # ── Anchor item setup ──────────────────────────────────────────────────────
    anchor_item: WardrobeItem | None = None
    anchor_cat: str | None = None
    if anchor_item_id is not None:
        anchor_item = next(
            (i for i in items if i.item_id == anchor_item_id), None
        )
        if anchor_item is None:
            raise InsufficientWardrobeError(
                "The anchor item is not available for this occasion or gender filter."
            )
        anchor_cat = anchor_item.category.value  # plain string, e.g. "top"

    # Step 5–6: Enumerate and gate-1 filter (collect valid outfits before scoring)
    valid_outfits: list[tuple[list[WardrobeItem], str]] = []  # (outfit, template_id)

    for template_id, required_categories in TEMPLATES.items():
        # When anchoring: skip templates that don't use the anchor's category
        if anchor_cat is not None and anchor_cat not in required_categories:
            continue

        # Build per-slot item pools:
        #   - anchor category → only the anchor item
        #   - all other categories → normal wardrobe pool
        pools = [
            [anchor_item] if (anchor_cat is not None and cat == anchor_cat)
            else by_category[cat]
            for cat in required_categories
        ]

        # Skip template if any required category has zero items
        if not all(pools):
            continue

        combos = itertools.product(*pools)

        for i, combo in enumerate(combos):
            if i >= MAX_CANDIDATES_PER_TEMPLATE:
                break  # Safety cap for very large wardrobes

            outfit = list(combo)

            # Gate 1: structural validity
            if not passes_hard_rules(outfit):
                continue

            valid_outfits.append((outfit, template_id))

    # Step 7: Gate 3 — batch Model 2 scoring (single predict call)
    # Build all pair vectors across all outfits, run one batch prediction,
    # then distribute scores back. This collapses ~1800 individual predict()
    # calls into 1, eliminating per-call TensorFlow overhead.
    all_vectors = []
    outfit_pair_counts = []  # how many pairs each outfit has

    for outfit, _ in valid_outfits:
        vectors = build_pair_vectors(outfit)
        num_pairs = vectors.shape[0] // 2 if vectors.shape[0] > 0 else 0
        outfit_pair_counts.append(num_pairs)
        if vectors.shape[0] > 0:
            all_vectors.append(vectors)

    # Single batch prediction for ALL outfits
    if all_vectors:
        batch = np.vstack(all_vectors)
        logger.info(
            "Batch Model 2 predict: %d vectors (%d outfits)",
            batch.shape[0], len(valid_outfits),
        )
        all_predictions = model2.predict(batch, verbose=0).flatten()
    else:
        all_predictions = np.array([])

    # Distribute predictions back to each outfit and score
    candidates: list[OutfitCandidate] = []
    pred_offset = 0

    for idx, (outfit, template_id) in enumerate(valid_outfits):
        num_pairs = outfit_pair_counts[idx]
        num_rows = num_pairs * 2

        if num_pairs > 0:
            outfit_preds = all_predictions[pred_offset:pred_offset + num_rows]
            pred_offset += num_rows
            m2_score = model2_score_from_predictions(outfit_preds, num_pairs)
        else:
            m2_score = 0.80

        scored = score_outfit(outfit, model2, temp_celsius,
                              precomputed_model2_score=m2_score)
        if scored.template_id.value != template_id:
            scored = scored.model_copy(update={"template_id": OutfitTemplate(template_id)})
        candidates.append(scored)

    if not candidates:
        raise InsufficientWardrobeError(
            "No valid outfit combinations could be generated for this request."
        )

    # Step 8: Apply completeness bonus, sort, return top N
    # Outfits with more items get a small bonus so 3-item outfits (with shoes)
    # rank above 2-item outfits with similar pairwise scores. Without this,
    # sparse outfits dominate because fewer pairs dilute the model2 average less.
    COMPLETENESS_BONUS = 0.03  # per item beyond 2
    boosted: list[tuple[float, OutfitCandidate]] = []
    for c in candidates:
        bonus = max(0, len(c.items) - 2) * COMPLETENESS_BONUS
        boosted.append((c.final_score + bonus, c))

    boosted.sort(key=lambda x: x[0], reverse=True)

    # Deduplicate: same item combination can appear via different templates
    seen: set[frozenset[int]] = set()
    deduped: list[tuple[float, OutfitCandidate]] = []
    for score, c in boosted:
        key = frozenset(i.item_id for i in c.items)
        if key not in seen:
            seen.add(key)
            deduped.append((score, c))

    return [c for _, c in deduped[:top_n]]
