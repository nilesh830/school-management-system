import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def _normalize_pg_url(url: str) -> str:
    """
    Force the psycopg (v3) driver for PostgreSQL URLs so the app works on
    Python versions that lack prebuilt psycopg2 wheels (e.g. 3.14). Accepts the
    raw 'postgres://' / 'postgresql://' strings cloud providers hand out and
    rewrites them to 'postgresql+psycopg://'. Non-PostgreSQL URLs (e.g. sqlite
    in tests) pass through unchanged.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')

    # Compute absolute paths relative to this config file so they are
    # independent of the working directory when the app is started.
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    _INSTANCE_DIR = os.path.join(_BASE_DIR, 'instance')
    SCHOOLS_DB_DIR = os.path.join(_INSTANCE_DIR, 'schools')

    # Schema-per-school on PostgreSQL: one database, master tables in the
    # public schema, each school in its own ``school_<slug>`` schema.
    # DATABASE_URL must be a PostgreSQL URL (postgresql://...). The master bind
    # points at the same database (public schema) unless overridden.
    SQLALCHEMY_DATABASE_URI = _normalize_pg_url(os.environ.get(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/sms'
    ))
    SQLALCHEMY_BINDS = {
        'master': _normalize_pg_url(os.environ.get('MASTER_DATABASE_URL', SQLALCHEMY_DATABASE_URI))
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Pin every PostgreSQL connection's base search_path to ``public`` at startup.
    # Master tables (schools, super_admins) live in public and are queried with
    # unqualified names, so the search_path must be deterministic — never left to
    # the role default or to leftover state from a pooled connection. Per-school
    # tenant queries don't rely on this: they are schema-qualified via
    # schema_translate_map. pool_pre_ping recycles stale/dropped connections.
    # pool_pre_ping: discard dead connections on checkout (Neon closes them when
    #   the serverless compute auto-suspends after idle).
    # pool_recycle: proactively drop connections older than 280s so we never hand
    #   out one that Neon is about to time out (its scale-to-zero default is ~5m).
    SQLALCHEMY_ENGINE_OPTIONS = (
        {
            "pool_pre_ping": True,
            "pool_recycle": 280,
            "connect_args": {"options": "-csearch_path=public"},
        }
        if SQLALCHEMY_DATABASE_URI.startswith("postgresql")
        else {}
    )

    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']

    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:4200').split(',')

    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@school.sms')
    MAIL_SUPPRESS_SEND = os.environ.get('MAIL_SUPPRESS_SEND', 'true').lower() == 'true'

    PASSWORD_RESET_EXPIRES_HOURS = 1
    FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:4200')

    # SMS-064 — admin dashboard KPI cache TTL in seconds (0 disables caching).
    DASHBOARD_CACHE_TTL = int(os.environ.get('DASHBOARD_CACHE_TTL', 300))


class DevelopmentConfig(Config):
    DEBUG = True
    MAIL_SUPPRESS_SEND = True  # Log instead of send in dev


class ProductionConfig(Config):
    DEBUG = False
    MAIL_SUPPRESS_SEND = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_BINDS = {'master': 'sqlite:///:memory:'}
    SQLALCHEMY_ENGINE_OPTIONS = {}  # no PostgreSQL connect args for the SQLite test DB
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    MAIL_SUPPRESS_SEND = True
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    DASHBOARD_CACHE_TTL = 0  # Disable caching in tests for deterministic results


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
