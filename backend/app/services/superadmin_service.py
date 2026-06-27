import logging

from flask import current_app

from app import db
from app.models.master.school import School

logger = logging.getLogger(__name__)


class SuperAdminService:

    # -------------------------------------------------------------------------
    # ERP-003 — School list
    # -------------------------------------------------------------------------

    @staticmethod
    def get_all_schools(page=1, per_page=20, search=""):
        """Paginated list of all schools from master.db."""
        query = School.query

        if search:
            query = query.filter(School.name.ilike(f"%{search}%") | School.slug.ilike(f"%{search}%"))

        pagination = query.order_by(School.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        return {
            "schools": [s.to_dict() for s in pagination.items],
            "meta": {
                "total": pagination.total,
                "page": pagination.page,
                "per_page": pagination.per_page,
                "pages": pagination.pages,
            },
        }

    # -------------------------------------------------------------------------
    # ERP-003 — Single school
    # -------------------------------------------------------------------------

    @staticmethod
    def get_school_by_id(school_id: int):
        """Return a single School dict or None."""
        school = db.session.get(School, school_id)
        return school.to_dict() if school else None

    # -------------------------------------------------------------------------
    # ERP-003 — Provision new school
    # -------------------------------------------------------------------------

    @staticmethod
    def provision_school(data: dict) -> tuple:
        """
        Create a new school:
        1. Validate slug is unique → 409 if not
        2. Derive the PostgreSQL schema name (school_<slug>)
        3. Create School record in the master tables
        4. Call _create_school_db() to create the schema + tables + Alembic stamp
        5. Call _seed_school_admin() to create first admin user in the school schema
        6. Return (school_dict, None) or (None, error_dict)

        Atomic-ish: if schema creation fails the School record is rolled back and
        any partially created schema is dropped.
        """
        slug = data["slug"].lower().strip()

        # 1. Uniqueness check
        if School.query.filter_by(slug=slug).first():
            return None, {"message": f"Slug '{slug}' is already taken.", "status": 409}

        # 2. Derive schema name — stored in School.db_url (repurposed column)
        schema = f"school_{slug}".replace("-", "_")

        # 3. Persist School record
        school = School(
            name=data["name"],
            slug=slug,
            db_url=schema,
            address=data.get("address"),
            phone=data.get("phone"),
            email=data.get("email"),
            academic_year_start_month=data.get("academic_year_start_month", 6),
            is_active=True,
        )
        db.session.add(school)

        try:
            db.session.flush()  # get school.id without committing yet

            # 4. Create the school schema + school-scoped tables + stamp Alembic head
            SuperAdminService._create_school_db(schema)

            # 5. Seed first admin user
            SuperAdminService._seed_school_admin(
                schema=schema,
                admin_email=data["admin_email"],
                admin_password=data["admin_password"],
                first_name=data.get("admin_first_name", "School"),
                last_name=data.get("admin_last_name", "Admin"),
            )

            db.session.commit()
            logger.info("Provisioned school '%s' in schema %s", slug, schema)
            return school.to_dict(), None

        except Exception as exc:
            db.session.rollback()
            logger.exception("Failed to provision school '%s': %s", slug, exc)
            # Best-effort cleanup of any partially created schema
            SuperAdminService._drop_school_schema(schema)
            return None, {"message": f"Provisioning failed: {exc}", "status": 500}

    # -------------------------------------------------------------------------
    # ERP-003 — Update school metadata
    # -------------------------------------------------------------------------

    @staticmethod
    def update_school(school_id: int, data: dict) -> tuple:
        """
        Update mutable school fields.
        Returns (school_dict, None) or (None, error_dict).
        """
        school = db.session.get(School, school_id)
        if not school:
            return None, {"message": "School not found", "status": 404}

        allowed = [
            "name",
            "address",
            "phone",
            "email",
            "logo_url",
            "is_active",
            "academic_year_start_month",
        ]
        for field in allowed:
            if field in data:
                setattr(school, field, data[field])

        db.session.commit()
        return school.to_dict(), None

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _create_school_db(schema: str) -> None:
        """
        Create the school's PostgreSQL schema, all school-scoped tables inside
        it, and stamp the Alembic version so future ``db-upgrade-all`` commands
        know the schema is already at head.

        Only tables that do NOT carry bind_key='master' in their .info dict are
        created here — master-bound tables live in the public schema.
        """
        import os
        from sqlalchemy import text
        from alembic.config import Config as AlembicConfig
        from alembic.script import ScriptDirectory
        from app import db as _db

        engine = _db.engine

        # 1. Create the schema (idempotent)
        with engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))

        # 2. Create school-scoped tables inside the schema (exclude master tables)
        school_tables = [t for t in _db.metadata.sorted_tables if t.info.get("bind_key") != "master"]
        routed = engine.connect().execution_options(schema_translate_map={None: schema})
        try:
            _db.metadata.create_all(bind=routed, tables=school_tables)
            routed.commit()
        finally:
            routed.close()

        # 3. Stamp with current Alembic head revision (inside the schema)
        migrations_dir = os.path.abspath(os.path.join(current_app.root_path, "..", "migrations"))
        alembic_cfg = AlembicConfig()
        alembic_cfg.set_main_option("script_location", migrations_dir)
        script = ScriptDirectory.from_config(alembic_cfg)
        head_rev = script.get_current_head()

        # Use schema-qualified identifiers (NOT `SET search_path`) so the
        # connection returns to the pool clean — a leaked search_path would
        # corrupt later master-table queries on the shared engine.
        with engine.begin() as conn:
            conn.execute(
                text(
                    f'CREATE TABLE IF NOT EXISTS "{schema}".alembic_version '
                    "(version_num VARCHAR(32) NOT NULL, "
                    "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
                )
            )
            if head_rev:
                conn.execute(
                    text(f'INSERT INTO "{schema}".alembic_version VALUES (:rev) ON CONFLICT DO NOTHING'),
                    {"rev": head_rev},
                )

    @staticmethod
    def _drop_school_schema(schema: str) -> None:
        """Best-effort teardown of a partially provisioned school schema."""
        from sqlalchemy import text
        from app import db as _db

        try:
            with _db.engine.begin() as conn:
                conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        except Exception:
            logger.exception("Failed to drop schema %s during cleanup", schema)

    @staticmethod
    def _seed_school_admin(
        schema: str,
        admin_email: str,
        admin_password: str,
        first_name: str = "School",
        last_name: str = "Admin",
    ) -> None:
        """
        Create the first admin user in the new school's schema.
        Uses a dedicated session routed to the school schema via
        schema_translate_map — isolated from Flask-SQLAlchemy's default session.
        admin_password is hashed immediately; the plain-text value is not
        persisted anywhere.
        """
        from sqlalchemy.orm import Session
        from app import bcrypt, db as _db
        from app.models.user import User

        connection = _db.engine.connect().execution_options(
            schema_translate_map={None: schema}
        )
        session = Session(bind=connection)
        try:
            if not session.query(User).filter_by(email=admin_email.lower()).first():
                user = User(
                    email=admin_email.lower().strip(),
                    first_name=first_name,
                    last_name=last_name,
                    role="admin",
                    is_active=True,
                )
                user.password_hash = bcrypt.generate_password_hash(admin_password).decode("utf-8")
                session.add(user)
                session.commit()
        finally:
            session.close()
            connection.close()
