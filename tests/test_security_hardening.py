import re

import pytest

from app import create_app
from app.security import reset_rate_limits
from models import Report, db


@pytest.fixture()
def app(tmp_path):
    reset_rate_limits()
    static_folder = tmp_path / "static"
    upload_folder = static_folder / "uploads"
    annotated_folder = upload_folder / "annotated"

    flask_app = create_app(
        {
            "TESTING": False,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "STATIC_FOLDER": str(static_folder),
            "UPLOAD_FOLDER": str(upload_folder),
            "ANNOTATED_FOLDER": str(annotated_folder),
            "ENABLE_COMPRESSION": False,
        }
    )

    with flask_app.app_context():
        db.create_all()

    yield flask_app

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def _csrf_from_response(response):
    match = re.search(
        rb'name="_csrf_token" value="([^"]+)"',
        response.data,
    )
    assert match is not None
    return match.group(1).decode("utf-8")


def test_security_headers_are_sent(client):
    response = client.get("/")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert "https://server.arcgisonline.com" in response.headers["Content-Security-Policy"]
    assert "geolocation=(self)" in response.headers["Permissions-Policy"]


def test_hsts_is_sent_for_https_requests(client):
    response = client.get("/", base_url="https://tariq.example")

    assert "Strict-Transport-Security" in response.headers


