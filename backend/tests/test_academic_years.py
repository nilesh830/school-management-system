"""
Sprint 3 — SMS-023 Academic Year Management
"""
import pytest
from datetime import date
from app.models.academic_year import AcademicYear


def make_ay(db, name='2024-2025', is_current=False):
    ay = AcademicYear(
        name=name,
        start_date=date(2024, 4, 1),
        end_date=date(2025, 3, 31),
        is_current=is_current,
    )
    db.session.add(ay)
    db.session.commit()
    return ay


class TestAcademicYearCreate:

    def test_admin_creates_academic_year(self, client, admin_token):
        resp = client.post('/api/v1/academic-years', json={
            'name': '2024-2025',
            'start_date': '2024-04-01',
            'end_date': '2025-03-31',
            'is_current': True,
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 201
        data = resp.get_json()['data']
        assert data['name'] == '2024-2025'
        assert data['is_current'] is True

    def test_duplicate_name_returns_409(self, client, db, admin_token):
        make_ay(db, '2024-2025')
        resp = client.post('/api/v1/academic-years', json={
            'name': '2024-2025',
            'start_date': '2024-04-01',
            'end_date': '2025-03-31',
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 409

    def test_missing_required_fields_400(self, client, admin_token):
        resp = client.post('/api/v1/academic-years', json={'name': '2024-2025'},
                           headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 400

    def test_teacher_cannot_create(self, client, teacher_token):
        resp = client.post('/api/v1/academic-years', json={
            'name': '2024-2025',
            'start_date': '2024-04-01',
            'end_date': '2025-03-31',
        }, headers={'Authorization': f'Bearer {teacher_token}'})
        assert resp.status_code == 403

    def test_setting_current_unsets_others(self, client, db, admin_token):
        ay1 = make_ay(db, '2023-2024', is_current=True)
        resp = client.post('/api/v1/academic-years', json={
            'name': '2024-2025',
            'start_date': '2024-04-01',
            'end_date': '2025-03-31',
            'is_current': True,
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 201
        # Old one should no longer be current
        db.session.refresh(ay1)
        assert ay1.is_current is False


class TestAcademicYearRead:

    def test_list_academic_years(self, client, db, admin_token):
        make_ay(db, '2023-2024')
        make_ay(db, '2024-2025')
        resp = client.get('/api/v1/academic-years',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        assert len(resp.get_json()['data']['academic_years']) == 2

    def test_get_current_academic_year(self, client, db, admin_token):
        make_ay(db, '2024-2025', is_current=True)
        resp = client.get('/api/v1/academic-years/current',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        assert resp.get_json()['data']['is_current'] is True

    def test_get_current_none_returns_404(self, client, admin_token):
        resp = client.get('/api/v1/academic-years/current',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 404


class TestAcademicYearUpdate:

    def test_admin_updates_academic_year(self, client, db, admin_token):
        ay = make_ay(db, '2024-2025')
        resp = client.put(f'/api/v1/academic-years/{ay.id}', json={
            'is_current': True,
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        assert resp.get_json()['data']['is_current'] is True

    def test_update_nonexistent_404(self, client, admin_token):
        resp = client.put('/api/v1/academic-years/9999', json={'is_current': True},
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 404


class TestAcademicYearDelete:

    def test_soft_delete_academic_year(self, client, db, admin_token):
        ay = make_ay(db)
        resp = client.delete(f'/api/v1/academic-years/{ay.id}',
                             headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        # Should not appear in list
        list_resp = client.get('/api/v1/academic-years',
                               headers={'Authorization': f'Bearer {admin_token}'})
        assert len(list_resp.get_json()['data']['academic_years']) == 0
