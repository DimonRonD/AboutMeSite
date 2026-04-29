import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY")
    _base_dir = os.path.dirname(os.path.abspath(__file__))
    _database_url = os.environ.get("DATABASE_URL", "sqlite:///database/site.db")
    if _database_url.startswith("sqlite:///") and not _database_url.startswith("sqlite:////"):
        _relative_path = _database_url.replace("sqlite:///", "", 1)
        _absolute_path = os.path.abspath(os.path.join(_base_dir, _relative_path))
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{_absolute_path}"
    else:
        SQLALCHEMY_DATABASE_URI = _database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = (
        os.environ.get("SQLALCHEMY_TRACK_MODIFICATIONS", "false").lower() == "true"
    )
    DEFAULT_ADMIN_USERNAME = os.environ.get("DEFAULT_ADMIN_USERNAME")
    DEFAULT_ADMIN_PASSWORD = os.environ.get("DEFAULT_ADMIN_PASSWORD")
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
    PORT = int(os.environ.get("FLASK_PORT", "5000"))
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
    LOG_FILE = os.environ.get("LOG_FILE", "logs/app.log")
    LOG_MAX_BYTES = int(os.environ.get("LOG_MAX_BYTES", "1048576"))
    LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", "5"))
    LOG_TO_CONSOLE = os.environ.get("LOG_TO_CONSOLE", "false").lower() == "true"
    PII_LOGGING_ENABLED = os.environ.get("PII_LOGGING_ENABLED", "false").lower() == "true"
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() == "true"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    REMEMBER_COOKIE_SECURE = os.environ.get("REMEMBER_COOKIE_SECURE", "true").lower() == "true"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = os.environ.get("REMEMBER_COOKIE_SAMESITE", "Lax")
    PERMANENT_SESSION_LIFETIME = timedelta(
        minutes=int(os.environ.get("PERMANENT_SESSION_MINUTES", "480"))
    )

    SECURITY_HEADERS_ENABLED = (
        os.environ.get("SECURITY_HEADERS_ENABLED", "true").lower() == "true"
    )
