"""
app/config.py
Configuration classes for Development, Testing, and Production environments.
"""

from __future__ import annotations

import os
from datetime import timedelta


def _maybe_load_dotenv() -> None:
    """Best-effort .env loading for local/dev; harmless in production."""
    try:
        from dotenv import load_dotenv  # type: ignore[import]
        load_dotenv()
    except Exception:  # nosec B110 — optional dependency, safe to skip
        # Do not fail app startup if python-dotenv is unavailable.
        pass


_maybe_load_dotenv()


def _mysql_uri() -> str:
    """Build MySQL URI from individual .env variables."""
    user     = os.environ.get("MYSQL_USER", "root")
    password = os.environ.get("MYSQL_PASSWORD", "")
    host     = os.environ.get("MYSQL_HOST", "localhost")
    port     = os.environ.get("MYSQL_PORT", "3306")
    database = os.environ.get("MYSQL_DATABASE", "outfit_fyp")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


def _get_db_uri() -> str:
    """Read DATABASE_URL or build MySQL URI.

    Local override:
      USE_LOCAL_MYSQL=1 forces MySQL URI even when DATABASE_URL is set.
    """
    use_local_mysql = os.environ.get("USE_LOCAL_MYSQL", "").strip().lower() in {
        "1", "true", "yes", "on"
    }
    if use_local_mysql:
        return _mysql_uri()

    uri = os.environ.get("DATABASE_URL")
    if uri:
        # SQLAlchemy 1.4+ requires 'postgresql://' instead of 'postgres://'
        if uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)
        return uri
    return _mysql_uri()


class Config:
    SECRET_KEY               = os.environ.get("SECRET_KEY", "dev-secret-key-minimum-32-bytes!!")
    JWT_SECRET_KEY           = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-key-min-32-bytes!!")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH       = 10 * 1024 * 1024   # 10 MB — Flask raises 413 on exceed
    UPLOAD_FOLDER            = "uploads"
    ALLOWED_EXTENSIONS       = {"jpg", "jpeg", "png"}
    SUPABASE_URL             = os.environ.get("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY     = os.environ.get("SUPABASE_SERVICE_KEY", "")
    SUPABASE_BUCKET          = "wardrobe-images"
    MODEL1_PATH              = "models/model1_efficientnet_best.h5"
    MODEL2_PATH              = os.path.join("models", "model 2 Assets", "model2_compatibility_scorer.h5")
    # VTO engines (FASHN v1.5 = primary, IDM-VTON = fallback; both use HF Spaces)
    HF_TOKEN                 = os.environ.get("HF_TOKEN", "")
    HF_FASHN_SPACE_ID        = os.environ.get("HF_FASHN_SPACE_ID", "fashn-ai/fashn-vton-1.5")
    HF_VTO_SPACE_ID          = os.environ.get("HF_VTO_SPACE_ID", "yisol/IDM-VTON")
    # CORS: comma-separated allowed origins. "*" = allow all (default for dev/monolith).
    # For split deployment set e.g. "https://outfitai.com,https://www.outfitai.com"
    CORS_ORIGINS             = os.environ.get("CORS_ORIGINS", "*")
    # flask-limiter storage: set REDIS_URL (or RATELIMIT_STORAGE_URI) in production
    # to share rate-limit counters across Gunicorn workers and survive restarts.
    # Supports redis://, rediss:// (TLS), or memory:// (single-process dev only).
    # Example: REDIS_URL=rediss://default:<pw>@<host>.upstash.io:6379
    RATELIMIT_STORAGE_URI    = os.environ.get(
        "RATELIMIT_STORAGE_URI",
        os.environ.get("REDIS_URL", "memory://"),
    )


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = _get_db_uri()


class TestingConfig(Config):
    TESTING = True
    DEBUG   = True
    # Tests use SQLite in-memory — no MySQL required to run the test suite
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SKIP_CLOTHING_PHOTO_CHECK = True  # test images are synthetic 1×1 PNGs
    RATELIMIT_ENABLED = False          # rate limiting tested at integration level, not unit


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _get_db_uri()
    # Production must not expose a CORS wildcard. Default to the known
    # Vercel frontend origin; override via CORS_ORIGINS env var if needed
    # (e.g. "https://drssl.app,https://www.drssl.app").
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "https://drssl.app")


config = {
    "development": DevelopmentConfig,
    "testing":     TestingConfig,
    "production":  ProductionConfig,
}
