import logging
import os
from pathlib import Path

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_migrate import Migrate
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge
from werkzeug.middleware.proxy_fix import ProxyFix

import config
from app.security import init_security
from models import db


migrate = Migrate()


def create_app(test_config=None):
    """Create and configure the Tariq.lb Flask application."""
    test_config = test_config or {}

    static_folder = test_config.get(
        "STATIC_FOLDER",
        os.path.join(config.BASE_DIR, "static"),
    )

    template_folder = test_config.get(
        "TEMPLATE_FOLDER",
        os.path.join(config.BASE_DIR, "templates"),
    )

    app = Flask(
        __name__,
        static_folder=static_folder,
        template_folder=template_folder,
    )

    app.config.from_object(config.config_object_for_environment())
    app.config.update(test_config)
    _configure_logging(app)
    _apply_proxy_fix(app)
    _validate_production_config(app)

    init_security(app)

    @app.context_processor
    def uploaded_media_context():
        return {"uploaded_media_url": _uploaded_media_url}

    os.makedirs(
        app.config["UPLOAD_FOLDER"],
        exist_ok=True,
    )

    os.makedirs(
        app.config["ANNOTATED_FOLDER"],
        exist_ok=True,
    )

    db.init_app(app)
    migrate.init_app(app, db)

    from app.admin.routes import admin_bp
    from app.detection.routes import detection_bp
    from app.reports import bp as reports_bp

    app.register_blueprint(reports_bp)
    app.register_blueprint(detection_bp)
    app.register_blueprint(admin_bp)

    _register_health_check(app)
    _register_error_handlers(app)

    if not app.testing:
        _preload_runtime_assets(app)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_large_upload(_error):
        message = (
            "The upload is larger than 5MB. "
            "Compress the image or choose a smaller file."
        )

        if request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": message,
                        "field": "image",
                    }
                ),
                413,
            )

        flash(message, "error")
        return redirect(url_for("reports.upload"), code=303)

    if app.config.get("AUTO_CREATE_DATABASE", True):
        with app.app_context():
            db.create_all()
            _upgrade_sqlite_schema()

    app.logger.info("Tariq.lb started in %s mode.", app.config.get("APP_ENV"))

    return app


def _uploaded_media_url(path: str | None) -> str:
    """Build a URL for an uploaded or annotated image path."""
    if not path:
        return ""

    normalized = str(path).replace("\\", "/").lstrip("/")
    if normalized.startswith("static/"):
        normalized = normalized[len("static/"):]

    if normalized.startswith("uploads/"):
        return url_for(
            "reports.uploaded_media",
            filename=normalized[len("uploads/"):],
        )

    return url_for("static", filename=normalized)


def _configure_logging(app: Flask) -> None:
    """Send production logs to stdout without exposing secrets."""
    if app.debug or app.testing:
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def _apply_proxy_fix(app: Flask) -> None:
    """Trust provider proxy headers only when explicitly configured."""
    if not app.config.get("TRUST_PROXY_HEADERS", False):
        return

    trusted_count = int(app.config.get("TRUSTED_PROXY_COUNT", 1))
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=trusted_count,
        x_proto=trusted_count,
        x_host=trusted_count,
        x_port=trusted_count,
        x_prefix=trusted_count,
    )


def _register_health_check(app: Flask) -> None:
    """Expose a lightweight health check without touching the YOLO model."""

    @app.get("/healthz")
    def healthz():
        try:
            db.session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            app.logger.exception("Health check database probe failed.")
            return jsonify({"status": "error", "database": "unavailable"}), 503

        return jsonify({"status": "ok"}), 200


def _wants_json_error() -> bool:
    """Return True when the current error response should be JSON."""
    return (
        request.path.startswith("/api/")
        or request.accept_mimetypes.best == "application/json"
    )


def _register_error_handlers(app: Flask) -> None:
    """Hide internal exceptions behind clean HTML or JSON responses."""

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        status_code = error.code or 500
        message = error.description or error.name

        if _wants_json_error():
            return jsonify({"ok": False, "error": message}), status_code

        return (
            render_template(
                "error.html",
                code=status_code,
                title=error.name,
                message=message,
            ),
            status_code,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error: Exception):
        if app.testing:
            raise error

        app.logger.exception("Unhandled application error.")

        if _wants_json_error():
            return jsonify(
                {
                    "ok": False,
                    "error": "An unexpected server error occurred.",
                }
            ), 500

        return (
            render_template(
                "error.html",
                code=500,
                title="Server error",
                message="Something went wrong. Please try again shortly.",
            ),
            500,
        )


