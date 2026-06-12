"""
Tests for ERP-003 — School Provisioning API.

Endpoints under test:
  GET    /api/v1/superadmin/schools/
  POST   /api/v1/superadmin/schools/
  GET    /api/v1/superadmin/schools/<id>
  PATCH  /api/v1/superadmin/schools/<id>
"""
import os
import pytest
from sqlalchemy import create_engine, inspect, text

from app import db as _db, bcrypt


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def super_admin(app):
    """Create a super admin in master.db and tear it down afterwards."""
    with app.app_context():
        from app.models.master.super_admin import SuperAdmin
        sa = SuperAdmin(
            email='erp003.sa@sms.com',
            password_hash=bcrypt.generate_password_hash('SA@1234567').decode('utf-8'),
            first_name='ERP003',
            last_name='SuperAdmin',
            is_active=True,
        )
        _db.session.add(sa)
        _db.session.commit()
        yield sa.id
        existing = _db.session.get(SuperAdmin, sa.id)
        if existing:
            _db.session.delete(existing)
            _db.session.commit()


@pytest.fixture
def sa_token(client, super_admin):
    resp = client.post(
        '/api/v1/superadmin/auth/login',
        json={'email': 'erp003.sa@sms.com', 'password': 'SA@1234567'},
    )
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()['data']['access_token']


