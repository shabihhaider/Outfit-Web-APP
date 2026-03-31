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
    Gender, InsufficientWardrobeError, TEMPLATE_CATEGORIES,
)
from engine.hard_rules import passes_hard_rules
from engine.occasion_filter import filter_by_occasion
from engine.scorer import score_outfit

logger = logging.getLogger(__name__)


# 6 outfit templates keyed by OutfitTemplate enum (preserves plan constants)
TEMPLATES: dict[str, list[str]] = {
    "A": ["top", "bottom", "shoes"],
    "B": ["top", "bottom", "outwear", "shoes"],
    "C": ["dress", "shoes"],
    "D": ["dress", "outwear", "shoes"],
    "E": ["jumpsuit", "shoes"],
    "F": ["jumpsuit", "outwear", "shoes"],
}

# Safety cap — prevents combinatorial explosion on large wardrobes
MAX_CANDIDATES_PER_TEMPLATE = 500


# ─── Private helpers ──────────────────────────────────────────────────────────

def _apply_gender_filter(
    items: list[WardrobeItem],
    gender_filter: Union[Gender, str],
) -> list[WardrobeItem]:
    """
    Keep only items appropriate for the user's gender preference.
    UNISEX items are always included. Requesting "unisex" keeps everything.
    """
    # Normalize: accept both Gender enum and plain string
    gender_key = gender_filter.value if isinstance(gender_filter, Gender) else str(gender_filter)

    if gender_key == Gender.UNISEX or gender_key == "unisex":
        return items  # No filtering — keep all items

    return [
        item for item in items
        if item.gender == gender_key or item.gender == Gender.UNISEX
    ]


def _check_wardrobe_minimum(items: list[WardrobeItem]) -> None:
    """
    Raise InsufficientWardrobeError if the items cannot form even one valid outfit.
    Minimum requirement: (top + bottom + shoes) OR (dress + shoes) OR (jumpsuit + shoes).
    """
    by_cat: dict[str, list[WardrobeItem]] = defaultdict(list)
    for item in items:
        by_cat[item.category].append(item)

    can_make_outfit = (
        (by_cat["top"] and by_cat["bottom"] and by_cat["shoes"])
        or (by_cat["dress"] and by_cat["shoes"])
        or (by_cat["jumpsuit"] and by_cat["shoes"])
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
    # Step 1: Gender filter
    items = _apply_gender_filter(wardrobe, gender_filter)
    logger.info("After gender filter (%s): %d items — %s",
                gender_filter, len(items),
                {cat: sum(1 for i in items if i.category == cat)
                 for cat in ["top","bottom","outwear","shoes","dress","jumpsuit"]})

    # Step 2: Gate 2 — occasion filter (item-level, reduces candidate space)
    items = filter_by_occasion(items, occasion)
    logger.info("After occasion filter (%s): %d items — %s",
                occasion, len(items),
                {cat: sum(1 for i in items if i.category == cat)
                 for cat in ["top","bottom","outwear","shoes","dress","jumpsuit"]})

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

    # Step 5–7: Enumerate, gate-1 filter, score
    candidates: list[OutfitCandidate] = []

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

            # Gate 3: score
            scored = score_outfit(outfit, model2, temp_celsius)
            # template_id is already inferred inside score_outfit; set explicitly
            # using model_copy to stay compatible with Pydantic v2 immutability
            if scored.template_id.value != template_id:
                scored = scored.model_copy(update={"template_id": OutfitTemplate(template_id)})
            candidates.append(scored)

    if not candidates:
        raise InsufficientWardrobeError(
            "No valid outfit combinations could be generated for this request."
        )

    # Step 8: Sort by final_score descending, return top N
    # Always return top_n even if all scores are below threshold (GAP-05 fix)
    candidates.sort(key=lambda x: x.final_score, reverse=True)
    return candidates[:top_n]
