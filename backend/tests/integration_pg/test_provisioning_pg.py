"""
PostgreSQL schema-per-school provisioning tests (ERP-003).

Run against a real PostgreSQL DB. Each test provisions a school into its own
``school_<slug>`` schema and asserts on PostgreSQL catalogs rather than files.
"""
from sqlalchemy import text

from app import db as _db, bcrypt


def _schema_for(slug: str) -> str:
    return f"school_{slug}".replace("-", "_")


def _provision_payload(**overrides):
    base = {
        "name": "Sunrise Academy",
        "slug": "pgtest-sunrise",
        "admin_email": "admin@pgtest-sunrise.sms",
        "admin_password": "Sunrise@123",
        "address": "123 Main St",
        "phone": "+91-9900000001",
        "academic_year_start_month": 6,
    }
    base.update(overrides)
    return base


class TestProvisionSchoolPg:

    def test_provision_creates_schema_with_tables(self, pg_client, pg_sa_token, pg_app, schema_cleanup):
        slug = "pgtest-create"
        schema_cleanup.append(slug)

        resp = pg_client.post(
            "/api/v1/superadmin/schools/",
            json=_provision_payload(slug=slug, name="PG Create School",
                                    admin_email="admin@pgtest-create.sms"),
            headers={"Authorization": f"Bearer {pg_sa_token}"},
        )
        assert resp.status_code == 201, resp.get_json()
        data = resp.get_json()["data"]
        assert data["slug"] == slug
        # Sensitive provisioning fields must NOT leak in the response
        assert "admin_email" not in data
        assert "admin_password" not in data

        with pg_app.app_context():
            insp = _db.inspect(_db.engine)
            schema = _schema_for(slug)
            # The school schema exists
            assert schema in insp.get_schema_names()
            # It contains the school-scoped tables (not the master ones)
            tables = set(insp.get_table_names(schema=schema))
            assert "users" in tables
            assert "students" in tables
            assert "alembic_version" in tables
            assert "schools" not in tables  # master tables stay in public

            # alembic_version is stamped at head (schema-qualified — no SET search_path)
            with _db.engine.connect() as conn:
                rev = conn.execute(
                    text(f'SELECT version_num FROM "{schema}".alembic_version')
                ).scalar()
                assert rev is not None

    def test_provision_seeds_admin_inside_schema(self, pg_client, pg_sa_token, pg_app, schema_cleanup):
        slug = "pgtest-seed"
        schema_cleanup.append(slug)

        resp = pg_client.post(
            "/api/v1/superadmin/schools/",
            json=_provision_payload(
                slug=slug, name="PG Seed School",
                admin_email="first@pgtest-seed.sms", admin_password="SeedAdmin@1",
            ),
            headers={"Authorization": f"Bearer {pg_sa_token}"},
        )
        assert resp.status_code == 201, resp.get_json()

        with pg_app.app_context():
            schema = _schema_for(slug)
            with _db.engine.connect() as conn:
                row = conn.execute(
                    text(f'SELECT email, role, is_active, password_hash FROM "{schema}".users')
                ).fetchone()
                assert row is not None, "Admin user not seeded inside the school schema"
                assert row.email == "first@pgtest-seed.sms"
                assert row.role == "admin"
                assert row.is_active is True
                # Password stored as a bcrypt hash, never plaintext
                assert row.password_hash != "SeedAdmin@1"
                assert bcrypt.check_password_hash(row.password_hash, "SeedAdmin@1")

                # The admin must NOT exist in public (data isolation)
                exists_users = conn.execute(text(
                    "SELECT to_regclass('public.users')"
                )).scalar()
                assert exists_users is None, "school 'users' table must not exist in public"

    def test_provision_duplicate_slug_rejected(self, pg_client, pg_sa_token, pg_app, schema_cleanup):
        slug = "pgtest-dup"
        schema_cleanup.append(slug)

        r1 = pg_client.post(
            "/api/v1/superadmin/schools/",
            json=_provision_payload(slug=slug, name="First",
                                    admin_email="a@pgtest-dup.sms"),
            headers={"Authorization": f"Bearer {pg_sa_token}"},
        )
        assert r1.status_code == 201, r1.get_json()

        r2 = pg_client.post(
            "/api/v1/superadmin/schools/",
            json=_provision_payload(slug=slug, name="Second",
                                    admin_email="b@pgtest-dup.sms"),
            headers={"Authorization": f"Bearer {pg_sa_token}"},
        )
        assert r2.status_code == 409, r2.get_json()
        assert r2.get_json()["success"] is False

    def test_provisioned_admin_can_log_in_and_query_tenant(self, pg_client, pg_sa_token, schema_cleanup):
        """End-to-end: provision → log in with school slug → tenant query routes
        into the school's schema."""
        slug = "pgtest-login"
        schema_cleanup.append(slug)

        resp = pg_client.post(
            "/api/v1/superadmin/schools/",
            json=_provision_payload(slug=slug, name="PG Login School",
                                    admin_email="admin@pgtest-login.sms",
                                    admin_password="Login@1234"),
            headers={"Authorization": f"Bearer {pg_sa_token}"},
        )
        assert resp.status_code == 201, resp.get_json()

        login = pg_client.post(
            "/api/v1/auth/login",
            json={"email": "admin@pgtest-login.sms", "password": "Login@1234", "school_slug": slug},
        )
        assert login.status_code == 200, login.get_json()
        token = login.get_json()["data"]["access_token"]

        # A tenant-table query must succeed (routes into the school schema)
        listing = pg_client.get(
            "/api/v1/students?per_page=1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert listing.status_code == 200, listing.get_json()
        assert listing.get_json()["success"] is True
