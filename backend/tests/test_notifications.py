"""
Sprint 8 — Notifications Tests (SMS-049)
"""
import pytest

from app.models.user import User
from app.models.notification import Notification


_counter = 0

def _uid():
    global _counter
    _counter += 1
    return _counter


def make_user(db, role='parent'):
    uid = _uid()
    u = User(email=f'notif_{role}_{uid}@test.sms', role=role,
             first_name=f'Notif{uid}', last_name='User')
    u.set_password('Test@1234')
    db.session.add(u)
    db.session.commit()
    return u


def make_notification(db, user_id, is_read=False, title='Test Notif'):
    n = Notification(
        user_id=user_id,
        type='general',
        title=title,
        body='Notification body',
        is_read=is_read,
    )
    db.session.add(n)
    db.session.commit()
    return n


def _login(client, email, password):
    resp = client.post('/api/v1/auth/login', json={
        'email': email, 'password': password, 'school_slug': 'test'
    })
    return resp.get_json()['data']


def _h(token):
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def notif_user(db, client):
    u = make_user(db, role='parent')
    token = _login(client, u.email, 'Test@1234')['access_token']
    return {'user': u, 'token': token}


class TestNotificationsExtended:

    def test_list_unread_notifications(self, client, db, notif_user):
        """T-049-1: List unread notifications returns 200."""
        make_notification(db, notif_user['user'].id, is_read=False, title='Unread1')
        make_notification(db, notif_user['user'].id, is_read=True, title='Read1')
        resp = client.get(
            '/api/v1/notifications?unread=true',
            headers=_h(notif_user['token']),
        )
        assert resp.status_code == 200
        notifs = resp.get_json()['data']['notifications']
        assert len(notifs) == 1
        assert notifs[0]['title'] == 'Unread1'
        assert notifs[0]['is_read'] is False

    def test_mark_one_notification_read(self, client, db, notif_user):
        """T-049-2: Mark single notification as read → is_read=True."""
        n = make_notification(db, notif_user['user'].id, is_read=False, title='ToRead')
        resp = client.put(
            f'/api/v1/notifications/{n.id}/read',
            headers=_h(notif_user['token']),
        )
        assert resp.status_code == 200
        db.session.refresh(n)
        assert n.is_read is True

    def test_mark_all_read(self, client, db, notif_user):
        """T-049-3: Mark all notifications as read."""
        make_notification(db, notif_user['user'].id, is_read=False, title='A')
        make_notification(db, notif_user['user'].id, is_read=False, title='B')
        make_notification(db, notif_user['user'].id, is_read=True, title='C')

        resp = client.put(
            '/api/v1/notifications/read-all',
            headers=_h(notif_user['token']),
        )
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True
        assert '2' in resp.get_json()['message']

    def test_non_owner_cannot_mark_read(self, client, db, notif_user):
        """T-049-4: Another user cannot mark someone else's notification as read."""
        other_user = make_user(db, role='parent')
        other_token = _login(client, other_user.email, 'Test@1234')['access_token']

        n = make_notification(db, notif_user['user'].id, is_read=False)
        resp = client.put(
            f'/api/v1/notifications/{n.id}/read',
            headers=_h(other_token),
        )
        assert resp.status_code == 404
