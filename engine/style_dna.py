"""
engine/style_dna.py
Rule-based Style DNA computation from a user's wardrobe.

Derives a persona label and matching vibe slug entirely from the existing
wardrobe data (category distribution, colour tones, formality mix).
No ML inference — runs in < 1ms per user.
"""

from __future__ import annotations

from dataclasses import dataclass


# ── Persona lookup table ───────────────────────────────────────────────────────
# Key: (dominant_formality, dominant_tone, dominant_category) → (persona_name, vibe_slug, tagline)
_PERSONAS: dict[tuple, tuple[str, str, str]] = {
    ("formal",  "neutral", "top")    : ("Old Money",          "quiet-luxury",       "Your wardrobe speaks quietly but says everything."),
    ("formal",  "dark",    "top")    : ("Power Dresser",       "business-casual",    "Precision tailoring, zero compromise."),
    ("formal",  "bright",  "top")    : ("Statement Formal",    "party-glam",         "You make every entrance count."),
    ("formal",  "rich",    "top")    : ("Mughal Luxe",         "mughal-luxe",        "Heritage richness in every thread."),
    ("formal",  "neutral", "dress")  : ("Elegant",             "quiet-luxury",       "Effortless polish is your signature."),
    ("casual",  "neutral", "top")    : ("Minimalist",          "minimalist",         "Less noise, more signal."),
    ("casual",  "dark",    "top")    : ("Dark Academia",       "dark-academia",      "Knowledge is the ultimate accessory."),
    ("casual",  "bright",  "top")    : ("Streetwear Explorer", "streetwear",         "The street is your runway."),
    ("casual",  "earthy",  "top")    : ("Boho",                "boho",               "Free-spirited and beautifully unstructured."),
    ("casual",  "neutral", "bottom") : ("Smart Casual",        "smart-casual",       "Relaxed but never underdressed."),
    ("casual",  "bright",  "dress")  : ("Cottagecore",         "cottagecore",        "Soft, romantic, and completely your own."),
    ("casual",  "earthy",  "bottom") : ("Gorpcore",            "gorpcore",           "Outdoors-ready wherever you go."),
    ("both",    "neutral", "top")    : ("Versatile Classic",   "smart-casual",       "You dress for every room."),
    ("both",    "bright",  "top")    : ("Y2K Revival",         "y2k",                "Nostalgic energy with modern edge."),
    # South Asian overrides (checked when dominant tone is rich/earthy + formal dominant)
    ("desi",    "bright",  "top")    : ("Desi Chic",           "desi-casual",        "Colour and culture worn with pride."),
    ("desi",    "rich",    "top")    : ("Mughal Luxe",         "mughal-luxe",        "Heritage richness in every thread."),
    ("desi",    "neutral", "top")    : ("Modern Fusion",       "fusion-east-west",   "East meets West in perfect harmony."),
    ("desi",    "earthy",  "top")    : ("Lawn Chic",           "lawn-chic",          "Effortless summer elegance."),
}

_FALLBACK = ("Style Explorer", "smart-casual", "Your style is uniquely your own.")


# ── Colour tone classifier ─────────────────────────────────────────────────────

def _tone(hue: float, sat: float, val: float) -> str:
    """Map HSV to a coarse tone bucket used in persona lookup."""
    if sat < 0.15:
        return "neutral"          # grey, white, black
    if val < 0.30:
        return "dark"
    if 20 <= hue <= 50:
        return "earthy"           # brown, tan, olive, khaki
    if (hue < 20 or hue > 340) and sat > 0.35:
        return "rich"             # deep red, maroon, burgundy — common in South Asian formal
    if sat > 0.55 and val > 0.55:
        return "bright"
    return "neutral"


# ── Public API ────────────────────────────────────────────────────────────────

@dataclass
class StyleDNA:
    persona_name:    str
    vibe_slug:       str
    tagline:         str
    dominant_tones:  list[str]   # top-3 tone buckets
    formality_mix:   dict        # e.g. {"casual": 0.60, "formal": 0.30, "both": 0.10}
    category_mix:    dict        # e.g. {"top": 0.40, "bottom": 0.35, "shoes": 0.25}
    total_items:     int

    def to_dict(self) -> dict:
        return {
            "persona_name":   self.persona_name,
            "vibe_slug":      self.vibe_slug,
            "tagline":        self.tagline,
            "dominant_tones": self.dominant_tones,
            "formality_mix":  self.formality_mix,
            "category_mix":   self.category_mix,
            "total_items":    self.total_items,
        }


