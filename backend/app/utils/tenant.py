"""
ERP-006 — TenantMiddleware.
Sets flask.g.db to a session on the school's SQLite database before each request.
TESTING bypass: sets g.db = db.session so all unit tests work unchanged.
"""

import logging
from flask import g, request, current_app

logger = logging.getLogger(__name__)

# Module-level engine cache: db_url -> sessionmaker
_engine_cache: dict = {}


def get_db():
    """
    Return the current request's tenant session.
    Falls back to Flask-SQLAlchemy's db.session for unauthenticated routes
    (forgot-password, reset-password) where no school context is established.
    """
    from app import db

    return getattr(g, "db", db.session)


def _get_session_factory(db_url: str):
    """Return a cached sessionmaker for db_url, creating the engine on first call."""
    if db_url not in _engine_cache:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine(db_url, connect_args={"check_same_thread": False})
        _engine_cache[db_url] = sessionmaker(bind=engine)
    return _engine_cache[db_url]


def _extract_school_slug() -> str | None:
    """
    Extract school_slug from JWT Bearer header (authenticated requests)
    or from the request body for POST /api/v1/auth/login.
    Returns None if not found.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from flask_jwt_extended import decode_token

            decoded = decode_token(auth_header[7:])
            slug = decoded.get("school_slug", "").strip().lower()
            return slug or None
        except Exception:
            pass

    # Login endpoint: get slug from request body
    if request.path == "/api/v1/auth/login" and request.method == "POST":
        data = request.get_json(silent=True) or {}
        slug = data.get("school_slug", "").strip().lower()
        return slug or None

    return None


def setup_tenant_db() -> None:
    """Flask before_request hook — establishes g.db for the current request."""
    # TESTING: reuse the main test DB session so all unit tests work unchanged
    if current_app.config.get("TESTING"):
        from app import db

        g.db = db.session
        return

    # Superadmin routes use master.db via bind key — no tenant session needed
    if request.path.startswith("/api/v1/superadmin/"):
        return

    school_slug = _extract_school_slug()
    if not school_slug:
        # Unauthenticated routes without school context (forgot/reset-password)
        # — the route handler uses db.session directly for those
        return

    from app.models.master.school import School

    school = School.query.filter_by(slug=school_slug, is_active=True).first()
    if not school:
        # Login/auth routes independently validate the slug and return 404
        return

    Session = _get_session_factory(school.db_url)
    g.db = Session()


def teardown_tenant_db(exc: Exception | None) -> None:
    """Flask teardown_request hook — closes the tenant session (non-test only)."""
    if current_app.config.get("TESTING"):
        return  # shared test session managed by Flask-SQLAlchemy
    session = g.pop("db", None)
    if session is not None:
        if exc is not None:
            session.rollback()
        session.close()
