"""
engine/pipeline.py
End-to-end entry point for the recommendation engine.

Loads both ML models once at startup, then exposes:
  - classify_and_embed()  — called at item upload time (via Flask)
  - recommend()           — called per recommendation request (via Flask)

The Flask layer is responsible for:
  - Calling the weather API and passing temp_celsius
  - Reading WardrobeItem objects from the database
  - Calling extract_dominant_color_hsv() at upload time
"""

from __future__ import annotations

import numpy as np

from engine.models import (
    WardrobeItem, OutfitCandidate, RecommendationRequest,
    RecommendationResponse, Confidence, ModelNotLoadedError, WeatherLocationError,
)
from engine.outfit_generator import generate_recommendations
from engine.color_extractor import extract_dominant_color_hsv
from engine.weather_api import get_temperature_by_coords


# Maps Model 1 classifier output index → category string.
# MUST match Kaggle_Model1_Training_Code.md:
#   CATEGORIES = ['top', 'bottom', 'outwear', 'shoes', 'dress', 'jumpsuit']
#   cat2idx = {cat: idx for idx, cat in enumerate(CATEGORIES)}
# → {top:0, bottom:1, outwear:2, shoes:3, dress:4, jumpsuit:5}
_IDX_TO_CATEGORY: dict[int, str] = {
    0: "top",
    1: "bottom",
    2: "outwear",
    3: "shoes",
    4: "dress",
    5: "jumpsuit",
}

# Input size for Model 1 (EfficientNet-B0 expects 256×256 RGB)
_MODEL1_INPUT_SIZE = (256, 256)


def _load_and_preprocess(image_path: str) -> np.ndarray:
    """
    Load an image and preprocess it for Model 1 inference.
    Returns a float32 array of shape (256, 256, 3) in [0, 255] range.
    Note: EfficientNet-B0 has built-in preprocessing; model was trained on [0, 255].
    """
    import cv2
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not load image: {image_path}")
    img = cv2.resize(img, _MODEL1_INPUT_SIZE)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img.astype(np.float32)


