"""
app/config.py
Configuration classes for Development, Testing, and Production environments.
"""

from __future__ import annotations

import os
from datetime import timedelta


def _mysql_uri() -> str:
    """Build MySQL URI from individual .env variables."""
    user     = os.environ.get("MYSQL_USER", "root")
    password = os.environ.get("MYSQL_PASSWORD", "")
    host     = os.environ.get("MYSQL_HOST", "localhost")
    port     = os.environ.get("MYSQL_PORT", "3306")
    database = os.environ.get("MYSQL_DATABASE", "outfit_fyp")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"


def _get_db_uri() -> str:
    """Read DATABASE_URL or build MySQL URI."""
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
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH       = 10 * 1024 * 1024   # 10 MB — Flask raises 413 on exceed
    UPLOAD_FOLDER            = "uploads"
    ALLOWED_EXTENSIONS       = {"jpg", "jpeg", "png"}
    MODEL1_PATH              = "models/model1_efficientnet_best.h5"
    MODEL2_PATH              = os.path.join("models", "model 2 Assets", "model2_compatibility_scorer.h5")
    # VTO engine tokens (Replicate = primary, HF = fallback)
    REPLICATE_API_TOKEN      = os.environ.get("REPLICATE_API_TOKEN", "")
    HF_TOKEN                 = os.environ.get("HF_TOKEN", "")
    # flask-limiter: explicit in-memory storage suppresses the startup warning.
    # Switch to Redis URI in production: "redis://localhost:6379/0"
    RATELIMIT_STORAGE_URI    = "memory://"


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


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _get_db_uri()


config = {
    "development": DevelopmentConfig,
    "testing":     TestingConfig,
    "production":  ProductionConfig,
}
