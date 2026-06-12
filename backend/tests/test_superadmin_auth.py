"""
Tests for ERP-002 — Super Admin Authentication.

Endpoints under test:
  POST   /api/v1/superadmin/auth/login
  POST   /api/v1/superadmin/auth/refresh
  DELETE /api/v1/superadmin/auth/logout
  GET    /api/v1/superadmin/auth/me
"""
import pytest
from flask_jwt_extended import decode_token

from app import db as _db, bcrypt


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def super_admin(app):
    with app.app_context():
        from app.models.master.super_admin import SuperAdmin
        sa = SuperAdmin(
            email='test.sa@sms.com',
            password_hash=bcrypt.generate_password_hash('Test@1234').decode('utf-8'),
            first_name='Test',
            last_name='SuperAdmin',
            is_active=True,
        )
        _db.session.add(sa)
        _db.session.commit()
        # Yield the id so the object can be refreshed inside each test's context
        yield sa.id
        # Clean up — guard against already-deleted rows
        existing = _db.session.get(SuperAdmin, sa.id)
        if existing:
            _db.session.delete(existing)
            _db.session.commit()


@pytest.fixture
def sa_token(client, super_admin):
    resp = client.post(
        '/api/v1/superadmin/auth/login',
        json={'email': 'test.sa@sms.com', 'password': 'Test@1234'},
    )
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()['data']['access_token']


@pytest.fixture
def sa_refresh_token(client, super_admin):
    resp = client.post(
        '/api/v1/superadmin/auth/login',
        json={'email': 'test.sa@sms.com', 'password': 'Test@1234'},
    )
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()['data']['refresh_token']


# ---------------------------------------------------------------------------
# ERP-002: Login
# ---------------------------------------------------------------------------

