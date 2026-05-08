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
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    CHROMA_OPENAI_API_KEY = os.environ.get("CHROMA_OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
    OPENAI_CHAT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-5-nano-2025-08-07")
    OPENAI_EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    CHROMA_DB_PATH = os.environ.get("CHROMA_DB_PATH", "database/chroma")
    CHROMA_COLLECTION_NAME = os.environ.get("CHROMA_COLLECTION_NAME", "aboutme_projects")
    RAG_SOURCE_DIR = os.environ.get("RAG_SOURCE_DIR", "rag_source")
    RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "4"))
    CHAT_MAX_MESSAGE_LENGTH = int(os.environ.get("CHAT_MAX_MESSAGE_LENGTH", "250"))
    CHAT_MEMORY_LIMIT = int(os.environ.get("CHAT_MEMORY_LIMIT", "10"))
    OPENAI_MAX_OUTPUT_TOKENS = int(os.environ.get("OPENAI_MAX_OUTPUT_TOKENS", "500"))
    OPENAI_TEMPERATURE = float(os.environ.get("OPENAI_TEMPERATURE", "0.1"))
    OPENAI_REASONING_EFFORT = os.environ.get("OPENAI_REASONING_EFFORT", "minimal")
    AIA_API_BASE_URL = os.environ.get("AIA_API_BASE_URL", "").strip()
