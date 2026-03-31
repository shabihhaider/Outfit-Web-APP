"""
engine/
3-Gate Recommendation Engine for the Outfit Recommendation System.

Public API:
    InsufficientWardrobeError — raised when wardrobe has no valid combinations
    ModelNotLoadedError       — raised when inference runs before model load
    WardrobeItem              — core data model for a wardrobe item
    OutfitCandidate           — scored outfit output
    RecommendationRequest     — input to pipeline.recommend()
    RecommendationResponse    — output from pipeline.recommend()

Usage (from Flask, after pipeline.py is implemented):
    from engine import RecommendationPipeline, InsufficientWardrobeError
"""

from engine.models import (
    InsufficientWardrobeError,
    ModelNotLoadedError,
    WeatherAPIError,
    WeatherLocationError,
    WardrobeItem,
    OutfitCandidate,
    RecommendationRequest,
    RecommendationResponse,
    Category,
    Formality,
    Gender,
    Occasion,
    Confidence,
    OutfitTemplate,
    CAT_TO_IDX,
    TEMPLATE_CATEGORIES,
)
from engine.pipeline import RecommendationPipeline

__all__ = [
    "RecommendationPipeline",
    "InsufficientWardrobeError",
    "ModelNotLoadedError",
    "WeatherAPIError",
    "WeatherLocationError",
    "WardrobeItem",
    "OutfitCandidate",
    "RecommendationRequest",
    "RecommendationResponse",
    "Category",
    "Formality",
    "Gender",
    "Occasion",
    "Confidence",
    "OutfitTemplate",
    "CAT_TO_IDX",
    "TEMPLATE_CATEGORIES",
]
