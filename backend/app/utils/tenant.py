"""
ERP-006 — TenantMiddleware (PostgreSQL schema-per-school).

Each school's data lives in its own PostgreSQL schema (``school_<slug>``) inside
a single database. Master tables (``schools``, ``super_admins``) live in the
default ``public`` schema. Per request we open a session on the shared engine
and route every unqualified table to the school's schema via SQLAlchemy's
``schema_translate_map`` — this compiles ``school_demo.users`` directly into the
SQL, so it is safe with connection pooling (no ``SET search_path`` that would
leak onto a recycled connection).

TESTING bypass: sets g.db = db.session so all unit tests work unchanged.
"""

import logging
from flask import g, request, current_app

logger = logging.getLogger(__name__)


def get_db():
    """
    Return the current request's tenant session.
    Falls back to Flask-SQLAlchemy's db.session for unauthenticated routes
    (forgot-password, reset-password) where no school context is established.
    """
    from app import db

    return getattr(g, "db", db.session)


def _open_tenant_session(schema: str):
    """
    Open a Session bound to a dedicated connection from the shared engine,
    routed to ``schema`` via schema_translate_map. Returns (session, connection)
    so the caller can close both on teardown and return the connection to the
    pool.
    """
    from sqlalchemy.orm import Session
    from app import db

    connection = db.engine.connect().execution_options(
        schema_translate_map={None: schema}
    )
    session = Session(bind=connection)
    return session, connection


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

    # Superadmin routes use the master tables (public schema) — no tenant session
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

    # school.db_url stores the schema name (e.g. "school_demo")
    session, connection = _open_tenant_session(school.db_url)
    g.db = session
    g.db_connection = connection


def teardown_tenant_db(exc: Exception | None) -> None:
    """Flask teardown_request hook — closes the tenant session + connection."""
    if current_app.config.get("TESTING"):
        return  # shared test session managed by Flask-SQLAlchemy

    session = g.pop("db", None)
    connection = g.pop("db_connection", None)
    if session is not None:
        if exc is not None:
            session.rollback()
        session.close()
    # The Session does not own the connection it was bound to, so close it
    # explicitly to return it to the engine's pool.
    if connection is not None:
        connection.close()
