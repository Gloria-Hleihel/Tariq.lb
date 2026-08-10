"""Application configuration for Tariq.lb.

Development keeps friendly local defaults. Production is environment-driven
and must be explicitly configured before the app starts.
"""

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


def _database_uri() -> str:
    """Return a SQLAlchemy database URL that works locally and in production."""
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        return f"sqlite:///{os.path.join(BASE_DIR, 'tariq.db')}"

    # Some providers still expose the old SQLAlchemy URL prefix.
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)

    return database_url


# --- Runtime mode ------------------------------------------------------
APP_ENV = os.environ.get(
    "APP_ENV",
    os.environ.get("FLASK_ENV", "development"),
).strip().lower()
IS_PRODUCTION = APP_ENV in {"production", "prod"}

# --- Flask / Database -------------------------------------------------
SQLALCHEMY_DATABASE_URI = _database_uri()
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
AUTO_CREATE_DATABASE = _env_bool("AUTO_CREATE_DATABASE", True)
ALLOW_SQLITE_IN_PRODUCTION = _env_bool(
    "ALLOW_SQLITE_IN_PRODUCTION",
    False,
)
SQLALCHEMY_ENGINE_OPTIONS = (
    {"pool_pre_ping": True, "pool_recycle": 300}
    if SQLALCHEMY_DATABASE_URI.startswith("postgresql")
    else {}
)

# --- File uploads -------------------------------------------------------
UPLOAD_FOLDER = os.path.abspath(
    os.environ.get(
        "UPLOAD_FOLDER",
        os.path.join(BASE_DIR, "static", "uploads"),
    )
)
ANNOTATED_FOLDER = os.path.abspath(
    os.environ.get(
        "ANNOTATED_FOLDER",
        os.path.join(UPLOAD_FOLDER, "annotated"),
    )
)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_CONTENT_LENGTH = _env_int("MAX_CONTENT_LENGTH", 5 * 1024 * 1024)
MAX_IMAGE_PIXELS = _env_int("MAX_IMAGE_PIXELS", 24_000_000)
PERSISTENT_UPLOADS_CONFIRMED = _env_bool(
    "PERSISTENT_UPLOADS_CONFIRMED",
    False,
)

# --- Detection API ------------------------------------------------------
MODEL_PATH = os.environ.get(
    "MODEL_PATH",
    os.path.join(BASE_DIR, "models", "road_damage_v3.pt"),
)
DETECTION_MODEL_PATH = os.environ.get(
    "DETECTION_MODEL_PATH",
    MODEL_PATH,
)
DETECTION_PRELOAD_MODEL = _env_bool("DETECTION_PRELOAD_MODEL", IS_PRODUCTION)
DETECTION_API_URL = os.environ.get(
    "DETECTION_API_URL",
    "internal",
)
DETECTION_API_TIMEOUT = _env_float("DETECTION_API_TIMEOUT", 15.0)
DETECTION_API_TOKEN = os.environ.get("DETECTION_API_TOKEN", "")
DETECTION_API_REQUIRE_TOKEN = _env_bool(
    "DETECTION_API_REQUIRE_TOKEN",
    IS_PRODUCTION,
)
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
TRUSTED_PROXY_COUNT = _env_int("TRUSTED_PROXY_COUNT", 1)

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
    UPLOAD_FOLDER,
    os.path.join(BASE_DIR, "test_images"),
]


