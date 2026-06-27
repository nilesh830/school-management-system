"""
Sprint 8 — Parent Profile Tests (SMS-050)
"""
import pytest
from datetime import date

from app.models.user import User
from app.models.parent import Parent


_counter = 0

def _uid():
    global _counter
    _counter += 1
    return _counter


def make_parent_user(db):
    uid = _uid()
    u = User(email=f'prof_parent_{uid}@test.sms', role='parent',
             first_name=f'ProfParent{uid}', last_name='Test')
    u.set_password('Parent@123')
    db.session.add(u)
    db.session.flush()
    p = Parent(
        user_id=u.id,
        first_name=f'ProfParent{uid}',
        last_name='Test',
        relationship_type='Mother',
        phone_primary='+91-9555555555',
        occupation='Engineer',
    )
    db.session.add(p)
    db.session.commit()
    return u, p


def _login(client, email, password):
    resp = client.post('/api/v1/auth/login', json={
        'email': email, 'password': password, 'school_slug': 'test'
    })
    return resp.get_json()['data']


def _h(token):
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def profile_setup(db, client):
    user, parent = make_parent_user(db)
    token = _login(client, user.email, 'Parent@123')['access_token']
    return {'user': user, 'parent': parent, 'token': token}


class TestParentProfile:

    def test_get_my_profile_returns_200(self, client, profile_setup):
        """T-050-1: GET /me returns 200 with parent data."""
        resp = client.get('/api/v1/parents/me', headers=_h(profile_setup['token']))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['data']['id'] == profile_setup['parent'].id
        assert data['data']['occupation'] == 'Engineer'

    def test_patch_my_profile_returns_200(self, client, db, profile_setup):
        """T-050-2: PATCH /me updates allowed fields."""
        resp = client.patch('/api/v1/parents/me', json={
            'occupation': 'Doctor',
            'phone_secondary': '+91-9000000002',
        }, headers=_h(profile_setup['token']))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['data']['occupation'] == 'Doctor'
        assert data['data']['phone_secondary'] == '+91-9000000002'

    def test_patch_cannot_update_email(self, client, db, profile_setup):
        """T-050-3: PATCH cannot change email — it is not in the allowed list."""
        original_email = profile_setup['user'].email
        resp = client.patch('/api/v1/parents/me', json={
            'email': 'hacker@evil.com',
            'occupation': 'Hacker',
        }, headers=_h(profile_setup['token']))
        # Should succeed but email must not change
        assert resp.status_code == 200
        db.session.refresh(profile_setup['user'])
        assert profile_setup['user'].email == original_email

    def test_non_parent_role_returns_403(self, client, admin_token):
        """T-050-4: Admin role cannot access parent profile endpoint."""
        resp = client.get('/api/v1/parents/me', headers=_h(admin_token))
        assert resp.status_code == 403