class RecommendationPipeline:
    """
    Wraps the two ML models and exposes the recommendation API.

    Usage (from Flask app factory):
        pipeline = RecommendationPipeline(
            model1_path="models/model1_efficientnet_best.h5",
            model2_path="models/model 2 Assets/model2_compatibility_scorer.h5",
        )
    """

    def __init__(self, model1_path: str, model2_path: str) -> None:
        """
        Load both models from disk. Raises ModelNotLoadedError on failure.

        Args:
            model1_path: Path to the full EfficientNet-B0 classifier (.h5).
                         Used for both category prediction and embedding extraction.
            model2_path: Path to the MLP compatibility scorer (.h5).
        """
        try:
            from tensorflow.keras.models import load_model  # type: ignore[import]
            self._classifier = load_model(model1_path)
            self._model2     = load_model(model2_path)
        except Exception as exc:
            raise ModelNotLoadedError(
                f"Failed to load models. "
                f"model1='{model1_path}', model2='{model2_path}'. "
                f"Original error: {exc}"
            ) from exc

        # Build a secondary model that outputs the 1280-dim embedding layer
        # (the GlobalAveragePooling2D output, last layer before the classifier head)
        self._embedding_extractor = self._build_embedding_extractor()

    @property
    def model2(self):
        """Public accessor for the Model 2 compatibility scorer (used by score-outfit route)."""
        return self._model2

    def _build_embedding_extractor(self):
        """
        Construct a sub-model that returns the 1280-dim embedding vector from
        the full classifier. The embedding is the output of the penultimate layer
        (GlobalAveragePooling2D in EfficientNet-B0).
        """
        from tensorflow.keras.models import Model  # type: ignore[import]
        # The embedding layer is the second-to-last layer in our EfficientNet-B0
        # training setup (last layer is the Dense softmax classifier)
        embedding_layer = self._classifier.layers[-2]
        return Model(
            inputs  = self._classifier.input,
            outputs = embedding_layer.output,
        )

    # ─── Upload-time API ──────────────────────────────────────────────────────

    def classify_and_embed(
        self,
        image_path: str,
    ) -> tuple[str, np.ndarray, float]:
        """
        Run Model 1 on an image. Returns (category_label, embedding_1280, confidence).

        Called once per uploaded image. The results are stored in the database
        alongside the color values from extract_dominant_color_hsv().

        Args:
            image_path: Path to the uploaded clothing image.

        Returns:
            (category, embedding, confidence) where category is one of the 6 label
            strings, embedding is a float32 ndarray of shape (1280,), and confidence
            is the max softmax probability (0.0–1.0).

        Raises:
            ValueError: If the top class probability is below 0.45, indicating the
                image is unlikely to be a clothing item.
        """
        img = _load_and_preprocess(image_path)
        batch = img[np.newaxis]  # (1, 256, 256, 3)

        # Extract 1280-dim embedding
        embedding: np.ndarray = self._embedding_extractor.predict(batch, verbose=0)[0]

        # Get class probabilities from the full classifier
        probs: np.ndarray = self._classifier.predict(batch, verbose=0)[0]
        category_idx = int(np.argmax(probs))
        category = _IDX_TO_CATEGORY.get(category_idx, "top")

        confidence = float(np.max(probs))
        if confidence < 0.75:
            raise ValueError(
                f"Image does not appear to be a clear clothing item "
                f"(confidence {confidence:.2f} < 0.75). "
                f"Please upload a clear photo of a single clothing item."
            )

        return category, embedding.astype(np.float32), confidence

    def extract_color(self, image_path: str) -> tuple[float, float, float]:
        """
        Extract dominant color from an image. Delegates to color_extractor.
        Returns (hue_degrees, saturation_0_1, value_0_1).
        """
        return extract_dominant_color_hsv(image_path)

    # ─── Weather API ──────────────────────────────────────────────────────────

    def get_temperature(
        self,
        lat: float | None,
        lon: float | None,
    ) -> float:
        """
        Fetch the current temperature in Celsius for a recommendation request.

        Args:
            lat: User latitude from the browser geolocation API.
            lon: User longitude from the browser geolocation API.

        Returns:
            Current temperature in Celsius.

        Raises:
            WeatherLocationError: If lat or lon is None. The Flask layer must
                handle this — either by asking the browser for location or by
                accepting a manual temperature input from the user.
            WeatherAPIError: If the WeatherAPI call fails (network,
                bad key, unexpected response). Flask handles this too.

        This float feeds directly into temp_celsius in scorer.py / recommend().
        """
        if lat is None or lon is None:
            raise WeatherLocationError(
                "Location coordinates are required to fetch temperature. "
                "Request location permission from the user or accept temp_celsius directly."
            )
        return get_temperature_by_coords(lat, lon)

    # ─── Recommendation-time API ──────────────────────────────────────────────

    def recommend(
        self,
        wardrobe: list[WardrobeItem],
        occasion: str,
        temp_celsius: float,
        gender_filter: str,
        top_n: int = 3,
        anchor_item_id: int | None = None,
    ) -> list[OutfitCandidate]:
        """
        Generate top_n outfit recommendations from the user's wardrobe.

        Args:
            wardrobe:        List of WardrobeItem objects loaded from the database.
            occasion:        "casual" | "formal" | "wedding"
            temp_celsius:    Current temperature (from weather API or user input).
            gender_filter:   "men" | "women" | "unisex"
            top_n:           Number of recommendations to return (default 3).
            anchor_item_id:  Optional item ID to anchor outfits around. When set,
                             only templates containing the anchor's category are
                             considered, and that slot is pinned to the anchor item.

        Returns:
            List of OutfitCandidate objects sorted by final_score descending.

        Raises:
            InsufficientWardrobeError: If no valid outfits can be formed.
        """
        return generate_recommendations(
            wardrobe        = wardrobe,
            occasion        = occasion,
            temp_celsius    = temp_celsius,
            gender_filter   = gender_filter,
            model2          = self._model2,
            top_n           = top_n,
            anchor_item_id  = anchor_item_id,
        )

    def recommend_from_request(
        self,
        wardrobe: list[WardrobeItem],
        request: RecommendationRequest,
    ) -> RecommendationResponse:
        """
        Convenience wrapper that accepts a RecommendationRequest and returns
        a full RecommendationResponse with the warning message set when
        all results have low confidence.
        """
        outfits = self.recommend(
            wardrobe      = wardrobe,
            occasion      = request.occasion,
            temp_celsius  = request.temp_celsius,
            gender_filter = request.gender_filter,
            top_n         = request.top_n,
        )

        has_low = outfits[0].confidence == Confidence.LOW if outfits else False
        warning = (
            "We could not find strongly compatible outfits for this occasion. "
            "These are the best available matches."
            if has_low else None
        )

        return RecommendationResponse(
            request          = request,
            outfits          = outfits,
            has_low_confidence = has_low,
            warning          = warning,
        )
