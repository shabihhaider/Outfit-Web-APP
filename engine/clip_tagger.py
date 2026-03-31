"""
engine/clip_tagger.py
Zero-shot sub-category classifier using CLIP (Contrastive Language-Image Pretraining).

This module addresses the core architectural limitation of Model 1: EfficientNet-B0
classifies into 6 coarse categories but cannot distinguish sub-categories such as
jeans vs. dress pants, blazer vs. hoodie, sneakers vs. heels, or kurta vs. polo.

CLIP (Radford et al., 2021 — OpenAI) matches images to textual descriptions using
a shared embedding space trained on 400M image-text pairs. This enables zero-shot
classification: no additional training is required. We define a sub-category taxonomy
per category and select the best-matching text description.

Why CLIP and not a retrained EfficientNet:
  - No labeled sub-category dataset is required
  - Supports Pakistani clothing (kurta, shalwar, sherwani) simply by adding text labels
  - Zero-shot means the taxonomy can be expanded without retraining
  - State-of-the-art zero-shot accuracy on clothing classification tasks

Dependency:
  pip install transformers torch  (or tensorflow — HuggingFace CLIP supports both)

Usage (at upload time, after Model 1 classification):
    from engine.clip_tagger import CLIPSubCategoryTagger
    tagger = CLIPSubCategoryTagger()
    sub_cat, confidence = tagger.classify(image_path, coarse_category="top")

The returned sub_category string can be stored in WardrobeItemDB.sub_category
and used to activate the hard-blocked fashion rules in engine/hard_rules.py.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ─── Sub-category taxonomy ────────────────────────────────────────────────────
# Defined as text prompts that CLIP can match against.
# Each entry: {"label": canonical_name, "prompts": [text descriptions for matching]}
# Including Pakistani clothing explicitly addresses the Western training data bias.

SUBCATEGORY_TAXONOMY: dict[str, list[dict]] = {
    "top": [
        {"label": "formal_shirt",   "prompts": ["a dress shirt", "a formal button-down shirt", "a business shirt", "an office shirt"]},
        {"label": "kurta",          "prompts": ["a kurta", "a Pakistani kurta", "a South Asian tunic", "a kameez", "a men's kurta shirt"]},
        {"label": "polo_shirt",     "prompts": ["a polo shirt", "a polo t-shirt", "a collared polo"]},
        {"label": "casual_tshirt",  "prompts": ["a casual t-shirt", "a graphic tee", "a plain t-shirt", "a casual top"]},
        {"label": "hoodie",         "prompts": ["a hoodie", "a sweatshirt", "a pullover hoodie", "a casual hoodie"]},
        {"label": "blouse",         "prompts": ["a blouse", "a women's blouse", "a formal blouse", "a chiffon blouse"]},
        {"label": "kameez",         "prompts": ["a kameez", "a women's kameez", "a Pakistani women's top", "a shalwar kameez top"]},
    ],
    "bottom": [
        {"label": "jeans",          "prompts": ["jeans", "denim jeans", "blue jeans", "casual denim trousers"]},
        {"label": "dress_trousers", "prompts": ["dress trousers", "formal pants", "business trousers", "suit pants", "dress pants"]},
        {"label": "shalwar",        "prompts": ["shalwar", "Pakistani shalwar", "baggy trousers", "traditional Pakistani pants"]},
        {"label": "chinos",         "prompts": ["chinos", "chino trousers", "khaki pants", "smart casual trousers"]},
        {"label": "shorts",         "prompts": ["shorts", "casual shorts", "summer shorts", "bermuda shorts"]},
        {"label": "skirt",          "prompts": ["a skirt", "a formal skirt", "a women's skirt", "a pencil skirt"]},
        {"label": "leggings",       "prompts": ["leggings", "athletic leggings", "yoga pants", "tight leggings"]},
    ],
    "outwear": [
        {"label": "blazer",         "prompts": ["a blazer", "a suit jacket", "a formal blazer", "a business blazer"]},
        {"label": "sherwani",       "prompts": ["a sherwani", "a Pakistani sherwani", "a formal South Asian coat", "a wedding sherwani"]},
        {"label": "waistcoat",      "prompts": ["a waistcoat", "a vest", "a formal vest", "a suit waistcoat"]},
        {"label": "jacket",         "prompts": ["a casual jacket", "a denim jacket", "a leather jacket", "a casual coat"]},
        {"label": "coat",           "prompts": ["a formal overcoat", "a trench coat", "a winter coat", "a long coat"]},
        {"label": "hoodie_jacket",  "prompts": ["a zip-up hoodie", "a casual jacket hoodie", "a sports jacket"]},
        {"label": "cardigan",       "prompts": ["a cardigan", "a knit cardigan", "a casual sweater", "a woolen cardigan"]},
    ],
    "shoes": [
        {"label": "heels",          "prompts": ["high heels", "stiletto heels", "formal women's heels", "dress heels"]},
        {"label": "formal_shoes",   "prompts": ["formal dress shoes", "oxford shoes", "leather formal shoes", "men's formal shoes"]},
        {"label": "sneakers",       "prompts": ["sneakers", "running shoes", "casual sneakers", "athletic shoes", "trainers"]},
        {"label": "loafers",        "prompts": ["loafers", "slip-on shoes", "casual loafers", "smart-casual loafers"]},
        {"label": "sandals",        "prompts": ["sandals", "open-toe sandals", "casual sandals", "summer sandals"]},
        {"label": "boots",          "prompts": ["boots", "ankle boots", "formal boots", "Chelsea boots"]},
        {"label": "chappal",        "prompts": ["Pakistani chappal", "khussa", "traditional sandals", "South Asian footwear"]},
    ],
    "dress": [
        {"label": "formal_dress",   "prompts": ["a formal dress", "an evening gown", "a cocktail dress", "a business dress"]},
        {"label": "casual_dress",   "prompts": ["a casual dress", "a summer dress", "a day dress", "a simple dress"]},
        {"label": "gown",           "prompts": ["a ball gown", "a wedding gown", "a formal gown", "a maxi gown"]},
        {"label": "anarkali",       "prompts": ["an anarkali dress", "a Pakistani anarkali", "a South Asian frock dress"]},
    ],
    "jumpsuit": [
        {"label": "formal_jumpsuit", "prompts": ["a formal jumpsuit", "a tailored jumpsuit", "an office jumpsuit"]},
        {"label": "casual_jumpsuit", "prompts": ["a casual jumpsuit", "a playsuit", "a casual romper", "a utility jumpsuit"]},
    ],
}

# Formality mapping from sub-category to formality tag
# Used to suggest formality when user uploads (overrides Model 1 which cannot infer this)
SUBCATEGORY_FORMALITY_HINT: dict[str, str] = {
    "formal_shirt":    "formal",
    "kurta":           "both",
    "polo_shirt":      "casual",
    "casual_tshirt":   "casual",
    "hoodie":          "casual",
    "blouse":          "both",
    "kameez":          "both",
    "jeans":           "casual",
    "dress_trousers":  "formal",
    "shalwar":         "both",
    "chinos":          "both",
    "shorts":          "casual",
    "skirt":           "both",
    "leggings":        "casual",
    "blazer":          "formal",
    "sherwani":        "formal",
    "waistcoat":       "formal",
    "jacket":          "casual",
    "coat":            "both",
    "hoodie_jacket":   "casual",
    "cardigan":        "casual",
    "heels":           "formal",
    "formal_shoes":    "formal",
    "sneakers":        "casual",
    "loafers":         "both",
    "sandals":         "casual",
    "boots":           "both",
    "chappal":         "casual",
    "formal_dress":    "formal",
    "casual_dress":    "casual",
    "gown":            "formal",
    "anarkali":        "both",
    "formal_jumpsuit": "formal",
    "casual_jumpsuit": "casual",
}


class CLIPSubCategoryTagger:
    """
    Zero-shot sub-category classifier using HuggingFace CLIP (ViT-B/32).

    Loaded once at application startup (lazy-loads on first call to avoid
    slowing down the main TensorFlow pipeline initialization).

    Example:
        tagger = CLIPSubCategoryTagger()
        sub_cat, conf = tagger.classify("path/to/shirt.jpg", "top")
        # → ("kurta", 0.73) or ("formal_shirt", 0.88)
    """

    def __init__(self) -> None:
        self._model = None
        self._processor = None
        self._loaded = False

    def _load(self) -> None:
        """Lazy-load CLIP model. Only runs on first classify() call."""
        if self._loaded:
            return
        try:
            from transformers import CLIPProcessor, CLIPModel
            import torch
            self._model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self._processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            self._model.eval()
            self._loaded = True
            logger.info("CLIP ViT-B/32 loaded for sub-category tagging.")
        except ImportError as exc:
            raise RuntimeError(
                "CLIP sub-category tagger requires: pip install transformers torch\n"
                f"Original error: {exc}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Failed to load CLIP model: {exc}") from exc

    def classify(
        self,
        image_path: str,
        coarse_category: str,
    ) -> tuple[str, float]:
        """
        Classify an uploaded image into a fine-grained sub-category using CLIP.

        Args:
            image_path:        Path to the clothing image (same file used by Model 1).
            coarse_category:   Model 1 category: "top" | "bottom" | "outwear" |
                               "shoes" | "dress" | "jumpsuit"

        Returns:
            (sub_category_label, confidence_score) where confidence is the
            softmax probability of the winning class over the candidate set.

        Raises:
            ValueError:  If coarse_category is not in the taxonomy.
            RuntimeError: If CLIP model loading fails.
        """
        self._load()

        if coarse_category not in SUBCATEGORY_TAXONOMY:
            raise ValueError(
                f"Unknown coarse category: '{coarse_category}'. "
                f"Must be one of: {list(SUBCATEGORY_TAXONOMY.keys())}"
            )

        from PIL import Image
        import torch

        candidates = SUBCATEGORY_TAXONOMY[coarse_category]

        # Build prompt list: use the first (most descriptive) prompt per sub-category
        prompts = [cand["prompts"][0] for cand in candidates]
        labels  = [cand["label"]      for cand in candidates]

        image = Image.open(image_path).convert("RGB")
        inputs = self._processor(
            text=prompts,
            images=image,
            return_tensors="pt",
            padding=True,
        )

        with torch.no_grad():
            outputs    = self._model(**inputs)
            logits_img = outputs.logits_per_image  # shape: (1, num_candidates)
            probs      = logits_img.softmax(dim=1)[0].numpy()

        best_idx   = int(probs.argmax())
        best_label = labels[best_idx]
        best_conf  = float(probs[best_idx])

        logger.debug(
            "CLIP sub-category: image=%s category=%s → %s (%.3f)",
            image_path, coarse_category, best_label, best_conf
        )
        return best_label, best_conf

    def get_formality_hint(self, sub_category: str) -> str | None:
        """Return the suggested formality tag for a sub-category, or None if unknown."""
        return SUBCATEGORY_FORMALITY_HINT.get(sub_category)


# ─── Module-level singleton (loaded lazily) ───────────────────────────────────

_tagger_instance: CLIPSubCategoryTagger | None = None


def get_tagger() -> CLIPSubCategoryTagger:
    """Return the module-level CLIPSubCategoryTagger singleton."""
    global _tagger_instance
    if _tagger_instance is None:
        _tagger_instance = CLIPSubCategoryTagger()
    return _tagger_instance
