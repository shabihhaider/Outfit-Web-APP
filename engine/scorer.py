"""
engine/scorer.py
Gate 3 orchestrator — computes the final weighted score for one outfit.

Score formula (5-component):
    final = model2_score   × 0.35
          + color_score    × 0.20
          + weather_score  × 0.15
          + cohesion_score × 0.10
          + synergy_score  × 0.20

Components:
  model2   (0.35) — learned pairwise compatibility from Polyvore outfit data
  color    (0.20) — Itten hue harmony × saturation consistency (Albers 1963)
  weather  (0.15) — ASHRAE 55 CLO thermal comfort matching
  cohesion (0.10) — EfficientNet-B0 embedding cosine similarity (visual aesthetic unity)
  synergy  (0.20) — knowledge-based fashion pairings (cultural + global outfit grammar)

Model 2 is scored symmetrically (GAP-03 fix): for every pair, both orderings
are averaged so score(A,B) == score(B,A) regardless of training order.
"""

from __future__ import annotations

import numpy as np

from engine.models import (
    WardrobeItem, OutfitCandidate, OutfitTemplate,
    Confidence, TEMPLATE_CATEGORIES,
)
from engine.color_scorer import score_outfit_color
from engine.weather_scorer import score_outfit_weather
from engine.cohesion_scorer import score_outfit_cohesion
from engine.style_intelligence import score_outfit_intelligence


# ─── Constants ────────────────────────────────────────────────────────────────

WEIGHTS = {
    "model2":   0.35,
    "color":    0.20,
    "weather":  0.15,
    "cohesion": 0.10,
    "synergy":  0.20,
}

THRESHOLD_HIGH   = 0.70
THRESHOLD_MEDIUM = 0.40


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _infer_template(outfit: list[WardrobeItem]) -> OutfitTemplate:
    """
    Determine the outfit template from the set of categories present.
    Raises ValueError if the combination doesn't match any template.
    """
    cats = frozenset(item.category for item in outfit)
    for template, required in TEMPLATE_CATEGORIES.items():
        if cats == frozenset(required):
            return template
    raise ValueError(f"Cannot infer outfit template from categories: {cats}")


def _score_pair_symmetric(
    a: WardrobeItem,
    b: WardrobeItem,
    model2,  # Keras model
) -> float:
    """
    Compute a symmetric pairwise compatibility score.

    Runs inference in both orderings (A→B and B→A) and returns the average,
    guaranteeing score(A,B) == score(B,A) regardless of the order pairs were
    presented during training.
    """
    cat_a = a.category_onehot()
    cat_b = b.category_onehot()
    emb_a = a.embedding_array()
    emb_b = b.embedding_array()

    vec_ab = np.concatenate([emb_a, emb_b, cat_a, cat_b]).reshape(1, -1)
    vec_ba = np.concatenate([emb_b, emb_a, cat_b, cat_a]).reshape(1, -1)

    score_ab = model2.predict(vec_ab, verbose=0)[0][0]
    score_ba = model2.predict(vec_ba, verbose=0)[0][0]
    return (float(score_ab) + float(score_ba)) / 2.0


# ─── Public API ───────────────────────────────────────────────────────────────

def score_outfit(
    outfit: list[WardrobeItem],
    model2,           # Loaded Keras model
    temp_celsius: float,
) -> OutfitCandidate:
    """
    Score a single outfit across all four Gate 3 components and return an
    OutfitCandidate with the weighted final score and confidence level.

    The four components:
      1. Model 2 pairwise compatibility (learned from Polyvore data)
      2. Color harmony (Itten hue theory + saturation consistency)
      3. Weather CLO comfort (ASHRAE Standard 55)
      4. Visual cohesion (EfficientNet-B0 embedding cosine similarity)
    """
    # Model 2: average symmetric pairwise scores across all pairs in the outfit
    pairs = [
        (outfit[i], outfit[j])
        for i in range(len(outfit))
        for j in range(i + 1, len(outfit))
    ]
    pair_scores = [_score_pair_symmetric(a, b, model2) for a, b in pairs]
    model2_score = sum(pair_scores) / len(pair_scores) if pair_scores else 0.80

    color_score    = score_outfit_color(outfit)
    weather_score  = score_outfit_weather(outfit, temp_celsius)
    cohesion_score = score_outfit_cohesion(outfit)
    synergy_score  = score_outfit_intelligence(outfit)

    final = (
        model2_score   * WEIGHTS["model2"]
        + color_score   * WEIGHTS["color"]
        + weather_score * WEIGHTS["weather"]
        + cohesion_score * WEIGHTS["cohesion"]
        + synergy_score * WEIGHTS["synergy"]
    )

    confidence = (
        Confidence.HIGH   if final >= THRESHOLD_HIGH
        else Confidence.MEDIUM if final >= THRESHOLD_MEDIUM
        else Confidence.LOW
    )

    template_id = _infer_template(outfit)

    return OutfitCandidate(
        items          = outfit,
        template_id    = template_id,
        model2_score   = model2_score,
        color_score    = color_score,
        weather_score  = weather_score,
        cohesion_score = cohesion_score,
        synergy_score  = synergy_score,
        final_score    = final,
        confidence     = confidence,
    )