@pytest.fixture
def school_db_cleanup(app):
    """
    Yield a list that tests can append slug strings to.
    After the test, remove each corresponding .db file from SCHOOLS_DB_DIR.
    """
    slugs_to_clean = []
    yield slugs_to_clean
    with app.app_context():
        schools_dir = app.config['SCHOOLS_DB_DIR']
    for slug in slugs_to_clean:
        db_path = os.path.join(schools_dir, f'school_{slug}.db')
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _provision_payload(**overrides):
    base = {
        'name': 'Sunrise Academy',
        'slug': 'sunrise-academy',
        'admin_email': 'admin@sunrise.sms',
        'admin_password': 'Sunrise@123',
        'address': '123 Main St',
        'phone': '+91-9900000001',
        'academic_year_start_month': 6,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# ERP-003: Provision school (POST /)
# ---------------------------------------------------------------------------

class TestProvisionSchool:

    def test_provision_school_success(self, client, sa_token, app, school_db_cleanup):
        slug = 'sunrise-academy'
        school_db_cleanup.append(slug)

        resp = client.post(
            '/api/v1/superadmin/schools/',
            json=_provision_payload(slug=slug),
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 201, resp.get_json()
        body = resp.get_json()
        assert body['success'] is True

        data = body['data']
        assert data['slug'] == slug
        assert data['name'] == 'Sunrise Academy'
        assert data['is_active'] is True
        # Sensitive provisioning fields must NOT appear in the response
        assert 'admin_email' not in data
        assert 'admin_password' not in data

        # School record must be in master.db
        with app.app_context():
            from app.models.master.school import School
            school = School.query.filter_by(slug=slug).first()
            assert school is not None
            assert school.name == 'Sunrise Academy'

        # The school .db file must exist on disk
        with app.app_context():
            schools_dir = app.config['SCHOOLS_DB_DIR']
        db_path = os.path.join(schools_dir, f'school_{slug}.db')
        assert os.path.exists(db_path), f"Expected DB file at {db_path}"

        # alembic_version table must exist in the new DB
        engine = create_engine(f'sqlite:///{db_path}')
        try:
            inspector = inspect(engine)
            assert 'alembic_version' in inspector.get_table_names()
            with engine.connect() as conn:
                row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
                assert row is not None, "alembic_version table is empty"
        finally:
            engine.dispose()

    def test_provision_school_duplicate_slug(self, client, sa_token, app, school_db_cleanup):
        slug = 'duplicate-slug'
        school_db_cleanup.append(slug)

        # First provision succeeds
        r1 = client.post(
            '/api/v1/superadmin/schools/',
            json=_provision_payload(slug=slug, name='First School'),
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert r1.status_code == 201, r1.get_json()

        # Second provision with same slug must fail
        r2 = client.post(
            '/api/v1/superadmin/schools/',
            json=_provision_payload(slug=slug, name='Second School'),
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert r2.status_code == 409, r2.get_json()
        assert r2.get_json()['success'] is False

    def test_provision_school_missing_required_fields(self, client, sa_token):
        # Missing name, admin_email, admin_password
        resp = client.post(
            '/api/v1/superadmin/schools/',
            json={'slug': 'missing-fields'},
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 422
        body = resp.get_json()
        assert body['success'] is False
        errors = body['errors']
        assert 'name' in errors
        assert 'admin_email' in errors
        assert 'admin_password' in errors

    def test_provision_school_invalid_slug_uppercase(self, client, sa_token):
        resp = client.post(
            '/api/v1/superadmin/schools/',
            json=_provision_payload(slug='UpperCase-Slug'),
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 422, resp.get_json()
        assert resp.get_json()['success'] is False

    def test_provision_school_invalid_slug_special_chars(self, client, sa_token):
        resp = client.post(
            '/api/v1/superadmin/schools/',
            json=_provision_payload(slug='bad slug!'),
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 422, resp.get_json()
        assert resp.get_json()['success'] is False

    def test_provision_school_invalid_slug_leading_hyphen(self, client, sa_token):
        resp = client.post(
            '/api/v1/superadmin/schools/',
            json=_provision_payload(slug='-leading-hyphen'),
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 422, resp.get_json()
        assert resp.get_json()['success'] is False

    def test_provision_school_admin_password_too_short(self, client, sa_token):
        resp = client.post(
            '/api/v1/superadmin/schools/',
            json=_provision_payload(admin_password='short'),
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 422, resp.get_json()
        errors = resp.get_json()['errors']
        assert 'admin_password' in errors

    def test_provision_school_seeds_admin_user(self, client, sa_token, app, school_db_cleanup):
        """The first admin user must be created in the school's own DB."""
        slug = 'seed-check'
        school_db_cleanup.append(slug)

        resp = client.post(
            '/api/v1/superadmin/schools/',
            json=_provision_payload(
                slug=slug,
                name='Seed Check School',
                admin_email='first@seedcheck.sms',
                admin_password='SeedAdmin@1',
            ),
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 201, resp.get_json()

        with app.app_context():
            schools_dir = app.config['SCHOOLS_DB_DIR']
        db_path = os.path.join(schools_dir, f'school_{slug}.db')

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.models.user import User
        from app import bcrypt

        engine = create_engine(f'sqlite:///{db_path}')
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            user = session.query(User).filter_by(email='first@seedcheck.sms').first()
            assert user is not None, "Admin user not seeded in school DB"
            assert user.role == 'admin'
            assert user.is_active is True
            # Password must be stored as a hash, not plaintext
            assert user.password_hash != 'SeedAdmin@1'
            assert bcrypt.check_password_hash(user.password_hash, 'SeedAdmin@1')
        finally:
            session.close()
            engine.dispose()


# ---------------------------------------------------------------------------
# ERP-003: List schools (GET /)
# ---------------------------------------------------------------------------

class TestListSchools:

    def test_list_schools(self, client, sa_token, app, school_db_cleanup):
        slug = 'list-test-school'
        school_db_cleanup.append(slug)

        # Provision one school
        client.post(
            '/api/v1/superadmin/schools/',
            json=_provision_payload(slug=slug, name='List Test School'),
            headers={'Authorization': f'Bearer {sa_token}'},
        )

        resp = client.get(
            '/api/v1/superadmin/schools/',
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        data = body['data']
        assert 'schools' in data
        assert 'meta' in data
        assert isinstance(data['schools'], list)
        assert data['meta']['total'] >= 1

        slugs = [s['slug'] for s in data['schools']]
        assert slug in slugs

    def test_list_schools_pagination_meta(self, client, sa_token):
        resp = client.get(
            '/api/v1/superadmin/schools/?page=1&per_page=5',
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 200
        meta = resp.get_json()['data']['meta']
        assert 'total' in meta
        assert 'page' in meta
        assert 'per_page' in meta
        assert 'pages' in meta
        assert meta['per_page'] == 5


# ---------------------------------------------------------------------------
# ERP-003: Get school by ID (GET /<id>)
# ---------------------------------------------------------------------------

class TestGetSchoolById:

    def test_get_school_by_id(self, client, sa_token, app, school_db_cleanup):
        slug = 'get-by-id-school'
        school_db_cleanup.append(slug)

        provision_resp = client.post(
            '/api/v1/superadmin/schools/',
            json=_provision_payload(slug=slug, name='Get By ID School'),
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        school_id = provision_resp.get_json()['data']['id']

        resp = client.get(
            f'/api/v1/superadmin/schools/{school_id}',
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 200, resp.get_json()
        body = resp.get_json()
        assert body['success'] is True
        assert body['data']['id'] == school_id
        assert body['data']['slug'] == slug

    def test_get_school_not_found(self, client, sa_token):
        resp = client.get(
            '/api/v1/superadmin/schools/999999',
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 404
        assert resp.get_json()['success'] is False


# ---------------------------------------------------------------------------
# ERP-003: Update school (PATCH /<id>)
# ---------------------------------------------------------------------------

class TestUpdateSchool:

    def test_deactivate_school(self, client, sa_token, app, school_db_cleanup):
        slug = 'deactivate-school'
        school_db_cleanup.append(slug)

        provision_resp = client.post(
            '/api/v1/superadmin/schools/',
            json=_provision_payload(slug=slug, name='Deactivate Me'),
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        school_id = provision_resp.get_json()['data']['id']

        resp = client.patch(
            f'/api/v1/superadmin/schools/{school_id}',
            json={'is_active': False},
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()['data']
        assert data['is_active'] is False

        # Verify persisted in master.db
        with app.app_context():
            from app.models.master.school import School
            school = _db.session.get(School, school_id)
            assert school.is_active is False

    def test_update_school_name_and_address(self, client, sa_token, app, school_db_cleanup):
        slug = 'update-name-school'
        school_db_cleanup.append(slug)

        provision_resp = client.post(
            '/api/v1/superadmin/schools/',
            json=_provision_payload(slug=slug, name='Original Name'),
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        school_id = provision_resp.get_json()['data']['id']

        resp = client.patch(
            f'/api/v1/superadmin/schools/{school_id}',
            json={'name': 'Updated Name', 'address': '999 New Street'},
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()['data']
        assert data['name'] == 'Updated Name'
        assert data['address'] == '999 New Street'

    def test_update_school_not_found(self, client, sa_token):
        resp = client.patch(
            '/api/v1/superadmin/schools/999999',
            json={'name': 'Ghost School'},
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 404

    def test_update_school_invalid_month(self, client, sa_token, app, school_db_cleanup):
        slug = 'invalid-month-school'
        school_db_cleanup.append(slug)

        provision_resp = client.post(
            '/api/v1/superadmin/schools/',
            json=_provision_payload(slug=slug, name='Month Test School'),
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        school_id = provision_resp.get_json()['data']['id']

        resp = client.patch(
            f'/api/v1/superadmin/schools/{school_id}',
            json={'academic_year_start_month': 13},
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# ERP-003: Authorization checks
# ---------------------------------------------------------------------------

class TestSchoolsAuthorization:

    def test_list_schools_no_token(self, client):
        resp = client.get('/api/v1/superadmin/schools/')
        assert resp.status_code == 401

    def test_provision_school_no_token(self, client):
        resp = client.post(
            '/api/v1/superadmin/schools/',
            json=_provision_payload(),
        )
        assert resp.status_code == 401

    def test_get_school_no_token(self, client):
        resp = client.get('/api/v1/superadmin/schools/1')
        assert resp.status_code == 401

    def test_patch_school_no_token(self, client):
        resp = client.patch('/api/v1/superadmin/schools/1', json={'name': 'X'})
        assert resp.status_code == 401

    def test_list_schools_school_admin_token_forbidden(self, client, admin_user):
        """A school-level admin JWT must be rejected with 403."""
        login_resp = client.post(
            '/api/v1/auth/login',
            json={'email': 'admin@test.sms', 'password': 'Admin@1234', 'school_slug': 'test'},
        )
        school_token = login_resp.get_json()['data']['access_token']

        resp = client.get(
            '/api/v1/superadmin/schools/',
            headers={'Authorization': f'Bearer {school_token}'},
        )
        assert resp.status_code == 403

    def test_provision_school_school_admin_token_forbidden(self, client, admin_user):
        """A school-level admin JWT must not be able to provision schools."""
        login_resp = client.post(
            '/api/v1/auth/login',
            json={'email': 'admin@test.sms', 'password': 'Admin@1234', 'school_slug': 'test'},
        )
        school_token = login_resp.get_json()['data']['access_token']

        resp = client.post(
            '/api/v1/superadmin/schools/',
            json=_provision_payload(),
            headers={'Authorization': f'Bearer {school_token}'},
        )
        assert resp.status_code == 403
