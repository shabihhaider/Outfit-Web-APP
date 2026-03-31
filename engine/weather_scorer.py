"""
engine/weather_scorer.py
Gate 3 component — scores how well an outfit's thermal insulation (CLO value)
matches the current ambient temperature.

Based on:
  ASHRAE Standard 55 (Thermal Environmental Conditions for Human Occupancy)
  ISO 11092 (Measurement of thermal and water-vapour resistance)

CLO values are category-level averages since fabric type cannot be inferred
from clothing images.
"""

from __future__ import annotations

from engine.models import WardrobeItem


# Category-level CLO averages (ASHRAE 55 Standard Table)
CLO_VALUES: dict[str, float] = {
    "top":      0.25,   # Light shirt / blouse
    "bottom":   0.24,   # Trousers / jeans
    "outwear":  0.48,   # Jacket / coat
    "shoes":    0.03,   # Footwear — minimal thermal contribution
    "dress":    0.33,   # Average dress (light 0.20 → formal 0.45)
    "jumpsuit": 0.49,   # Full-body coverage (one-piece, ISO 11092: 0.40–0.58)
}

# Fallback CLO if an unexpected category appears
_DEFAULT_CLO = 0.20


def get_target_clo_range(temp_celsius: float) -> tuple[float, float]:
    """
    Return (min_comfortable_clo, max_comfortable_clo) for the given temperature.
    Based on ASHRAE Standard 55 comfort zone for sedentary activity (1.0 met).
    """
    if temp_celsius >= 40:
        return (0.10, 0.60)   # Very hot: light clothing (Lahore summer, top+bottom+shoes=0.52)
    elif temp_celsius >= 32:
        return (0.25, 0.55)   # Hot: light clothing
    elif temp_celsius >= 24:
        return (0.45, 0.80)   # Warm: light to medium
    elif temp_celsius >= 16:
        return (0.70, 1.20)   # Mild: medium weight
    elif temp_celsius >= 8:
        return (1.00, 1.70)   # Cool: heavier clothing
    elif temp_celsius >= 0:
        return (1.50, 2.20)   # Cold: winter clothing
    else:
        return (2.00, 3.00)   # Very cold: heavy winter (rare for Pakistan)


def score_outfit_weather(items: list[WardrobeItem], temp_celsius: float) -> float:
    """
    Score how well the outfit's total CLO matches the ambient temperature.

    Returns:
      1.0  — total CLO is within the comfortable range.
      >0.0 — linearly decreasing as CLO deviates outside the comfort zone.
      0.0  — CLO deviation equals or exceeds the half-width of the comfort zone.
    """
    total_clo = sum(CLO_VALUES.get(item.category, _DEFAULT_CLO) for item in items)
    clo_min, clo_max = get_target_clo_range(temp_celsius)

    if clo_min <= total_clo <= clo_max:
        return 1.0  # Perfect thermal fit

    # Linear penalty proportional to deviation outside the comfort zone,
    # normalized by the half-width of the range.
    clo_half_width = (clo_max - clo_min) / 2.0
    distance = max(total_clo - clo_max, clo_min - total_clo)
    penalty = min(distance / clo_half_width, 1.0)
    return max(0.0, 1.0 - penalty)
