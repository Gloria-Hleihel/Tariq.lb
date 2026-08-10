import logging
import os

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_migrate import Migrate
from sqlalchemy import inspect, text
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import RequestEntityTooLarge
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

    app.config.from_object(config)
    app.config.update(test_config)
    _validate_production_config(app)

    _configure_logging(app)

    if app.config.get("TRUST_PROXY_HEADERS"):
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=int(app.config.get("PROXYFIX_X_FOR", 1)),
            x_proto=int(app.config.get("PROXYFIX_X_PROTO", 1)),
            x_host=int(app.config.get("PROXYFIX_X_HOST", 1)),
            x_port=int(app.config.get("PROXYFIX_X_PORT", 1)),
        )

    init_security(app)

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

    @app.get("/healthz")
    def healthz():
        """Lightweight production health check; never runs YOLO inference."""
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            app.logger.exception("Health check database probe failed.")
            return jsonify({"status": "error", "database": "unavailable"}), 503

        return jsonify({"status": "ok", "database": "ok"}), 200

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(405)
    @app.errorhandler(429)
    def handle_http_error(error):
        return _render_error_response(error)

    @app.errorhandler(500)
    def handle_internal_server_error(error):
        app.logger.error("Unhandled server error: %s", error)
        return _render_error_response(error, generic_message=True)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        if isinstance(error, HTTPException):
            return _render_error_response(error)

        app.logger.exception("Unhandled application exception.")
        return _render_error_response(
            HTTPException(description="Internal server error"),
            status_code=500,
            generic_message=True,
        )

    if app.config.get("AUTO_CREATE_DATABASE", True):
        with app.app_context():
            db.create_all()
            _upgrade_sqlite_schema()

    return app


def _configure_logging(app: Flask) -> None:
    """Configure clear production logs without exposing secrets."""
    level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )

    app.logger.setLevel(level)
    app.logger.info("Starting Tariq.lb in %s mode.", app.config.get("APP_ENV"))


def _wants_json_error() -> bool:
    best_match = request.accept_mimetypes.best_match(
        ["application/json", "text/html"]
    )
    return request.path.startswith("/api/") or best_match == "application/json"


def _render_error_response(
    error,
    status_code: int | None = None,
    generic_message: bool = False,
):
    """Return clean HTML or JSON errors without stack traces."""
    code = status_code or getattr(error, "code", 500) or 500
    name = getattr(error, "name", "Server Error")

    if generic_message or code >= 500:
        message = "Something went wrong. Please try again later."
    else:
        message = getattr(error, "description", None) or name

    if _wants_json_error():
        return (
            jsonify(
                {
                    "success": False,
                    "error": {
                        "code": code,
                        "message": message,
                    },
                }
            ),
            code,
        )

    return (
        render_template(
            "error.html",
            status_code=code,
            title=name,
            message=message,
        ),
        code,
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

    if app.config.get("SECRET_KEY") == "dev-secret-change-me":
        problems.append("set SECRET_KEY to a strong random value")

    password_hash = app.config.get("ADMIN_PASSWORD_HASH")
    if not password_hash:
        problems.append("set ADMIN_PASSWORD_HASH; plain passwords are not allowed")

    database_uri = str(app.config.get("SQLALCHEMY_DATABASE_URI") or "")
    if (
        database_uri.startswith("sqlite:///")
        and not app.config.get("ALLOW_SQLITE_IN_PRODUCTION", False)
    ):
        problems.append("set DATABASE_URL for PostgreSQL production storage")

    if (
        not app.config.get("PERSISTENT_UPLOADS_CONFIRMED", False)
        and not app.config.get("ALLOW_EPHEMERAL_UPLOADS", False)
    ):
        problems.append(
            "confirm persistent upload storage or explicitly allow ephemeral demo uploads"
        )

    if not app.config.get("SESSION_COOKIE_SECURE", False):
        problems.append("enable SESSION_COOKIE_SECURE for HTTPS")

    model_path = app.config.get("DETECTION_MODEL_PATH")
    if model_path:
        resolved_model_path = (
            model_path
            if os.path.isabs(model_path)
            else os.path.join(config.BASE_DIR, model_path)
        )
        if not os.path.isfile(resolved_model_path):
            problems.append(
                f"ensure the YOLO model exists at {resolved_model_path}"
            )

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
