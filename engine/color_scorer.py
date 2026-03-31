"""
engine/color_scorer.py
Gate 3 component — scores color harmony between all items in an outfit using
Itten Color Theory (1961) with saturation consistency scoring.

Two sub-components:
  1. Hue harmony  — Itten Color Theory relationships (complementary, analogous, triadic, etc.)
  2. Saturation consistency — penalises mixing very vibrant and very muted items
     (based on saturation contrast principles from Itten 1961 and Albers 1963)

Final color score = hue_harmony × saturation_consistency_factor

Neutral items (saturation < 0.15) are excluded from hue scoring because
white/black/grey never clash with any color.
"""

from __future__ import annotations

from engine.models import WardrobeItem


# Saturation below this threshold → item is considered neutral (white/grey/black/beige)
NEUTRAL_SATURATION_THRESHOLD = 0.15

# (name, ideal_angular_distance_degrees, tolerance_degrees, harmony_score)
HARMONY_RULES: list[tuple[str, float, float, float]] = [
    ("monochromatic",     0.0,  25.0, 0.90),
    ("analogous",        30.0,  20.0, 0.85),
    ("complementary",   180.0,  25.0, 1.00),  # Strongest harmony
    ("split_comp_left", 150.0,  20.0, 0.80),
    ("split_comp_right",210.0,  20.0, 0.80),
    ("triadic_60",       60.0,  20.0, 0.75),
    ("triadic_120",     120.0,  20.0, 0.75),
]


def hue_distance(h1: float, h2: float) -> float:
    """Shortest angular distance on the color wheel, in range 0–180 degrees."""
    diff = abs(h1 - h2) % 360.0
    return min(diff, 360.0 - diff)


def score_pair_hue(h1: float, h2: float) -> float:
    """
    Return harmony score for a pair of hues using Itten's rules.
    Checks each harmony type in HARMONY_RULES and returns the first match's score.
    Returns 0.40 (weak score) if no recognized harmony is found.
    """
    dist = hue_distance(h1, h2)
    for _name, ideal, tol, score in HARMONY_RULES:
        if abs(dist - ideal) <= tol:
            return score
    return 0.40  # No recognized harmony


def _saturation_consistency(non_neutral: list[WardrobeItem]) -> float:
    """
    Score saturation consistency across non-neutral items (0.60–1.0).

    Mixing very vibrant items (sat ≈ 0.9) with very muted items (sat ≈ 0.1)
    creates visual tension. Items with similar saturation levels read as
    intentionally coordinated.

    Reference: saturation contrast in Itten (1961) and Albers (1963).
    """
    if len(non_neutral) <= 1:
        return 1.0

    sats = [item.dominant_sat for item in non_neutral]
    sat_range = max(sats) - min(sats)

    if sat_range <= 0.25:
        return 1.0   # Highly consistent
    elif sat_range <= 0.45:
        return 0.90  # Acceptable variance
    elif sat_range <= 0.65:
        return 0.75  # Noticeable mismatch
    else:
        return 0.60  # Strong vibrancy clash


def score_outfit_color(items: list[WardrobeItem]) -> float:
    """
    Score color harmony for an outfit (0.0–1.0).

    Two-component scoring:
      1. Hue harmony  — Itten Color Theory relationships (complementary, analogous, etc.)
      2. Saturation consistency — penalises mixing very vibrant and very muted items

    Final = hue_score × saturation_consistency_factor

    Rules:
      - Neutral items (sat < 0.15) are excluded from hue and saturation scoring.
      - All neutrals  → 0.85 (clean, monochromatic-neutral, always acceptable).
      - One non-neutral + neutrals → 0.80 (safe single-color outfit).
      - Two+ non-neutrals → hue harmony × saturation consistency.
    """
    non_neutral = [i for i in items if i.dominant_sat >= NEUTRAL_SATURATION_THRESHOLD]

    if len(non_neutral) == 0:
        return 0.85  # All neutrals — clean but uninspired

    if len(non_neutral) == 1:
        return 0.80  # One color + neutrals — always safe

    # Component 1: hue harmony
    hue_scores: list[float] = []
    for i in range(len(non_neutral)):
        for j in range(i + 1, len(non_neutral)):
            hue_scores.append(score_pair_hue(
                non_neutral[i].dominant_hue,
                non_neutral[j].dominant_hue,
            ))
    hue_score = sum(hue_scores) / len(hue_scores)

    # Component 2: saturation consistency multiplier
    sat_factor = _saturation_consistency(non_neutral)

    return hue_score * sat_factor
