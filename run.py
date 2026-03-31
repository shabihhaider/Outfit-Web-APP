"""
run.py
Entry point for the Flask application.

Local dev:   python run.py          → development config, debug=True, port 5000
Production:  gunicorn run:app       → production config via FLASK_CONFIG env var
"""

import os

# Prevent OpenBLAS/ONNX from hanging on memory allocation retries
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("ONNXRUNTIME_PREFER_MEM_ARENA", "0")

from app import create_app

config_name = os.environ.get("FLASK_CONFIG", "development")
app = create_app(config_name)

if __name__ == "__main__":
    debug = config_name == "development"
    port  = int(os.environ.get("PORT", 5000))
    app.run(debug=debug, host="0.0.0.0", port=port)