def _preload_runtime_assets(app: Flask) -> None:
    """Warm low-risk runtime caches so first user actions feel faster."""
    if app.config.get("PRELOAD_LOCALITY_SEARCH", True):
        try:
            from app.reports.location import preload_locality_search

            indexed_count = preload_locality_search()
            app.logger.info(
                "Preloaded %s Lebanese locality search entries.",
                indexed_count,
            )
        except Exception:
            app.logger.exception(
                "Could not preload locality search data."
            )

    if app.config.get("DETECTION_PRELOAD_MODEL", False):
        try:
            from app.detection.detector import preload_model

            preload_model()
            app.logger.info("Preloaded YOLO detection model.")
        except Exception:
            app.logger.exception(
                "Could not preload YOLO detection model."
            )


def _validate_production_config(app: Flask) -> None:
    """Fail fast when production mode still uses local demo secrets."""
    if app.testing:
        return

    if not app.config.get("REQUIRE_PRODUCTION_SECRETS", False):
        return

    problems = []

    secret_key = str(app.config.get("SECRET_KEY") or "")
    if secret_key == "dev-secret-change-me" or len(secret_key) < 32:
        problems.append("set SECRET_KEY to a strong random value")

    password_hash = app.config.get("ADMIN_PASSWORD_HASH")
    if not password_hash:
        problems.append("set ADMIN_PASSWORD_HASH instead of a plaintext password")

    database_uri = str(app.config.get("SQLALCHEMY_DATABASE_URI") or "")
    if (
        database_uri.startswith("sqlite:")
        and not app.config.get("ALLOW_SQLITE_IN_PRODUCTION", False)
    ):
        problems.append(
            "set DATABASE_URL to a persistent PostgreSQL database"
        )

    if not app.config.get("PERSISTENT_UPLOADS_CONFIRMED", False):
        problems.append(
            "set UPLOAD_FOLDER to persistent storage and "
            "PERSISTENT_UPLOADS_CONFIRMED=true"
        )

    if not app.config.get("SESSION_COOKIE_SECURE", False):
        problems.append("set SESSION_COOKIE_SECURE=true behind HTTPS")

    if (
        app.config.get("DETECTION_API_REQUIRE_TOKEN", False)
        and not app.config.get("DETECTION_API_TOKEN")
    ):
        problems.append("set DETECTION_API_TOKEN for protected detection APIs")

    model_path = Path(app.config.get("DETECTION_MODEL_PATH") or "")
    if not model_path.is_absolute():
        model_path = Path(config.BASE_DIR) / model_path

    if not model_path.is_file():
        problems.append(f"ensure the YOLO model exists at {model_path}")

    if problems:
        raise RuntimeError(
            "Unsafe production configuration: "
            + "; ".join(problems)
            + "."
        )


def _upgrade_sqlite_schema() -> None:
    """Apply safe SQLite-only schema upgrades for existing local databases."""
    engine = db.engine

    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if "reports" not in inspector.get_table_names():
        return

    report_columns = {
        column["name"]
        for column in inspector.get_columns("reports")
    }

    with engine.begin() as connection:
        if "detection_status" not in report_columns:
            connection.execute(
                text(
                    "ALTER TABLE reports "
                    "ADD COLUMN detection_status VARCHAR(20) "
                    "NOT NULL DEFAULT 'pending'"
                )
            )
            connection.execute(
                text(
                    "UPDATE reports "
                    "SET detection_status = 'completed' "
                    "WHERE EXISTS ("
                    "SELECT 1 FROM detections "
                    "WHERE detections.report_id = reports.id"
                    ")"
                )
            )

        if "detection_error" not in report_columns:
            connection.execute(
                text(
                    "ALTER TABLE reports "
                    "ADD COLUMN detection_error VARCHAR(500)"
                )
            )
