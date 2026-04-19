"""
engine/occasion_filter.py
Gate 2 — Occasion filter that removes wardrobe items inappropriate for the
selected occasion. Operates at item level BEFORE outfit enumeration to reduce
the candidate space.

Relies on the `formality` tag set by the user at item upload time (GAP-01 fix).
"""

from __future__ import annotations

from typing import Union

from engine.models import WardrobeItem, Occasion


OCCASION_RULES: dict[str, set[str]] = {
    "casual": {"casual", "formal", "both"},   # All formalities allowed
    "formal": {"formal", "both"},             # No casual-only items
}


def filter_by_occasion(
    items: list[WardrobeItem],
    occasion: Union[Occasion, str],
) -> list[WardrobeItem]:
    """Return only items whose formality is appropriate for the given occasion."""
    # Normalize: accept both Occasion enum and plain string
    occasion_key = occasion.value if isinstance(occasion, Occasion) else str(occasion)
    allowed = OCCASION_RULES[occasion_key]
    return [item for item in items if item.formality in allowed]