class BaseConfig:
    """Shared Flask config for all runtime environments."""

    APP_ENV = APP_ENV
    IS_PRODUCTION = IS_PRODUCTION
    SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI
    SQLALCHEMY_TRACK_MODIFICATIONS = SQLALCHEMY_TRACK_MODIFICATIONS
    SQLALCHEMY_ENGINE_OPTIONS = SQLALCHEMY_ENGINE_OPTIONS
    SECRET_KEY = SECRET_KEY
    AUTO_CREATE_DATABASE = AUTO_CREATE_DATABASE
    ALLOW_SQLITE_IN_PRODUCTION = ALLOW_SQLITE_IN_PRODUCTION
    UPLOAD_FOLDER = UPLOAD_FOLDER
    ANNOTATED_FOLDER = ANNOTATED_FOLDER
    ALLOWED_EXTENSIONS = ALLOWED_EXTENSIONS
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH
    MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    PERSISTENT_UPLOADS_CONFIRMED = PERSISTENT_UPLOADS_CONFIRMED
    MODEL_PATH = MODEL_PATH
    DETECTION_MODEL_PATH = DETECTION_MODEL_PATH
    DETECTION_PRELOAD_MODEL = DETECTION_PRELOAD_MODEL
    DETECTION_API_URL = DETECTION_API_URL
    DETECTION_API_TIMEOUT = DETECTION_API_TIMEOUT
    DETECTION_API_TOKEN = DETECTION_API_TOKEN
    DETECTION_API_REQUIRE_TOKEN = DETECTION_API_REQUIRE_TOKEN
    DETECTION_ESTIMATED_WAIT_SECONDS = DETECTION_ESTIMATED_WAIT_SECONDS
    DETECTION_STATUSES = DETECTION_STATUSES
    DAMAGE_TYPES = DAMAGE_TYPES
    SEVERITY_LEVELS = SEVERITY_LEVELS
    SEVERITY_COLORS = SEVERITY_COLORS
    REPORT_STATUSES = REPORT_STATUSES
    LOCATION_SOURCES = LOCATION_SOURCES
    ADMIN_USERNAME = ADMIN_USERNAME
    ADMIN_PASSWORD = ADMIN_PASSWORD
    ADMIN_PASSWORD_HASH = ADMIN_PASSWORD_HASH
    CSRF_ENABLED = CSRF_ENABLED
    SESSION_COOKIE_HTTPONLY = SESSION_COOKIE_HTTPONLY
    SESSION_COOKIE_SAMESITE = SESSION_COOKIE_SAMESITE
    SESSION_COOKIE_SECURE = SESSION_COOKIE_SECURE
    PERMANENT_SESSION_LIFETIME = PERMANENT_SESSION_LIFETIME
    SECURITY_HEADERS_ENABLED = SECURITY_HEADERS_ENABLED
    REQUIRE_PRODUCTION_SECRETS = REQUIRE_PRODUCTION_SECRETS
    RATE_LIMIT_ENABLED = RATE_LIMIT_ENABLED
    ADMIN_LOGIN_RATE_LIMIT = ADMIN_LOGIN_RATE_LIMIT
    ADMIN_LOGIN_RATE_WINDOW_SECONDS = ADMIN_LOGIN_RATE_WINDOW_SECONDS
    UPLOAD_RATE_LIMIT = UPLOAD_RATE_LIMIT
    UPLOAD_RATE_WINDOW_SECONDS = UPLOAD_RATE_WINDOW_SECONDS
    FEEDBACK_RATE_LIMIT = FEEDBACK_RATE_LIMIT
    FEEDBACK_RATE_WINDOW_SECONDS = FEEDBACK_RATE_WINDOW_SECONDS
    DETECTION_RATE_LIMIT = DETECTION_RATE_LIMIT
    DETECTION_RATE_WINDOW_SECONDS = DETECTION_RATE_WINDOW_SECONDS
    SEARCH_RATE_LIMIT = SEARCH_RATE_LIMIT
    SEARCH_RATE_WINDOW_SECONDS = SEARCH_RATE_WINDOW_SECONDS
    TRUST_PROXY_HEADERS = TRUST_PROXY_HEADERS
    TRUSTED_PROXY_COUNT = TRUSTED_PROXY_COUNT
    STATIC_CACHE_SECONDS = STATIC_CACHE_SECONDS
    SEND_FILE_MAX_AGE_DEFAULT = SEND_FILE_MAX_AGE_DEFAULT
    ENABLE_COMPRESSION = ENABLE_COMPRESSION
    COMPRESS_MIMETYPES = COMPRESS_MIMETYPES
    PRELOAD_LOCALITY_SEARCH = PRELOAD_LOCALITY_SEARCH
    MAP_DEFAULT_LAT = MAP_DEFAULT_LAT
    MAP_DEFAULT_LNG = MAP_DEFAULT_LNG
    MAP_DEFAULT_ZOOM = MAP_DEFAULT_ZOOM
    PUBLIC_REPORT_LIMIT = PUBLIC_REPORT_LIMIT
    SEARCH_QUERY_MAX_LENGTH = SEARCH_QUERY_MAX_LENGTH
    DETECTION_ALLOWED_ROOTS = DETECTION_ALLOWED_ROOTS


class DevelopmentConfig(BaseConfig):
    """Local developer configuration."""

    DEBUG = False


class TestingConfig(BaseConfig):
    """Testing configuration. Individual tests may still override values."""

    TESTING = True
    WTF_CSRF_ENABLED = False
    CSRF_ENABLED = False
    AUTO_CREATE_DATABASE = True


class ProductionConfig(BaseConfig):
    """Production configuration for public hosting."""

    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    REQUIRE_PRODUCTION_SECRETS = True
    AUTO_CREATE_DATABASE = _env_bool("AUTO_CREATE_DATABASE", False)
    DETECTION_PRELOAD_MODEL = _env_bool("DETECTION_PRELOAD_MODEL", True)


CONFIG_BY_ENV = {
    "development": DevelopmentConfig,
    "dev": DevelopmentConfig,
    "testing": TestingConfig,
    "test": TestingConfig,
    "production": ProductionConfig,
    "prod": ProductionConfig,
}


def config_object_for_environment():
    """Return the config class matching APP_ENV/FLASK_ENV."""
    return CONFIG_BY_ENV.get(APP_ENV, DevelopmentConfig)
