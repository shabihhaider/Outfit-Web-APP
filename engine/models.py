"""
engine/models.py
Core data models for the Phase 4 recommendation engine.
Uses Pydantic for automatic validation and clear error messages.
"""

from __future__ import annotations

import numpy as np
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ─── Enumerations ─────────────────────────────────────────────────────────────

class Category(str, Enum):
    TOP = "top"
    BOTTOM = "bottom"
    OUTWEAR = "outwear"
    SHOES = "shoes"
    DRESS = "dress"
    JUMPSUIT = "jumpsuit"


class Formality(str, Enum):
    CASUAL = "casual"
    FORMAL = "formal"
    BOTH = "both"


class Gender(str, Enum):
    MEN = "men"
    WOMEN = "women"
    UNISEX = "unisex"


class Occasion(str, Enum):
    CASUAL = "casual"
    FORMAL = "formal"
    WEDDING = "wedding"


class Confidence(str, Enum):
    HIGH = "high"    # final_score >= 0.70
    MEDIUM = "medium"  # final_score >= 0.40
    LOW = "low"     # final_score <  0.40


class OutfitTemplate(str, Enum):
    A = "A"  # top + bottom + shoes
    B = "B"  # top + bottom + outwear + shoes
    C = "C"  # dress + shoes
    D = "D"  # dress + outwear + shoes
    E = "E"  # jumpsuit + shoes
    F = "F"  # jumpsuit + outwear + shoes
    G = "G"  # top + bottom
    H = "H"  # top + bottom + outwear
    I = "I"  # dress (standalone)  # noqa: E741
    J = "J"  # dress + outwear
    K = "K"  # jumpsuit (standalone)
    L = "L"  # jumpsuit + outwear


# ─── Category order — MUST match model2_results.json ─────────────────────────
# {"bottom":0, "dress":1, "outwear":2, "shoes":3, "top":4}
CAT_TO_IDX: dict[str, int] = {
    Category.BOTTOM: 0,
    Category.DRESS: 1,
    Category.OUTWEAR: 2,
    Category.SHOES: 3,
    Category.TOP: 4,
}

TEMPLATE_CATEGORIES: dict[OutfitTemplate, list[Category]] = {
    OutfitTemplate.A: [Category.TOP, Category.BOTTOM, Category.SHOES],
    OutfitTemplate.B: [Category.TOP, Category.BOTTOM, Category.OUTWEAR, Category.SHOES],
    OutfitTemplate.C: [Category.DRESS, Category.SHOES],
    OutfitTemplate.D: [Category.DRESS, Category.OUTWEAR, Category.SHOES],
    OutfitTemplate.E: [Category.JUMPSUIT, Category.SHOES],
    OutfitTemplate.F: [Category.JUMPSUIT, Category.OUTWEAR, Category.SHOES],
    OutfitTemplate.G: [Category.TOP, Category.BOTTOM],
    OutfitTemplate.H: [Category.TOP, Category.BOTTOM, Category.OUTWEAR],
    OutfitTemplate.I: [Category.DRESS],
    OutfitTemplate.J: [Category.DRESS, Category.OUTWEAR],
    OutfitTemplate.K: [Category.JUMPSUIT],
    OutfitTemplate.L: [Category.JUMPSUIT, Category.OUTWEAR],
}


# ─── Core Models ──────────────────────────────────────────────────────────────