def compute_style_dna(wardrobe_items: list) -> StyleDNA:
    """
    Derive a Style DNA persona from a user's wardrobe items.

    Parameters
    ----------
    wardrobe_items : list of WardrobeItemDB
        The user's wardrobe (any size, including empty).

    Returns
    -------
    StyleDNA dataclass with persona_name, vibe_slug, tagline, and stats.
    """
    if not wardrobe_items:
        return StyleDNA(
            persona_name=_FALLBACK[0],
            vibe_slug=_FALLBACK[1],
            tagline=_FALLBACK[2],
            dominant_tones=[],
            formality_mix={},
            category_mix={},
            total_items=0,
        )

    n = len(wardrobe_items)

    # ── Formality distribution ─────────────────────────────────────────────────
    form_counts: dict[str, int] = {}
    for item in wardrobe_items:
        f = item.formality or "both"
        form_counts[f] = form_counts.get(f, 0) + 1
    formality_mix = {k: round(v / n, 2) for k, v in form_counts.items()}
    dominant_formality = max(form_counts, key=form_counts.get)

    # ── Category distribution ──────────────────────────────────────────────────
    cat_counts: dict[str, int] = {}
    for item in wardrobe_items:
        c = item.category or "top"
        cat_counts[c] = cat_counts.get(c, 0) + 1
    category_mix = {k: round(v / n, 2) for k, v in cat_counts.items()}
    dominant_category = max(cat_counts, key=cat_counts.get)

    # ── Colour tone distribution ───────────────────────────────────────────────
    tone_counts: dict[str, int] = {}
    for item in wardrobe_items:
        if item.color_hue is not None:
            t = _tone(item.color_hue, item.color_sat or 0.0, item.color_val or 0.0)
            tone_counts[t] = tone_counts.get(t, 0) + 1
    dominant_tone = max(tone_counts, key=tone_counts.get) if tone_counts else "neutral"
    dominant_tones = sorted(tone_counts, key=tone_counts.get, reverse=True)[:3]

    # ── South Asian override ───────────────────────────────────────────────────
    # Desi dominant: if rich/earthy tones make up > 30% of items AND formal is dominant
    desi_items = tone_counts.get("rich", 0) + tone_counts.get("earthy", 0)
    is_desi_dominant = (desi_items / n >= 0.30) and (dominant_formality == "formal")
    if is_desi_dominant:
        dominant_formality = "desi"

    # ── Persona lookup ─────────────────────────────────────────────────────────
    key = (dominant_formality, dominant_tone, dominant_category)
    persona_name, vibe_slug, tagline = _PERSONAS.get(key, _FALLBACK)

    return StyleDNA(
        persona_name=persona_name,
        vibe_slug=vibe_slug,
        tagline=tagline,
        dominant_tones=dominant_tones,
        formality_mix=formality_mix,
        category_mix=category_mix,
        total_items=n,
    )


def compute_style_compatibility(
    user_a_items: list,
    user_b_items: list,
) -> float | None:
    """
    Compute a 0.0–1.0 style compatibility score between two users' wardrobes.

    Uses mean-of-best-match cosine similarity on L2-normalised embeddings
    (top-3 most recent items per category to limit compute).

    Returns None if either wardrobe is empty or has no usable embeddings.
    """
    import json
    import numpy as np

    if not user_a_items or not user_b_items:
        return None

    def _top_embeddings(items: list, max_per_cat: int = 3) -> np.ndarray:
        cat_seen: dict[str, int] = {}
        vecs: list[np.ndarray] = []
        for item in sorted(items, key=lambda x: x.created_at, reverse=True):
            cat = item.category
            cat_seen[cat] = cat_seen.get(cat, 0) + 1
            if cat_seen[cat] > max_per_cat:
                continue
            if item.embedding is None:
                continue
            try:
                emb = np.array(json.loads(item.embedding), dtype=np.float32)
            except (json.JSONDecodeError, ValueError):
                continue
            norm = np.linalg.norm(emb)
            if norm > 1e-9:
                vecs.append(emb / norm)
        return np.stack(vecs) if vecs else np.empty((0, 1280), dtype=np.float32)

    emb_a = _top_embeddings(user_a_items)
    emb_b = _top_embeddings(user_b_items)

    if emb_a.shape[0] == 0 or emb_b.shape[0] == 0:
        return None

    # Cross-similarity matrix (A × B) → mean of each row's max
    sim_matrix  = emb_a @ emb_b.T          # (len_a, len_b)
    best_matches = sim_matrix.max(axis=1)   # (len_a,)
    score = float(best_matches.mean())
    return round(min(max(score, 0.0), 1.0), 2)
