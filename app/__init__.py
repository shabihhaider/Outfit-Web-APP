"""
app/__init__.py
Flask application factory — create_app().

The ML pipeline is loaded ONCE here and stored on app.pipeline.
It is skipped during `flask db migrate/init` CLI commands to avoid loading
TensorFlow when all that's needed is schema introspection.
"""

from __future__ import annotations

import sys

from flask import Flask

from app.config import config


def create_app(config_name: str = "development") -> Flask:
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config[config_name])

    # ── Init extensions ───────────────────────────────────────────────────────
    from app.extensions import db, migrate, jwt, bcrypt, cors, limiter

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app)
    limiter.init_app(app)

    # ── Load ML pipeline once at startup ──────────────────────────────────────
    # Guard: skip during `flask db` CLI commands and pytest (TESTING=True).
    # Wrapped in try/except so the server still starts when TensorFlow is not
    # installed (e.g. dev machine without GPU / Python 3.14 incompatibility).
    # Routes that need the pipeline will return 503 if app.pipeline is None.
    import logging as _logging
    _log = _logging.getLogger(__name__)

    if "db" not in sys.argv and not app.config.get("TESTING", False):
        try:
            from engine.pipeline import RecommendationPipeline
            app.pipeline = RecommendationPipeline(  # type: ignore[attr-defined]
                model1_path=app.config["MODEL1_PATH"],
                model2_path=app.config["MODEL2_PATH"],
            )
        except Exception as exc:
            _log.warning("ML pipeline not loaded (%s). Recommendation routes will return 503.", exc)
            app.pipeline = None  # type: ignore[attr-defined]
    else:
        app.pipeline = None  # type: ignore[attr-defined]

    # ── Register blueprints ───────────────────────────────────────────────────
    from app.auth.routes import auth_bp
    from app.wardrobe.routes import wardrobe_bp, uploads_bp
    from app.recommendations.routes import recommendations_bp
    from app.outfits.routes import outfits_bp
    from app.calendar.routes import calendar_bp
    from app.vto.routes import vto_bp
    from app.social.routes import social_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(wardrobe_bp, url_prefix="/wardrobe")
    app.register_blueprint(uploads_bp)           # no prefix — serves /uploads/<filename>
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(outfits_bp, url_prefix="/outfits")
    app.register_blueprint(calendar_bp, url_prefix="/calendar")
    app.register_blueprint(vto_bp, url_prefix="/vto")
    app.register_blueprint(social_bp, url_prefix="/social")

    # ── Health endpoint ───────────────────────────────────────────────────────
    @app.get("/health")
    def health():
        from flask import jsonify
        return jsonify({"status": "ok"}), 200

    # ── Register error handlers ───────────────────────────────────────────────
    from app.errors import register_error_handlers
    register_error_handlers(app)

    return app
