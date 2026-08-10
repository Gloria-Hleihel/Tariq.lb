"""Application configuration for Tariq.lb."""

from datetime import timedelta
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable safely."""
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    """Read an integer environment variable with a safe fallback."""
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    """Read a float environment variable with a safe fallback."""
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


# --- Runtime mode ------------------------------------------------------
APP_ENV = os.environ.get(
    "APP_ENV",
    os.environ.get("FLASK_ENV", "development"),
).strip().lower()
IS_PRODUCTION = APP_ENV in {"production", "prod"}

# --- Flask / Database -------------------------------------------------
def _normalize_database_url(raw_url: str | None) -> str | None:
    """Return a SQLAlchemy-compatible database URL."""
    if not raw_url:
        return None

    value = raw_url.strip()
    if value.startswith("postgres://"):
        return "postgresql://" + value[len("postgres://"):]
    return value


DATABASE_URL = _normalize_database_url(os.environ.get("DATABASE_URL"))
SQLITE_DATABASE_PATH = os.environ.get(
    "SQLITE_DATABASE_PATH",
    os.path.join(BASE_DIR, "tariq.db"),
)
SQLALCHEMY_DATABASE_URI = (
    DATABASE_URL
    or f"sqlite:///{SQLITE_DATABASE_PATH}"
)
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
AUTO_CREATE_DATABASE = _env_bool("AUTO_CREATE_DATABASE", not IS_PRODUCTION)
ALLOW_SQLITE_IN_PRODUCTION = _env_bool("ALLOW_SQLITE_IN_PRODUCTION", False)

# --- File uploads -------------------------------------------------------
UPLOAD_FOLDER = os.environ.get(
    "UPLOAD_FOLDER",
    os.path.join(BASE_DIR, "static", "uploads"),
)
ANNOTATED_FOLDER = os.environ.get(
    "ANNOTATED_FOLDER",
    os.path.join(UPLOAD_FOLDER, "annotated"),
)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_CONTENT_LENGTH = _env_int("MAX_CONTENT_LENGTH", 5 * 1024 * 1024)
MAX_IMAGE_PIXELS = _env_int("MAX_IMAGE_PIXELS", 24_000_000)
PERSISTENT_UPLOADS_CONFIRMED = _env_bool(
    "PERSISTENT_UPLOADS_CONFIRMED",
    not IS_PRODUCTION,
)

# --- Detection API ------------------------------------------------------
MODEL_PATH = os.environ.get(
    "MODEL_PATH",
    os.environ.get(
        "DETECTION_MODEL_PATH",
        os.path.join(BASE_DIR, "models", "road_damage_v3.pt"),
    ),
)
DETECTION_MODEL_PATH = MODEL_PATH
DETECTION_PRELOAD_MODEL = _env_bool("DETECTION_PRELOAD_MODEL", IS_PRODUCTION)
DETECTION_API_URL = os.environ.get(
    "DETECTION_API_URL",
    "internal",
)
DETECTION_API_TIMEOUT = _env_float("DETECTION_API_TIMEOUT", 15.0)
DETECTION_ESTIMATED_WAIT_SECONDS = _env_int(
    "DETECTION_ESTIMATED_WAIT_SECONDS",
    15,
)
DETECTION_STATUSES = ["pending", "completed"]

# --- Damage classification ----------------------------------------------
DAMAGE_TYPES = [
    "Longitudinal Crack",
    "Transverse Crack",
    "Alligator Crack",
    "Potholes",
    "None",
]

# --- Severity ------------------------------------------------------------
SEVERITY_LEVELS = ["Low", "Medium", "High", "Critical"]

SEVERITY_COLORS = {
    "Low": "green",
    "Medium": "yellow",
    "High": "orange",
    "Critical": "red",
}

# --- Report workflow -----------------------------------------------------
REPORT_STATUSES = ["pending", "reviewed", "resolved", "rejected"]
LOCATION_SOURCES = ["gps", "browser", "manual", "search"]

# --- Admin auth ----------------------------------------------------------
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")

# --- Security ------------------------------------------------------------
CSRF_ENABLED = _env_bool("CSRF_ENABLED", True)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", IS_PRODUCTION)
PREFERRED_URL_SCHEME = os.environ.get(
    "PREFERRED_URL_SCHEME",
    "https" if IS_PRODUCTION else "http",
)
PERMANENT_SESSION_LIFETIME = timedelta(
    hours=_env_int("SESSION_LIFETIME_HOURS", 2)
)
SECURITY_HEADERS_ENABLED = _env_bool("SECURITY_HEADERS_ENABLED", True)
REQUIRE_PRODUCTION_SECRETS = _env_bool(
    "REQUIRE_PRODUCTION_SECRETS",
    IS_PRODUCTION,
)
RATE_LIMIT_ENABLED = _env_bool("RATE_LIMIT_ENABLED", True)
ADMIN_LOGIN_RATE_LIMIT = _env_int("ADMIN_LOGIN_RATE_LIMIT", 8)
ADMIN_LOGIN_RATE_WINDOW_SECONDS = _env_int(
    "ADMIN_LOGIN_RATE_WINDOW_SECONDS",
    15 * 60,
)
UPLOAD_RATE_LIMIT = _env_int("UPLOAD_RATE_LIMIT", 20)
UPLOAD_RATE_WINDOW_SECONDS = _env_int(
    "UPLOAD_RATE_WINDOW_SECONDS",
    15 * 60,
)
FEEDBACK_RATE_LIMIT = _env_int("FEEDBACK_RATE_LIMIT", 6)
FEEDBACK_RATE_WINDOW_SECONDS = _env_int(
    "FEEDBACK_RATE_WINDOW_SECONDS",
    10 * 60,
)
DETECTION_RATE_LIMIT = _env_int("DETECTION_RATE_LIMIT", 30)
DETECTION_RATE_WINDOW_SECONDS = _env_int(
    "DETECTION_RATE_WINDOW_SECONDS",
    10 * 60,
)
SEARCH_RATE_LIMIT = _env_int("SEARCH_RATE_LIMIT", 120)
SEARCH_RATE_WINDOW_SECONDS = _env_int("SEARCH_RATE_WINDOW_SECONDS", 60)
TRUST_PROXY_HEADERS = _env_bool("TRUST_PROXY_HEADERS", IS_PRODUCTION)
PROXYFIX_X_FOR = _env_int("PROXYFIX_X_FOR", 1)
PROXYFIX_X_PROTO = _env_int("PROXYFIX_X_PROTO", 1)
PROXYFIX_X_HOST = _env_int("PROXYFIX_X_HOST", 1)
PROXYFIX_X_PORT = _env_int("PROXYFIX_X_PORT", 1)
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# --- Static files / compression -----------------------------------------
STATIC_CACHE_SECONDS = _env_int("STATIC_CACHE_SECONDS", 86_400)
SEND_FILE_MAX_AGE_DEFAULT = STATIC_CACHE_SECONDS
ENABLE_COMPRESSION = _env_bool("ENABLE_COMPRESSION", True)
COMPRESS_MIMETYPES = [
    "text/html",
    "text/css",
    "text/javascript",
    "application/javascript",
    "application/json",
    "image/svg+xml",
]

# --- Runtime preloading --------------------------------------------------
PRELOAD_LOCALITY_SEARCH = _env_bool("PRELOAD_LOCALITY_SEARCH", True)

# --- Map defaults (centered on Lebanon) ---------------------------------
MAP_DEFAULT_LAT = 33.85
MAP_DEFAULT_LNG = 35.86
MAP_DEFAULT_ZOOM = 9

# --- API safety limits ---------------------------------------------------
PUBLIC_REPORT_LIMIT = _env_int("PUBLIC_REPORT_LIMIT", 1000)
SEARCH_QUERY_MAX_LENGTH = _env_int("SEARCH_QUERY_MAX_LENGTH", 80)

# Inference endpoints may only read images from these project-relative roots.
DETECTION_ALLOWED_ROOTS = [
    os.path.join(BASE_DIR, "static", "uploads"),
    os.path.join(BASE_DIR, "test_images"),
]


class BaseConfig:
    """Shared configuration marker for deployment documentation/tests."""

    APP_ENV = APP_ENV
    TESTING = False
    DEBUG = False


class DevelopmentConfig(BaseConfig):
    """Local developer defaults."""

    APP_ENV = "development"
    AUTO_CREATE_DATABASE = True


class TestingConfig(BaseConfig):
    """Isolated test defaults."""

    APP_ENV = "testing"
    TESTING = True
    AUTO_CREATE_DATABASE = False
    WTF_CSRF_ENABLED = False


class ProductionConfig(BaseConfig):
    """Production mode must use explicit secrets and durable services."""

    APP_ENV = "production"
    DEBUG = False
    AUTO_CREATE_DATABASE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REQUIRE_PRODUCTION_SECRETS = True