class TestSuperAdminLogin:

    def test_superadmin_login_success(self, client, super_admin):
        resp = client.post(
            '/api/v1/superadmin/auth/login',
            json={'email': 'test.sa@sms.com', 'password': 'Test@1234'},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True

        data = body['data']
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert data['super_admin']['email'] == 'test.sa@sms.com'
        assert data['super_admin']['first_name'] == 'Test'
        assert data['super_admin']['last_name'] == 'SuperAdmin'

        # Verify JWT claims
        claims = decode_token(data['access_token'])
        assert claims['role'] == 'super_admin'
        assert 'super_admin_id' in claims
        assert isinstance(claims['super_admin_id'], int)

    def test_superadmin_login_no_school_slug_in_claims(self, client, super_admin):
        resp = client.post(
            '/api/v1/superadmin/auth/login',
            json={'email': 'test.sa@sms.com', 'password': 'Test@1234'},
        )
        assert resp.status_code == 200
        claims = decode_token(resp.get_json()['data']['access_token'])
        assert 'school_slug' not in claims

    def test_superadmin_login_identity_has_sa_prefix(self, client, super_admin):
        resp = client.post(
            '/api/v1/superadmin/auth/login',
            json={'email': 'test.sa@sms.com', 'password': 'Test@1234'},
        )
        assert resp.status_code == 200
        claims = decode_token(resp.get_json()['data']['access_token'])
        assert claims['sub'].startswith('sa:')

    def test_superadmin_login_wrong_password(self, client, super_admin):
        resp = client.post(
            '/api/v1/superadmin/auth/login',
            json={'email': 'test.sa@sms.com', 'password': 'WrongPassword!'},
        )
        assert resp.status_code == 401
        assert resp.get_json()['success'] is False

    def test_superadmin_login_wrong_email(self, client, super_admin):
        resp = client.post(
            '/api/v1/superadmin/auth/login',
            json={'email': 'nobody@sms.com', 'password': 'Test@1234'},
        )
        assert resp.status_code == 401
        assert resp.get_json()['success'] is False

    def test_superadmin_login_missing_password(self, client, super_admin):
        resp = client.post(
            '/api/v1/superadmin/auth/login',
            json={'email': 'test.sa@sms.com'},
        )
        assert resp.status_code == 400

    def test_superadmin_login_missing_email(self, client, super_admin):
        resp = client.post(
            '/api/v1/superadmin/auth/login',
            json={'password': 'Test@1234'},
        )
        assert resp.status_code == 400

    def test_superadmin_login_empty_body(self, client, super_admin):
        resp = client.post('/api/v1/superadmin/auth/login', json={})
        assert resp.status_code == 400

    def test_superadmin_login_inactive_account(self, client, super_admin):
        from app.models.master.super_admin import SuperAdmin
        sa = _db.session.get(SuperAdmin, super_admin)
        sa.is_active = False
        _db.session.commit()

        resp = client.post(
            '/api/v1/superadmin/auth/login',
            json={'email': 'test.sa@sms.com', 'password': 'Test@1234'},
        )
        assert resp.status_code == 401
        assert resp.get_json()['success'] is False


# ---------------------------------------------------------------------------
# ERP-002: Me endpoint
# ---------------------------------------------------------------------------

class TestSuperAdminMe:

    def test_superadmin_me_success(self, client, sa_token):
        resp = client.get(
            '/api/v1/superadmin/auth/me',
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        data = body['data']
        assert data['email'] == 'test.sa@sms.com'
        assert data['first_name'] == 'Test'
        assert data['last_name'] == 'SuperAdmin'
        # Sensitive fields must never be exposed
        assert 'password_hash' not in data

    def test_superadmin_me_no_school_data(self, client, sa_token):
        resp = client.get(
            '/api/v1/superadmin/auth/me',
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        data = resp.get_json()['data']
        assert 'school_slug' not in data
        assert 'user_id' not in data

    def test_superadmin_me_requires_auth(self, client):
        resp = client.get('/api/v1/superadmin/auth/me')
        assert resp.status_code == 401

    def test_superadmin_me_school_token_forbidden(self, client, admin_user):
        """A school admin JWT must not access the super admin /me endpoint."""
        login_resp = client.post(
            '/api/v1/auth/login',
            json={'email': 'admin@test.sms', 'password': 'Admin@1234', 'school_slug': 'test'},
        )
        school_token = login_resp.get_json()['data']['access_token']

        resp = client.get(
            '/api/v1/superadmin/auth/me',
            headers={'Authorization': f'Bearer {school_token}'},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# ERP-002: Logout (token revocation)
# ---------------------------------------------------------------------------

class TestSuperAdminLogout:

    def test_superadmin_logout_success(self, client, sa_token):
        resp = client.delete(
            '/api/v1/superadmin/auth/logout',
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    def test_superadmin_logout_revokes_token(self, client, sa_token):
        # Logout
        client.delete(
            '/api/v1/superadmin/auth/logout',
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        # Subsequent request with the same token must be rejected
        resp = client.get(
            '/api/v1/superadmin/auth/me',
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code == 401

    def test_superadmin_logout_requires_auth(self, client):
        resp = client.delete('/api/v1/superadmin/auth/logout')
        assert resp.status_code == 401

    def test_school_token_cannot_use_sa_logout(self, client, admin_user):
        """A school admin JWT hitting the SA logout must be rejected with 403."""
        login_resp = client.post(
            '/api/v1/auth/login',
            json={'email': 'admin@test.sms', 'password': 'Admin@1234', 'school_slug': 'test'},
        )
        school_token = login_resp.get_json()['data']['access_token']

        resp = client.delete(
            '/api/v1/superadmin/auth/logout',
            headers={'Authorization': f'Bearer {school_token}'},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# ERP-002: Token Refresh
# ---------------------------------------------------------------------------

class TestSuperAdminRefresh:

    def test_superadmin_refresh_returns_new_access_token(self, client, sa_refresh_token):
        resp = client.post(
            '/api/v1/superadmin/auth/refresh',
            headers={'Authorization': f'Bearer {sa_refresh_token}'},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        assert 'access_token' in body['data']

    def test_superadmin_refresh_preserves_claims(self, client, sa_refresh_token):
        resp = client.post(
            '/api/v1/superadmin/auth/refresh',
            headers={'Authorization': f'Bearer {sa_refresh_token}'},
        )
        assert resp.status_code == 200
        new_token = resp.get_json()['data']['access_token']
        claims = decode_token(new_token)
        assert claims['role'] == 'super_admin'
        assert 'super_admin_id' in claims
        assert 'school_slug' not in claims

    def test_superadmin_refresh_with_access_token_fails(self, client, sa_token):
        """Access tokens must not be accepted on the refresh endpoint."""
        resp = client.post(
            '/api/v1/superadmin/auth/refresh',
            headers={'Authorization': f'Bearer {sa_token}'},
        )
        assert resp.status_code in (401, 422)

    def test_superadmin_refresh_requires_auth(self, client):
        resp = client.post('/api/v1/superadmin/auth/refresh')
        assert resp.status_code == 401

    def test_school_refresh_token_rejected_by_sa_refresh(self, client, refresh_token_for_admin):
        """A school user's refresh token must be rejected by the SA refresh endpoint."""
        resp = client.post(
            '/api/v1/superadmin/auth/refresh',
            headers={'Authorization': f'Bearer {refresh_token_for_admin}'},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# ERP-002: Isolation — super admin logout does not affect school users
# ---------------------------------------------------------------------------

class TestTokenIsolation:

    def test_sa_revoked_token_does_not_affect_school_login(self, client, super_admin, admin_user):
        """Revoking a super admin token must not block school user requests."""
        sa_resp = client.post(
            '/api/v1/superadmin/auth/login',
            json={'email': 'test.sa@sms.com', 'password': 'Test@1234'},
        )
        sa_tok = sa_resp.get_json()['data']['access_token']

        # Get a school admin token
        school_resp = client.post(
            '/api/v1/auth/login',
            json={'email': 'admin@test.sms', 'password': 'Admin@1234', 'school_slug': 'test'},
        )
        school_tok = school_resp.get_json()['data']['access_token']

        # Revoke the SA token
        client.delete(
            '/api/v1/superadmin/auth/logout',
            headers={'Authorization': f'Bearer {sa_tok}'},
        )

        # School token must still work
        me_resp = client.get(
            '/api/v1/auth/me',
            headers={'Authorization': f'Bearer {school_tok}'},
        )
        assert me_resp.status_code == 200
