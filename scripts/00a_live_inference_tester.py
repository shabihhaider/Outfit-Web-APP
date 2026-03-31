"""
Script 00a — Live Inference Tester for Model 1
==============================================
Loads the finalized Kaggle EfficientNet model (`model1_efficientnet_best.h5`)
and visually tests it on ANY raw image you feed it.

Usage:
  1. Download `model1_efficientnet_best.h5` from Kaggle.
  2. Place it in `e:\Final\models\` (create the folder if it doesn't exist).
  3. Run: python scripts/00a_live_inference_tester.py

You can change `TEST_IMAGE_PATH` to point to any random image on your computer!
"""

import os
import sys
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
MODEL_PATH = r"e:\Final\models\model1_efficientnet_best.h5"

# Pick a random image from the raw DeepFashion2 dataset to test!
# Change this path to ANY .jpg file on your computer to test the AI yourself.
TEST_IMAGE_PATH = r"e:\Final\datasets\for_model1\deepfashion2\validation\image\000001.jpg"

CATEGORIES = ['top', 'bottom', 'outwear', 'shoes', 'dress', 'jumpsuit']
idx2cat = {idx: cat for cat, idx in enumerate(CATEGORIES)}

def preprocess_image(img_path):
    """Loads and preprocesses an image exactly like Kaggle Stage 1."""
    if not os.path.exists(img_path):
        print(f"\n❌ [ERROR] Image not found: {img_path}")
        sys.exit(1)
        
    img = tf.io.read_file(img_path)
    img = tf.image.decode_jpeg(img, channels=3)
    img = tf.image.resize(img, [256, 256])
    img = tf.cast(img, tf.float32)
    
    # Expand dims to simulate a "batch" of 1 image: shape (1, 256, 256, 3)
    img = tf.expand_dims(img, axis=0) 
    return img

def main():
    print("="*60)
    print("  Model 1 (Classifier) — Live Inference Tester")
    print("="*60)

    if not os.path.exists(MODEL_PATH):
        print(f"\n❌ [ERROR] Could not find the model file!")
        print(f"Please download 'model1_efficientnet_best.h5' from Kaggle")
        print(f"and save it to: {MODEL_PATH}")
        sys.exit(1)

    print("\n[1] Loading Neural Network Weights...")
    # Compile=False saves loading time since we are only inferencing, not training
    model = load_model(MODEL_PATH, compile=False) 
    print("    ✅ Model loaded successfully!")

    print(f"\n[2] Loading Target Image...")
    print(f"    Path: {TEST_IMAGE_PATH}")
    img_tensor = preprocess_image(TEST_IMAGE_PATH)

    print("\n[3] Running AI Prediction...")
    # The model outputs a probability array for all 6 categories
    predictions = model.predict(img_tensor, verbose=0)[0] 
    
    # Find the index with the highest probability
    best_idx = np.argmax(predictions)
    best_cat = idx2cat[best_idx]
    confidence = predictions[best_idx] * 100

    print("\n" + "="*60)
    print(f"  🧠 AI PREDICTION: 👉 {best_cat.upper()} 👈")
    print(f"  🎯 CONFIDENCE:    {confidence:.2f}%")
    print("="*60)
    
    print("\nProbability Breakdown:")
    for idx, prob in enumerate(predictions):
        cat_name = idx2cat[idx]
        print(f"  - {cat_name.ljust(10)}: {(prob * 100):.2f}%")

if __name__ == "__main__":
    main()
