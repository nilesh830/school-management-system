"""
Tests for SMS-001, SMS-002, SMS-005, SMS-006 — Auth endpoints.
"""
import pytest


# ── SMS-001: Login ───────────────────────────────────────────────────────────

class TestLogin:

    def test_login_success_admin(self, client, admin_user):
        resp = client.post('/api/v1/auth/login', json={
            'email': 'admin@test.sms',
            'password': 'Admin@1234',
            'school_slug': 'test',
        })
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        assert 'access_token' in body['data']
        assert 'refresh_token' in body['data']
        assert body['data']['user']['role'] == 'admin'

    def test_login_parent_includes_parent_id_in_jwt(self, client, parent_user, db):
        from flask_jwt_extended import decode_token
        resp = client.post('/api/v1/auth/login', json={
            'email': 'robert@test.sms',
            'password': 'Parent@123',
            'school_slug': 'test',
        })
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        token = body['data']['access_token']
        claims = decode_token(token)
        assert claims['role'] == 'parent'
        assert 'parent_id' in claims
        assert isinstance(claims['parent_id'], int)

    def test_login_wrong_password(self, client, admin_user):
        resp = client.post('/api/v1/auth/login', json={
            'email': 'admin@test.sms',
            'password': 'WrongPass',
            'school_slug': 'test',
        })
        assert resp.status_code == 401
        assert resp.get_json()['success'] is False

    def test_login_nonexistent_email(self, client):
        resp = client.post('/api/v1/auth/login', json={
            'email': 'nobody@test.sms',
            'password': 'Any@1234',
            'school_slug': 'test',
        })
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post('/api/v1/auth/login', json={'email': 'admin@test.sms'})
        assert resp.status_code == 400

    def test_login_inactive_user(self, client, db, admin_user):
        admin_user.is_active = False
        db.session.commit()
        resp = client.post('/api/v1/auth/login', json={
            'email': 'admin@test.sms',
            'password': 'Admin@1234',
            'school_slug': 'test',
        })
        assert resp.status_code == 401

    def test_me_endpoint_returns_user_profile(self, client, admin_token):
        resp = client.get(
            '/api/v1/auth/me',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['email'] == 'admin@test.sms'
        assert data['role'] == 'admin'
        assert 'password_hash' not in data

    def test_me_requires_auth(self, client):
        resp = client.get('/api/v1/auth/me')
        assert resp.status_code == 401


# ── SMS-002: Token Refresh & Logout ─────────────────────────────────────────

class TestRefreshAndLogout:

    def test_refresh_returns_new_access_token(self, client, refresh_token_for_admin):
        resp = client.post(
            '/api/v1/auth/refresh',
            headers={'Authorization': f'Bearer {refresh_token_for_admin}'},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        assert 'access_token' in body['data']

    def test_refresh_with_access_token_fails(self, client, admin_token):
        resp = client.post(
            '/api/v1/auth/refresh',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        # Flask-JWT-Extended returns 401 via our custom unauthorized/invalid handlers
        assert resp.status_code in (401, 422)

    def test_logout_revokes_token(self, client, admin_token):
        # Logout
        resp = client.delete(
            '/api/v1/auth/logout',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 200

        # Subsequent request with same token should be rejected
        resp2 = client.get(
            '/api/v1/auth/me',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp2.status_code == 401

    def test_logout_requires_auth(self, client):
        resp = client.delete('/api/v1/auth/logout')
        assert resp.status_code == 401


# ── SMS-003: User Registration ───────────────────────────────────────────────

class TestUserRegistration:

    def test_admin_can_create_teacher(self, client, admin_token):
        resp = client.post(
            '/api/v1/users',
            json={
                'email': 'newteacher@test.sms',
                'password': 'Teacher@123',
                'role': 'teacher',
                'first_name': 'New',
                'last_name': 'Teacher',
            },
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body['success'] is True
        assert body['data']['user']['role'] == 'teacher'
        assert body['data']['user']['email'] == 'newteacher@test.sms'

    def test_admin_can_create_parent_with_profile(self, client, admin_token):
        resp = client.post(
            '/api/v1/users',
            json={
                'email': 'newparent@test.sms',
                'password': 'Parent@123',
                'role': 'parent',
                'first_name': 'Jane',
                'last_name': 'Doe',
                'relationship_type': 'Mother',
                'phone_primary': '+91-9000000001',
            },
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body['data']['user']['role'] == 'parent'

        # Verify Parent record was created
        from app.models.parent import Parent
        from app.models.user import User
        user_id = body['data']['user']['id']
        parent = Parent.query.filter_by(user_id=user_id).first()
        assert parent is not None
        assert parent.relationship_type == 'Mother'

    def test_teacher_cannot_create_user(self, client, teacher_token):
        resp = client.post(
            '/api/v1/users',
            json={'email': 'x@test.sms', 'password': 'X@1234ab', 'role': 'teacher',
                  'first_name': 'X', 'last_name': 'Y'},
            headers={'Authorization': f'Bearer {teacher_token}'},
        )
        assert resp.status_code == 403

    def test_duplicate_email_rejected(self, client, admin_token, admin_user):
        resp = client.post(
            '/api/v1/users',
            json={
                'email': 'admin@test.sms',  # already exists
                'password': 'Admin@1234',
                'role': 'teacher',
                'first_name': 'Dupe',
                'last_name': 'User',
            },
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 409

    def test_weak_password_rejected(self, client, admin_token):
        resp = client.post(
            '/api/v1/users',
            json={
                'email': 'weak@test.sms',
                'password': 'password',  # no uppercase/digit/special
                'role': 'teacher',
                'first_name': 'Weak',
                'last_name': 'Pass',
            },
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 422

    def test_parent_without_required_fields_rejected(self, client, admin_token):
        resp = client.post(
            '/api/v1/users',
            json={
                'email': 'incomplete.parent@test.sms',
                'password': 'Parent@123',
                'role': 'parent',
                'first_name': 'John',
                'last_name': 'Doe',
                # missing relationship_type and phone_primary
            },
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 400

    def test_list_users_admin_only(self, client, admin_token, teacher_token):
        # Admin can list
        resp = client.get('/api/v1/users', headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200

        # Teacher cannot
        resp2 = client.get('/api/v1/users', headers={'Authorization': f'Bearer {teacher_token}'})
        assert resp2.status_code == 403

    def test_deactivate_user(self, client, admin_token, teacher_user):
        resp = client.delete(
            f'/api/v1/users/{teacher_user.id}',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 200
        assert resp.get_json()['data']['is_active'] is False


# ── SMS-005: Password Reset ───────────────────────────────────────────────────

class TestPasswordReset:

    def test_forgot_password_always_returns_200(self, client, admin_user):
        # Known email
        resp = client.post('/api/v1/auth/forgot-password', json={'email': 'admin@test.sms'})
        assert resp.status_code == 200

    def test_forgot_password_unknown_email_still_200(self, client):
        resp = client.post('/api/v1/auth/forgot-password', json={'email': 'nobody@nowhere.com'})
        assert resp.status_code == 200

    def test_reset_password_with_valid_token(self, client, db, admin_user):
        import hashlib, secrets
        from datetime import datetime, timedelta
        from app.models.password_reset_token import PasswordResetToken

        raw = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        rt = PasswordResetToken(
            user_id=admin_user.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.session.add(rt)
        db.session.commit()

        resp = client.post('/api/v1/auth/reset-password', json={
            'token': raw,
            'password': 'NewAdmin@5678',
        })
        assert resp.status_code == 200

        # Old password should now fail
        resp2 = client.post('/api/v1/auth/login', json={
            'email': 'admin@test.sms',
            'password': 'Admin@1234',
            'school_slug': 'test',
        })
        assert resp2.status_code == 401

        # New password should work
        resp3 = client.post('/api/v1/auth/login', json={
            'email': 'admin@test.sms',
            'password': 'NewAdmin@5678',
            'school_slug': 'test',
        })
        assert resp3.status_code == 200

    def test_reset_password_invalid_token(self, client):
        resp = client.post('/api/v1/auth/reset-password', json={
            'token': 'completely-invalid-token',
            'password': 'NewAdmin@5678',
        })
        assert resp.status_code == 400

    def test_reset_password_weak_password_rejected(self, client, db, admin_user):
        import hashlib, secrets
        from datetime import datetime, timedelta
        from app.models.password_reset_token import PasswordResetToken

        raw = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        rt = PasswordResetToken(
            user_id=admin_user.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.session.add(rt)
        db.session.commit()

        resp = client.post('/api/v1/auth/reset-password', json={
            'token': raw,
            'password': 'weak',
        })
        assert resp.status_code == 422


# ── SMS-006: Profile Update ───────────────────────────────────────────────────

class TestProfileUpdate:

    def test_update_profile_name(self, client, admin_token):
        resp = client.patch(
            '/api/v1/auth/profile',
            json={'first_name': 'UpdatedFirst', 'last_name': 'UpdatedLast'},
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['first_name'] == 'UpdatedFirst'
        assert data['last_name'] == 'UpdatedLast'

    def test_update_profile_requires_auth(self, client):
        resp = client.patch('/api/v1/auth/profile', json={'first_name': 'X'})
        assert resp.status_code == 401

    def test_update_profile_empty_body(self, client, admin_token):
        resp = client.patch(
            '/api/v1/auth/profile',
            json={},
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 400


# ── ERP-005: JWT school_slug enrichment ─────────────────────────────────────

class TestLoginSchoolSlug:

    def test_login_embeds_school_slug_in_jwt(self, client, admin_user):
        from flask_jwt_extended import decode_token
        resp = client.post('/api/v1/auth/login', json={
            'email': 'admin@test.sms', 'password': 'Admin@1234', 'school_slug': 'test'
        })
        assert resp.status_code == 200
        token = resp.get_json()['data']['access_token']
        claims = decode_token(token)
        assert claims['school_slug'] == 'test'

    def test_login_missing_school_slug_returns_400(self, client, admin_user):
        resp = client.post('/api/v1/auth/login', json={
            'email': 'admin@test.sms', 'password': 'Admin@1234'
        })
        assert resp.status_code == 400

    def test_login_unknown_school_slug_returns_404(self, client, admin_user):
        resp = client.post('/api/v1/auth/login', json={
            'email': 'admin@test.sms', 'password': 'Admin@1234', 'school_slug': 'doesnotexist'
        })
        assert resp.status_code == 404

    def test_login_inactive_school_returns_404(self, client, admin_user, db):
        from app.models.master.school import School
        school = School.query.filter_by(slug='test').first()
        school.is_active = False
        db.session.commit()
        resp = client.post('/api/v1/auth/login', json={
            'email': 'admin@test.sms', 'password': 'Admin@1234', 'school_slug': 'test'
        })
        assert resp.status_code == 404

    def test_refresh_preserves_school_slug(self, client, admin_user):
        from flask_jwt_extended import decode_token
        login_resp = client.post('/api/v1/auth/login', json={
            'email': 'admin@test.sms', 'password': 'Admin@1234', 'school_slug': 'test'
        })
        refresh_token = login_resp.get_json()['data']['refresh_token']
        refresh_resp = client.post('/api/v1/auth/refresh', headers={
            'Authorization': f'Bearer {refresh_token}'
        })
        assert refresh_resp.status_code == 200
        new_token = refresh_resp.get_json()['data']['access_token']
        claims = decode_token(new_token)
        assert claims['school_slug'] == 'test'
