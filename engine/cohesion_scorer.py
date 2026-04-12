"""
engine/cohesion_scorer.py
Gate 3 component — scores visual cohesion of an outfit using centroid-based
alignment in the EfficientNet-B0 embedding space.

Architecture rationale:
  Pairwise cross-category cosine similarity (shoe vs. dress) compares items
  from different semantic regions of the embedding space. This measures shared
  low-level features (brightness, dominant color) rather than aesthetic unity.

  The centroid approach is more principled:
    1. Compute the mean embedding of all outfit items → the outfit's "visual theme"
    2. Score each item's cosine similarity to this centroid
    3. Average the per-item similarities

  Interpretation:
    - High cohesion: all items point in a similar direction in embedding space,
      sharing a common aesthetic register (same formality level, matching texture
      density, coherent pattern style)
    - Low cohesion: one or more items is a visual outlier — an item that looks
      stylistically disconnected from the rest

  Properties:
    - Outfit-size invariant: 2-item and 4-item outfits are scored on the same scale
    - Sensitive to single outliers: one mismatched item pulls the centroid and lowers
      all per-item similarities
    - EfficientNet-B0 GlobalAveragePooling2D produces non-negative activations
      (preceded by ReLU), so cosine similarities are in [0.0, 1.0]

Normalization:
  Item-to-centroid cosine similarities for clothing outfit items typically fall
  in [0.75, 0.98]. We map this range linearly to [0.0, 1.0] and clip.
  Items scoring < 0.75 (major visual outlier) map to 0.0.
  Items scoring > 0.98 (identical visual features) map to 1.0.
"""

from __future__ import annotations

import numpy as np

from engine.models import WardrobeItem


# Expected item-to-centroid cosine similarity range for clothing outfits.
# EfficientNet-B0 produces non-negative embeddings; clothing items share
# enough visual structure (fabric-like texture, human-wearable shapes) that
# cross-category item-centroid similarities rarely drop below 0.75 for
# real outfit combinations. Above 0.98 indicates near-identical aesthetic.
_COHESION_LOW  = 0.75
_COHESION_HIGH = 0.98


def score_outfit_cohesion(items: list[WardrobeItem]) -> float:
    """
    Score visual cohesion for an outfit via centroid-alignment (0.0–1.0).

    Algorithm:
      1. Compute outfit centroid = mean of all item embedding vectors
      2. For each item, compute cosine similarity to the centroid
      3. Average the per-item similarities → raw cohesion signal
      4. Normalise [_COHESION_LOW, _COHESION_HIGH] → [0.0, 1.0]

    Returns 0.80 for single-item outfits (no theme to align with).
    """
    if len(items) < 2:
        return 0.80

    embeddings = [item.embedding_array() for item in items]

    # Step 1: outfit visual theme centroid
    centroid = np.mean(embeddings, axis=0)
    centroid_norm = np.linalg.norm(centroid)
    if centroid_norm < 1e-9:
        return 0.80  # Degenerate case — zero centroid

    # Step 2: per-item similarity to centroid
    item_sims: list[float] = []
    for emb in embeddings:
        emb_norm = np.linalg.norm(emb)
        if emb_norm < 1e-9:
            continue
        sim = float(np.dot(emb, centroid) / (emb_norm * centroid_norm))
        item_sims.append(max(0.0, sim))  # clip any floating-point negatives

    if not item_sims:
        return 0.80

    # Step 3: average
    avg_centroid_sim = sum(item_sims) / len(item_sims)

    # Step 4: normalise
    normalized = (avg_centroid_sim - _COHESION_LOW) / (_COHESION_HIGH - _COHESION_LOW)
    return float(max(0.0, min(1.0, normalized)))