def test_healthz_checks_database(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_html_404_uses_clean_error_page(client):
    response = client.get("/missing-page")

    assert response.status_code == 404
    assert b"Tariq.lb" in response.data
    assert b"Traceback" not in response.data


def test_api_404_uses_json_error(client):
    response = client.get(
        "/api/missing-page",
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 404
    assert response.get_json()["success"] is False


def test_admin_login_rejects_missing_csrf_token(client):
    response = client.post(
        "/admin/login",
        data={"username": "admin", "password": "changeme"},
    )

    assert response.status_code == 400


def test_admin_login_accepts_valid_csrf_token(client):
    login_page = client.get("/admin/login")
    token = _csrf_from_response(login_page)

    response = client.post(
        "/admin/login",
        data={
            "username": "admin",
            "password": "changeme",
            "_csrf_token": token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/dashboard")


def test_admin_login_rate_limit_blocks_repeated_attempts(tmp_path):
    reset_rate_limits()
    flask_app = create_app(
        {
            "TESTING": False,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "STATIC_FOLDER": str(tmp_path / "static"),
            "UPLOAD_FOLDER": str(tmp_path / "static" / "uploads"),
            "ANNOTATED_FOLDER": str(
                tmp_path / "static" / "uploads" / "annotated"
            ),
            "ENABLE_COMPRESSION": False,
            "ADMIN_LOGIN_RATE_LIMIT": 1,
            "ADMIN_LOGIN_RATE_WINDOW_SECONDS": 60,
        }
    )

    with flask_app.app_context():
        db.create_all()

    test_client = flask_app.test_client()
    token = _csrf_from_response(test_client.get("/admin/login"))

    first_response = test_client.post(
        "/admin/login",
        data={
            "username": "admin",
            "password": "wrong",
            "_csrf_token": token,
        },
    )
    second_response = test_client.post(
        "/admin/login",
        data={
            "username": "admin",
            "password": "wrong",
            "_csrf_token": token,
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert 1 <= int(second_response.headers["Retry-After"]) <= 60

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()
    reset_rate_limits()
    reset_rate_limits()


def test_production_config_rejects_default_secrets(tmp_path):
    with pytest.raises(RuntimeError, match="Unsafe production configuration"):
        create_app(
            {
                "TESTING": False,
                "REQUIRE_PRODUCTION_SECRETS": True,
                "SECRET_KEY": "dev-secret-change-me",
                "ADMIN_PASSWORD": "changeme",
                "ADMIN_PASSWORD_HASH": None,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "STATIC_FOLDER": str(tmp_path / "static"),
                "UPLOAD_FOLDER": str(tmp_path / "static" / "uploads"),
                "ANNOTATED_FOLDER": str(
                    tmp_path / "static" / "uploads" / "annotated"
                ),
                "ENABLE_COMPRESSION": False,
                "AUTO_CREATE_DATABASE": False,
            }
        )


def test_production_config_rejects_plain_admin_password(tmp_path):
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"fake model")

    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD_HASH"):
        create_app(
            {
                "TESTING": False,
                "REQUIRE_PRODUCTION_SECRETS": True,
                "SECRET_KEY": "test-secret-value-that-is-long-enough",
                "ADMIN_PASSWORD": "not-default",
                "ADMIN_PASSWORD_HASH": None,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "ALLOW_SQLITE_IN_PRODUCTION": True,
                "PERSISTENT_UPLOADS_CONFIRMED": True,
                "SESSION_COOKIE_SECURE": True,
                "DETECTION_MODEL_PATH": str(model_path),
                "STATIC_FOLDER": str(tmp_path / "static"),
                "UPLOAD_FOLDER": str(tmp_path / "static" / "uploads"),
                "ANNOTATED_FOLDER": str(
                    tmp_path / "static" / "uploads" / "annotated"
                ),
                "ENABLE_COMPRESSION": False,
                "AUTO_CREATE_DATABASE": False,
            }
        )


def test_production_config_accepts_required_runtime_settings(tmp_path):
    model_path = tmp_path / "model.pt"
    model_path.write_bytes(b"fake model")

    flask_app = create_app(
        {
            "TESTING": False,
            "REQUIRE_PRODUCTION_SECRETS": True,
            "SECRET_KEY": "test-secret-value-that-is-long-enough",
            "ADMIN_PASSWORD_HASH": "scrypt:32768:8:1$fake$fake",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "ALLOW_SQLITE_IN_PRODUCTION": True,
            "PERSISTENT_UPLOADS_CONFIRMED": True,
            "SESSION_COOKIE_SECURE": True,
            "DETECTION_MODEL_PATH": str(model_path),
            "STATIC_FOLDER": str(tmp_path / "static"),
            "UPLOAD_FOLDER": str(tmp_path / "static" / "uploads"),
            "ANNOTATED_FOLDER": str(
                tmp_path / "static" / "uploads" / "annotated"
            ),
            "ENABLE_COMPRESSION": False,
            "AUTO_CREATE_DATABASE": False,
        }
    )

    assert flask_app.config["SESSION_COOKIE_SECURE"] is True


def test_retry_detection_requires_csrf_token(client, app):
    with app.app_context():
        report = Report(
            image_path="uploads/missing.jpg",
            lat=33.89,
            lng=35.50,
            location_source="manual",
            status="pending",
            detection_status="pending",
        )
        db.session.add(report)
        db.session.commit()
        report_id = report.id

    response = client.post(f"/reports/{report_id}/retry-detection")

    assert response.status_code == 400


def test_retry_detection_form_includes_csrf_token(client, app):
    with app.app_context():
        report = Report(
            image_path="uploads/missing.jpg",
            lat=33.89,
            lng=35.50,
            location_source="manual",
            status="pending",
            detection_status="pending",
        )
        db.session.add(report)
        db.session.commit()
        report_id = report.id

    response = client.get(f"/reports/{report_id}")

    assert response.status_code == 200
    assert b'name="_csrf_token"' in response.data


def test_runtime_preloader_warms_enabled_caches(tmp_path, monkeypatch):
    from app import _preload_runtime_assets
    from app.detection import detector as detector_module
    from app.reports import location as location_module

    calls = []

    monkeypatch.setattr(
        location_module,
        "preload_locality_search",
        lambda: calls.append("localities") or 12,
    )
    monkeypatch.setattr(
        detector_module,
        "preload_model",
        lambda: calls.append("model") or True,
    )

    flask_app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "STATIC_FOLDER": str(tmp_path / "static"),
            "UPLOAD_FOLDER": str(tmp_path / "static" / "uploads"),
            "ANNOTATED_FOLDER": str(
                tmp_path / "static" / "uploads" / "annotated"
            ),
            "AUTO_CREATE_DATABASE": False,
            "PRELOAD_LOCALITY_SEARCH": True,
            "DETECTION_PRELOAD_MODEL": True,
        }
    )

    _preload_runtime_assets(flask_app)

    assert calls == ["localities", "model"]