class WardrobeItem(BaseModel):
    """
    A single clothing item from a user's wardrobe.
    Embedding and color are pre-computed at upload time and stored in the DB.
    """
    item_id: int
    category: Category
    formality: Formality
    gender: Gender
    embedding: list[float] = Field(..., min_length=1280, max_length=1280)
    dominant_hue: float = Field(..., ge=0.0, le=360.0)
    dominant_sat: float = Field(..., ge=0.0, le=1.0)
    dominant_val: float = Field(..., ge=0.0, le=1.0)

    @field_validator("embedding")
    @classmethod
    def embedding_must_be_1280(cls, v: list[float]) -> list[float]:
        if len(v) != 1280:
            raise ValueError(f"Embedding must be 1280-dim, got {len(v)}")
        return v

    def embedding_array(self) -> np.ndarray:
        """Return embedding as a numpy float32 array for model inference."""
        return np.array(self.embedding, dtype=np.float32)

    def category_onehot(self) -> np.ndarray:
        """Return 5-dim one-hot category vector matching CAT_TO_IDX order.
        Jumpsuit is mapped to dress (closest one-piece category) since
        Model 2 was trained on Polyvore which has no jumpsuit class."""
        vec = np.zeros(5, dtype=np.float32)
        cat = self.category
        if cat == Category.JUMPSUIT:
            cat = Category.DRESS  # nearest proxy for Model 2
        vec[CAT_TO_IDX[cat]] = 1.0
        return vec

    model_config = ConfigDict(arbitrary_types_allowed=True)


class OutfitCandidate(BaseModel):
    """
    A scored outfit candidate produced by the recommendation engine.
    Contains the items, per-component scores, final score, and confidence level.
    """
    items: list[WardrobeItem]
    template_id: OutfitTemplate
    model2_score: float = Field(..., ge=0.0, le=1.0)
    color_score: float = Field(..., ge=0.0, le=1.0)
    weather_score: float = Field(..., ge=0.0, le=1.0)
    cohesion_score: float = Field(..., ge=0.0, le=1.0)
    final_score: float = Field(..., ge=0.0, le=1.0)
    confidence: Confidence

    @model_validator(mode="after")
    def validate_items_match_template(self) -> OutfitCandidate:
        expected_cats = set(TEMPLATE_CATEGORIES[self.template_id])
        actual_cats = {item.category for item in self.items}
        if actual_cats != expected_cats:
            raise ValueError(
                f"Template {self.template_id} expects {expected_cats}, "
                f"but outfit contains {actual_cats}"
            )
        return self

    def item_ids(self) -> list[int]:
        return [item.item_id for item in self.items]

    def score_breakdown(self) -> dict[str, float]:
        return {
            "model2": round(self.model2_score, 3),
            "color": round(self.color_score, 3),
            "weather": round(self.weather_score, 3),
            "cohesion": round(self.cohesion_score, 3),
            "final": round(self.final_score, 3),
        }


class RecommendationRequest(BaseModel):
    """Input to the recommendation pipeline from the Flask layer."""
    user_id: int
    occasion: Occasion
    temp_celsius: float = Field(..., ge=-20.0, le=60.0,
                                description="Temperature in Celsius. Lahore range: -2 to 48.")
    gender_filter: Gender
    top_n: int = Field(default=3, ge=1, le=10)


class RecommendationResponse(BaseModel):
    """Output from the recommendation pipeline returned to the Flask layer."""
    request: RecommendationRequest
    outfits: list[OutfitCandidate]
    has_low_confidence: bool  # True if best outfit has confidence=="low"
    warning: Optional[str] = None  # Set when has_low_confidence is True


# ─── Exceptions ───────────────────────────────────────────────────────────────

class InsufficientWardrobeError(Exception):
    """
    Raised when the user's wardrobe (after gender + occasion filtering)
    does not contain enough items to form any valid outfit.
    """
    pass


class ModelNotLoadedError(Exception):
    """Raised when inference is attempted before models are loaded."""
    pass


class WeatherAPIError(Exception):
    """
    Raised when the WeatherAPI.com call fails (network error, bad key, etc.).
    Flask catches this and returns an appropriate HTTP error to the frontend.
    """
    pass


class WeatherLocationError(Exception):
    """
    Raised by pipeline.get_temperature() when no lat/lon are provided.
    The UI layer must handle this — either by requesting location permission
    or by asking the user to enter a temperature manually.
    """
    pass
