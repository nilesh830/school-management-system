"""
Fixtures for PostgreSQL-only integration tests (schema-per-school provisioning).

These tests run against a REAL PostgreSQL database — the same one configured via
DATABASE_URL (e.g. your Neon instance) — because they verify behaviour that does
not exist on SQLite: CREATE SCHEMA, schema_translate_map routing, and per-schema
table creation.

They are skipped automatically when DATABASE_URL is not a PostgreSQL URL, so the
default SQLite test run is unaffected.

The root conftest's autouse fixtures (clean_db, test_school) are overridden here
with no-ops so they never run their SQLite-oriented DELETE / insert logic against
the live PostgreSQL database. Each test cleans up only the artifacts it creates.
"""
import os
import pytest

from app import create_app, db as _db, bcrypt

_DB_URL = os.environ.get("DATABASE_URL", "")
_IS_PG = _DB_URL.startswith("postgres://") or _DB_URL.startswith("postgresql://")

# Skip the entire directory unless a PostgreSQL DATABASE_URL is configured.
pytestmark = pytest.mark.skipif(
    not _IS_PG,
    reason="PostgreSQL integration tests require a postgresql:// DATABASE_URL",
)


# ── Neutralise the SQLite-oriented autouse fixtures from the root conftest ──────

@pytest.fixture(autouse=True)
def clean_db():
    """Override root conftest: do NOT wipe the live PostgreSQL database."""
    yield


@pytest.fixture(autouse=True)
def test_school():
    """Override root conftest: do NOT insert the SQLite 'test' school."""
    yield


# ── PostgreSQL application fixtures ─────────────────────────────────────────────

@pytest.fixture(scope="session")
def pg_app():
    """A real app wired to the configured PostgreSQL DB (tenant routing active)."""
    app = create_app("default")
    app.config["TESTING"] = False  # ensure the tenant middleware actually routes
    with app.app_context():
        yield app


@pytest.fixture(scope="function")
def pg_client(pg_app):
    return pg_app.test_client()


@pytest.fixture
def schema_cleanup(pg_app):
    """
    Yield a list; append school slugs created during the test. On teardown each
    school's schema is dropped (CASCADE) and its master-table row removed.
    """
    slugs = []
    yield slugs
    from sqlalchemy import text
    from app.models.master.school import School

    with pg_app.app_context():
        for slug in slugs:
            schema = f"school_{slug}".replace("-", "_")
            try:
                with _db.engine.begin() as conn:
                    conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            except Exception:
                pass
            row = School.query.filter_by(slug=slug).first()
            if row:
                _db.session.delete(row)
                _db.session.commit()


@pytest.fixture
def pg_super_admin(pg_app):
    """Create a throwaway super admin in the master tables; remove it afterwards."""
    from app.models.master.super_admin import SuperAdmin

    email = "pgtest.sa@sms.com"
    with pg_app.app_context():
        sa = SuperAdmin.query.filter_by(email=email).first()
        if not sa:
            sa = SuperAdmin(
                email=email,
                password_hash=bcrypt.generate_password_hash("SA@1234567").decode("utf-8"),
                first_name="PGTest",
                last_name="SuperAdmin",
                is_active=True,
            )
            _db.session.add(sa)
            _db.session.commit()
        sa_id = sa.id
    yield sa_id
    with pg_app.app_context():
        sa = _db.session.get(SuperAdmin, sa_id)
        if sa:
            _db.session.delete(sa)
            _db.session.commit()


@pytest.fixture
def pg_sa_token(pg_client, pg_super_admin):
    resp = pg_client.post(
        "/api/v1/superadmin/auth/login",
        json={"email": "pgtest.sa@sms.com", "password": "SA@1234567"},
    )
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["data"]["access_token"]
