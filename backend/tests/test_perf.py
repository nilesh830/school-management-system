"""
SMS-064 — Performance optimization tests:
  * TTLCache behavior (get/set/expiry/invalidate/clear)
  * Admin dashboard per-tenant caching with a non-zero TTL
  * gzip response compression (Flask-Compress)
"""
from datetime import date

from app.utils.cache import TTLCache, dashboard_cache
from app.models.user import User
from app.models.student import Student


def auth(token):
    return {'Authorization': f'Bearer {token}'}


def make_student(db, admission_no, email):
    u = User(email=email, role='student', first_name='Perf', last_name='Test')
    u.set_password('Student@123')
    db.session.add(u)
    db.session.flush()
    s = Student(
        user_id=u.id, admission_no=admission_no, first_name='Perf', last_name='Test',
        date_of_birth=date(2012, 1, 1), gender='Male', admission_date=date(2024, 6, 1),
    )
    db.session.add(s)
    db.session.commit()
    return s


# ---------------------------------------------------------------------------
# TTLCache unit tests
# ---------------------------------------------------------------------------

class TestTTLCache:

    def test_get_miss_returns_none(self):
        c = TTLCache()
        assert c.get('missing') is None

    def test_set_then_get_hit(self):
        c = TTLCache()
        c.set('k', {'v': 1}, ttl=300)
        assert c.get('k') == {'v': 1}

    def test_zero_ttl_expires_immediately(self):
        c = TTLCache()
        c.set('k', 'v', ttl=0)
        # expires_at == now, so the next read is already expired
        assert c.get('k') is None

    def test_invalidate(self):
        c = TTLCache()
        c.set('k', 'v', ttl=300)
        c.invalidate('k')
        assert c.get('k') is None

    def test_clear(self):
        c = TTLCache()
        c.set('a', 1, ttl=300)
        c.set('b', 2, ttl=300)
        c.clear()
        assert c.get('a') is None and c.get('b') is None


# ---------------------------------------------------------------------------
# Dashboard caching integration (TTL temporarily enabled)
# ---------------------------------------------------------------------------

class TestDashboardCaching:

    def test_admin_dashboard_is_cached_per_tenant(self, app, client, admin_token, db):
        dashboard_cache.clear()
        original_ttl = app.config.get('DASHBOARD_CACHE_TTL', 0)
        app.config['DASHBOARD_CACHE_TTL'] = 300
        try:
            make_student(db, 'ADM-PERF-1', 'p1@test.sms')
            first = client.get('/api/v1/dashboard/admin', headers=auth(admin_token))
            assert first.status_code == 200
            count1 = first.get_json()['data']['total_students']

            # Mutate underlying data, then request again — should serve stale cache
            make_student(db, 'ADM-PERF-2', 'p2@test.sms')
            second = client.get('/api/v1/dashboard/admin', headers=auth(admin_token))
            assert second.status_code == 200
            assert second.get_json()['data']['total_students'] == count1
            assert 'cached' in second.get_json()['message'].lower()

            # After invalidation, fresh data appears
            dashboard_cache.clear()
            third = client.get('/api/v1/dashboard/admin', headers=auth(admin_token))
            assert third.get_json()['data']['total_students'] == count1 + 1
        finally:
            app.config['DASHBOARD_CACHE_TTL'] = original_ttl
            dashboard_cache.clear()


# ---------------------------------------------------------------------------
# gzip compression
# ---------------------------------------------------------------------------

class TestCompression:

    def test_large_response_is_gzipped(self, client):
        # /apispec.json is a large unauthenticated payload (> COMPRESS_MIN_SIZE).
        resp = client.get('/apispec.json', headers={'Accept-Encoding': 'gzip'})
        assert resp.status_code == 200
        assert resp.headers.get('Content-Encoding') == 'gzip'
