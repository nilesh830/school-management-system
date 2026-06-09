import logging
import os

from flask import current_app

from app import db
from app.models.master.school import School

logger = logging.getLogger(__name__)


class SuperAdminService:

    # -------------------------------------------------------------------------
    # ERP-003 — School list
    # -------------------------------------------------------------------------

    @staticmethod
    def get_all_schools(page=1, per_page=20, search=''):
        """Paginated list of all schools from master.db."""
        query = School.query

        if search:
            query = query.filter(
                School.name.ilike(f'%{search}%')
                | School.slug.ilike(f'%{search}%')
            )

        pagination = query.order_by(School.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        return {
            'schools': [s.to_dict() for s in pagination.items],
            'meta': {
                'total': pagination.total,
                'page': pagination.page,
                'per_page': pagination.per_page,
                'pages': pagination.pages,
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
        2. Build db_url using SCHOOLS_DB_DIR from config
        3. Create School record in master.db
        4. Call _create_school_db() to stamp schema + Alembic version
        5. Call _seed_school_admin() to create first admin user in school DB
        6. Return (school_dict, None) or (None, error_dict)

        Atomic-ish: if DB creation fails the School record is rolled back.
        """
        slug = data['slug'].lower().strip()

        # 1. Uniqueness check
        if School.query.filter_by(slug=slug).first():
            return None, {'message': f"Slug '{slug}' is already taken.", 'status': 409}

        # 2. Build db_url
        schools_dir = current_app.config['SCHOOLS_DB_DIR']
        db_path = os.path.join(schools_dir, f'school_{slug}.db')
        db_url = 'sqlite:///' + db_path.replace('\\', '/')

        # 3. Persist School record
        school = School(
            name=data['name'],
            slug=slug,
            db_url=db_url,
            address=data.get('address'),
            phone=data.get('phone'),
            email=data.get('email'),
            academic_year_start_month=data.get('academic_year_start_month', 6),
            is_active=True,
        )
        db.session.add(school)

        try:
            db.session.flush()  # get school.id without committing yet

            # 4. Create school-scoped tables + stamp Alembic head
            SuperAdminService._create_school_db(db_url)

            # 5. Seed first admin user
            SuperAdminService._seed_school_admin(
                db_url=db_url,
                admin_email=data['admin_email'],
                admin_password=data['admin_password'],
                first_name=data.get('admin_first_name', 'School'),
                last_name=data.get('admin_last_name', 'Admin'),
            )

            db.session.commit()
            logger.info("Provisioned school '%s' at %s", slug, db_url)
            return school.to_dict(), None

        except Exception as exc:
            db.session.rollback()
            logger.exception("Failed to provision school '%s': %s", slug, exc)
            # Best-effort cleanup of any partially created DB file
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except OSError:
                    pass
            return None, {'message': f'Provisioning failed: {exc}', 'status': 500}

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
            return None, {'message': 'School not found', 'status': 404}

        allowed = [
            'name', 'address', 'phone', 'email',
            'logo_url', 'is_active', 'academic_year_start_month',
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
    def _create_school_db(db_url: str) -> None:
        """
        Create all school-scoped tables in a brand-new SQLite file and stamp
        the Alembic version so future migrate --upgrade commands know the DB
        is already at head.

        Only tables that do NOT carry bind_key='master' in their .info dict
        are created here — master-bound tables live in master.db.
        """
        import os
        from sqlalchemy import create_engine, text
        from alembic.config import Config as AlembicConfig
        from alembic.script import ScriptDirectory
        from app import db as _db

        engine = create_engine(db_url)

        # Filter to school-scoped tables (exclude master-bound tables)
        school_tables = [
            t for t in _db.metadata.sorted_tables
            if t.info.get('bind_key') != 'master'
        ]
        _db.metadata.create_all(engine, tables=school_tables)

        # Stamp with current Alembic head revision
        migrations_dir = os.path.abspath(
            os.path.join(current_app.root_path, '..', 'migrations')
        )
        alembic_cfg = AlembicConfig()
        alembic_cfg.set_main_option('script_location', migrations_dir)
        script = ScriptDirectory.from_config(alembic_cfg)
        head_rev = script.get_current_head()

        with engine.connect() as conn:
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS alembic_version "
                "(version_num VARCHAR(32) NOT NULL, "
                "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
            ))
            if head_rev:
                conn.execute(
                    text("INSERT OR IGNORE INTO alembic_version VALUES (:rev)"),
                    {'rev': head_rev},
                )
            conn.commit()

        engine.dispose()

    @staticmethod
    def _seed_school_admin(
        db_url: str,
        admin_email: str,
        admin_password: str,
        first_name: str = 'School',
        last_name: str = 'Admin',
    ) -> None:
        """
        Create the first admin user in the new school's DB.
        Uses a dedicated SQLAlchemy session bound to the school engine —
        completely isolated from Flask-SQLAlchemy's default session.
        admin_password is hashed immediately; the plain-text value is not
        persisted anywhere.
        """
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app import bcrypt
        from app.models.user import User

        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        try:
            if not session.query(User).filter_by(email=admin_email.lower()).first():
                user = User(
                    email=admin_email.lower().strip(),
                    first_name=first_name,
                    last_name=last_name,
                    role='admin',
                    is_active=True,
                )
                user.password_hash = bcrypt.generate_password_hash(
                    admin_password
                ).decode('utf-8')
                session.add(user)
                session.commit()
        finally:
            session.close()
            engine.dispose()
