"""
Tests for ERP-003 — School Provisioning API (SQLite-safe subset).

These cover request validation, authorization, and master-table CRUD (list /
get / update) — none of which require a real school schema. The actual
schema-per-school provisioning behaviour (CREATE SCHEMA, seeded admin, etc.) is
verified against PostgreSQL in tests/integration_pg/test_provisioning_pg.py.

Endpoints under test:
  GET    /api/v1/superadmin/schools/
  POST   /api/v1/superadmin/schools/
  GET    /api/v1/superadmin/schools/<id>
  PATCH  /api/v1/superadmin/schools/<id>
"""
import pytest

from app import db as _db, bcrypt


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def super_admin(app):
    """Create a super admin in the master tables and tear it down afterwards."""
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


def _make_school(slug, name='Some School', **kwargs):
    """Insert a School row directly in the master table (no schema creation)."""
    from app.models.master.school import School
    school = School(
        name=name,
        slug=slug,
        db_url=f'school_{slug}'.replace('-', '_'),
        is_active=kwargs.pop('is_active', True),
        **kwargs,
    )
    _db.session.add(school)
    _db.session.commit()
    return school


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
# ERP-003: Provision school — request validation (SQLite-safe; rejected before
# any schema is created)
# ---------------------------------------------------------------------------

class TestProvisionSchoolValidation:

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


# ---------------------------------------------------------------------------
# ERP-003: List schools (GET /)
# ---------------------------------------------------------------------------

class TestListSchools:

    def test_list_schools(self, client, sa_token):
        _make_school('list-test-school', name='List Test School')

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
        assert 'list-test-school' in slugs

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

    def test_get_school_by_id(self, client, sa_token):
        school = _make_school('get-by-id-school', name='Get By ID School')

        resp = client.get(
            f'/api/v1/superadmin/schools/{school.id}',
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 200, resp.get_json()
        body = resp.get_json()
        assert body['success'] is True
        assert body['data']['id'] == school.id
        assert body['data']['slug'] == 'get-by-id-school'

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

    def test_deactivate_school(self, client, sa_token, app):
        school = _make_school('deactivate-school', name='Deactivate Me')

        resp = client.patch(
            f'/api/v1/superadmin/schools/{school.id}',
            json={'is_active': False},
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 200, resp.get_json()
        data = resp.get_json()['data']
        assert data['is_active'] is False

        with app.app_context():
            from app.models.master.school import School
            refreshed = _db.session.get(School, school.id)
            assert refreshed.is_active is False

    def test_update_school_name_and_address(self, client, sa_token):
        school = _make_school('update-name-school', name='Original Name')

        resp = client.patch(
            f'/api/v1/superadmin/schools/{school.id}',
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

    def test_update_school_invalid_month(self, client, sa_token):
        school = _make_school('invalid-month-school', name='Month Test School')

        resp = client.patch(
            f'/api/v1/superadmin/schools/{school.id}',
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
