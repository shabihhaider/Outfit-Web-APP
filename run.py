"""
run.py
Entry point for the Flask development server.

Usage:
  python run.py
"""

import os
# Prevent OpenBLAS/ONNX from hanging on memory allocation retries (rembg fallback)
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("ONNXRUNTIME_PREFER_MEM_ARENA", "0")

from app import create_app

app = create_app("development")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
