"""
engine/color_extractor.py
Extracts the dominant color from a clothing image and returns (hue, sat, val).

Called by the Flask upload endpoint at item upload time — NOT during recommendation.
Stores the result in the database so color scoring has zero image I/O cost per request.

Dependencies: opencv-python, numpy, scikit-learn
  pip install opencv-python scikit-learn
"""

from __future__ import annotations

import numpy as np


def extract_dominant_color_hsv(image_path: str) -> tuple[float, float, float]:
    """
    Returns (hue_degrees, saturation_0_1, value_0_1) of the dominant
    non-background color in the image.

    Algorithm:
      1. Resize to 128×128 to reduce compute.
      2. k-means (k=3) on all pixels to find 3 dominant color clusters.
      3. Convert each cluster center from RGB to HSV.
      4. Return the most-saturated cluster (avoids picking white/grey background).

    Args:
        image_path: Absolute or relative path to the clothing image.

    Returns:
        (hue, saturation, value) where hue is 0–360°, sat/val are 0–1.

    Raises:
        FileNotFoundError: If the image cannot be loaded.
        ValueError: If the image has an unexpected format.
    """
    import cv2
    from sklearn.cluster import KMeans

    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not load image: {image_path}")

    img = cv2.resize(img, (128, 128))
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Flatten to a list of pixels, normalized to 0–1
    pixels = img_rgb.reshape(-1, 3).astype(np.float32) / 255.0

    # k-means to find 3 dominant color clusters
    kmeans = KMeans(n_clusters=3, n_init=3, random_state=42)
    kmeans.fit(pixels)
    centers = kmeans.cluster_centers_  # shape (3, 3) in RGB 0–1

    # Convert each cluster center to HSV
    hsv_centers: list[tuple[float, float, float]] = []
    for rgb in centers:
        rgb_uint8 = (rgb * 255).astype(np.uint8).reshape(1, 1, 3)
        hsv = cv2.cvtColor(rgb_uint8, cv2.COLOR_RGB2HSV)[0][0]
        # OpenCV HSV: H=0–179, S=0–255, V=0–255
        h_deg  = float(hsv[0]) * 2.0       # Convert to 0–360
        s_norm = float(hsv[1]) / 255.0     # Normalize to 0–1
        v_norm = float(hsv[2]) / 255.0     # Normalize to 0–1
        hsv_centers.append((h_deg, s_norm, v_norm))

    # Pick the most saturated cluster (skips white/grey background)
    best = max(hsv_centers, key=lambda c: c[1])
    return best  # (hue_degrees, saturation, value)
