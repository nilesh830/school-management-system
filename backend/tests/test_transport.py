"""
SMS-061 / SMS-062 — Transport Management
Tests: route & vehicle CRUD, student assignment/reassignment/unassignment, RBAC.
"""
import pytest
from datetime import date

from app.models.user import User
from app.models.student import Student
from app.models.academic_year import AcademicYear
from app.models.transport_route import TransportRoute
from app.models.transport_vehicle import TransportVehicle
from app.models.student_transport import StudentTransport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def auth(token):
    return {'Authorization': f'Bearer {token}'}


def make_route(db, name='Route A', description='North Zone', stops=None):
    r = TransportRoute(name=name, description=description, stops_json=stops or ['Stop 1', 'Stop 2'])
    db.session.add(r)
    db.session.commit()
    return r


def make_academic_year(db, name='2024-2025'):
    ay = AcademicYear(
        name=name,
        start_date=date(2024, 6, 1),
        end_date=date(2025, 5, 31),
        is_current=True,
        is_active=True,
    )
    db.session.add(ay)
    db.session.commit()
    return ay


def make_student(db, admission_no='ADM-T-001', email='s1@test.sms'):
    u = User(email=email, role='student', first_name='Sam', last_name='Lee')
    u.set_password('Student@123')
    db.session.add(u)
    db.session.flush()
    s = Student(
        user_id=u.id,
        admission_no=admission_no,
        first_name='Sam',
        last_name='Lee',
        date_of_birth=date(2012, 1, 1),
        gender='Male',
        admission_date=date(2024, 6, 1),
    )
    db.session.add(s)
    db.session.commit()
    return s


# ===========================================================================
# SMS-061 — Routes
# ===========================================================================

class TestRoutes:

    def test_create_route(self, client, admin_token):
        resp = client.post('/api/v1/transport/routes', json={
            'name': 'Route A', 'description': 'North Zone', 'stops': ['Stop 1', 'Stop 2'],
        }, headers=auth(admin_token))
        assert resp.status_code == 201
        data = resp.get_json()['data']
        assert data['name'] == 'Route A'
        assert data['stops'] == ['Stop 1', 'Stop 2']
        assert data['is_active'] is True

    def test_create_route_validation(self, client, admin_token):
        resp = client.post('/api/v1/transport/routes', json={'description': 'no name'},
                           headers=auth(admin_token))
        assert resp.status_code == 422

    def test_create_route_forbidden_for_teacher(self, client, teacher_token):
        resp = client.post('/api/v1/transport/routes', json={'name': 'Route X'},
                           headers=auth(teacher_token))
        assert resp.status_code == 403

    def test_list_routes(self, client, admin_token, db):
        make_route(db, name='Route A')
        make_route(db, name='Route B')
        resp = client.get('/api/v1/transport/routes', headers=auth(admin_token))
        assert resp.status_code == 200
        routes = resp.get_json()['data']['routes']
        assert len(routes) == 2

    def test_list_routes_teacher_allowed(self, client, teacher_token, db):
        make_route(db, name='Route A')
        resp = client.get('/api/v1/transport/routes', headers=auth(teacher_token))
        assert resp.status_code == 200

    def test_get_route(self, client, admin_token, db):
        r = make_route(db)
        resp = client.get(f'/api/v1/transport/routes/{r.id}', headers=auth(admin_token))
        assert resp.status_code == 200
        assert resp.get_json()['data']['id'] == r.id

    def test_get_route_404(self, client, admin_token):
        resp = client.get('/api/v1/transport/routes/999', headers=auth(admin_token))
        assert resp.status_code == 404

    def test_update_route(self, client, admin_token, db):
        r = make_route(db)
        resp = client.put(f'/api/v1/transport/routes/{r.id}', json={
            'name': 'Route A Updated', 'stops': ['S1', 'S2', 'S3'],
        }, headers=auth(admin_token))
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['name'] == 'Route A Updated'
        assert data['stops'] == ['S1', 'S2', 'S3']

    def test_delete_route_soft(self, client, admin_token, db):
        r = make_route(db)
        resp = client.delete(f'/api/v1/transport/routes/{r.id}', headers=auth(admin_token))
        assert resp.status_code == 200
        # Soft delete: excluded from active listing
        listing = client.get('/api/v1/transport/routes', headers=auth(admin_token))
        assert all(rt['id'] != r.id for rt in listing.get_json()['data']['routes'])


# ===========================================================================
# SMS-061 — Vehicles
# ===========================================================================

class TestVehicles:

    def test_create_vehicle(self, client, admin_token, db):
        r = make_route(db)
        resp = client.post('/api/v1/transport/vehicles', json={
            'registration_no': 'MH01AB1234', 'capacity': 40,
            'driver_name': 'Ram', 'driver_phone': '9999999999', 'route_id': r.id,
        }, headers=auth(admin_token))
        assert resp.status_code == 201
        data = resp.get_json()['data']
        assert data['registration_no'] == 'MH01AB1234'
        assert data['route_id'] == r.id
        assert data['route_name'] == r.name

    def test_create_vehicle_duplicate_409(self, client, admin_token, db):
        client.post('/api/v1/transport/vehicles', json={
            'registration_no': 'MH01AB1234', 'capacity': 40,
        }, headers=auth(admin_token))
        resp = client.post('/api/v1/transport/vehicles', json={
            'registration_no': 'MH01AB1234', 'capacity': 30,
        }, headers=auth(admin_token))
        assert resp.status_code == 409

    def test_create_vehicle_bad_route_404(self, client, admin_token):
        resp = client.post('/api/v1/transport/vehicles', json={
            'registration_no': 'MH02CD5678', 'capacity': 40, 'route_id': 999,
        }, headers=auth(admin_token))
        assert resp.status_code == 404

    def test_create_vehicle_invalid_capacity_422(self, client, admin_token):
        resp = client.post('/api/v1/transport/vehicles', json={
            'registration_no': 'MH03EF', 'capacity': 0,
        }, headers=auth(admin_token))
        assert resp.status_code == 422

    def test_list_vehicles_filter_by_route(self, client, admin_token, db):
        r1 = make_route(db, name='R1')
        r2 = make_route(db, name='R2')
        for reg, rid in [('A1', r1.id), ('A2', r1.id), ('B1', r2.id)]:
            client.post('/api/v1/transport/vehicles', json={
                'registration_no': reg, 'capacity': 40, 'route_id': rid,
            }, headers=auth(admin_token))
        resp = client.get(f'/api/v1/transport/vehicles?route_id={r1.id}', headers=auth(admin_token))
        assert resp.status_code == 200
        vehicles = resp.get_json()['data']['vehicles']
        assert len(vehicles) == 2
        assert all(v['route_id'] == r1.id for v in vehicles)

    def test_update_vehicle(self, client, admin_token, db):
        client.post('/api/v1/transport/vehicles', json={
            'registration_no': 'MH09XX0001', 'capacity': 40,
        }, headers=auth(admin_token))
        vid = client.get('/api/v1/transport/vehicles', headers=auth(admin_token)).get_json()['data']['vehicles'][0]['id']
        resp = client.put(f'/api/v1/transport/vehicles/{vid}', json={
            'capacity': 50, 'driver_name': 'Shyam',
        }, headers=auth(admin_token))
        assert resp.status_code == 200
        assert resp.get_json()['data']['capacity'] == 50


# ===========================================================================
# SMS-062 — Student assignments
# ===========================================================================

class TestAssignments:

    def test_assign_student(self, client, admin_token, db):
        r = make_route(db)
        ay = make_academic_year(db)
        s = make_student(db)
        resp = client.post('/api/v1/transport/assignments', json={
            'student_id': s.id, 'route_id': r.id,
            'pickup_stop': 'Stop 1', 'drop_stop': 'Stop 2', 'academic_year_id': ay.id,
        }, headers=auth(admin_token))
        assert resp.status_code == 201
        data = resp.get_json()['data']
        assert data['student_id'] == s.id
        assert data['route_id'] == r.id
        assert data['student_name'] == 'Sam Lee'

    def test_reassign_closes_old(self, client, admin_token, db):
        r1 = make_route(db, name='R1')
        r2 = make_route(db, name='R2')
        ay = make_academic_year(db)
        s = make_student(db)
        client.post('/api/v1/transport/assignments', json={
            'student_id': s.id, 'route_id': r1.id, 'academic_year_id': ay.id,
        }, headers=auth(admin_token))
        # Reassign to a different route — same student+year
        resp = client.post('/api/v1/transport/assignments', json={
            'student_id': s.id, 'route_id': r2.id, 'pickup_stop': 'New Stop',
            'academic_year_id': ay.id,
        }, headers=auth(admin_token))
        assert resp.status_code == 201
        assert resp.get_json()['data']['route_id'] == r2.id
        # Exactly one row exists for that student+year (upsert, no duplicate)
        rows = db.session.query(StudentTransport).filter_by(
            student_id=s.id, academic_year_id=ay.id).all()
        assert len(rows) == 1
        assert rows[0].route_id == r2.id
        assert rows[0].pickup_stop == 'New Stop'

    def test_assign_bad_student_404(self, client, admin_token, db):
        r = make_route(db)
        ay = make_academic_year(db)
        resp = client.post('/api/v1/transport/assignments', json={
            'student_id': 999, 'route_id': r.id, 'academic_year_id': ay.id,
        }, headers=auth(admin_token))
        assert resp.status_code == 404

    def test_assign_forbidden_for_teacher(self, client, teacher_token, db):
        r = make_route(db)
        ay = make_academic_year(db)
        s = make_student(db)
        resp = client.post('/api/v1/transport/assignments', json={
            'student_id': s.id, 'route_id': r.id, 'academic_year_id': ay.id,
        }, headers=auth(teacher_token))
        assert resp.status_code == 403

    def test_list_assignments_by_route(self, client, admin_token, db):
        r1 = make_route(db, name='R1')
        r2 = make_route(db, name='R2')
        ay = make_academic_year(db)
        s1 = make_student(db, admission_no='ADM-T-001', email='s1@test.sms')
        s2 = make_student(db, admission_no='ADM-T-002', email='s2@test.sms')
        client.post('/api/v1/transport/assignments', json={
            'student_id': s1.id, 'route_id': r1.id, 'academic_year_id': ay.id,
        }, headers=auth(admin_token))
        client.post('/api/v1/transport/assignments', json={
            'student_id': s2.id, 'route_id': r2.id, 'academic_year_id': ay.id,
        }, headers=auth(admin_token))
        resp = client.get(f'/api/v1/transport/assignments?route_id={r1.id}', headers=auth(admin_token))
        assert resp.status_code == 200
        assignments = resp.get_json()['data']['assignments']
        assert len(assignments) == 1
        assert assignments[0]['student_id'] == s1.id

    def test_unassign_student(self, client, admin_token, db):
        r = make_route(db)
        ay = make_academic_year(db)
        s = make_student(db)
        created = client.post('/api/v1/transport/assignments', json={
            'student_id': s.id, 'route_id': r.id, 'academic_year_id': ay.id,
        }, headers=auth(admin_token)).get_json()['data']
        resp = client.delete(f"/api/v1/transport/assignments/{created['id']}", headers=auth(admin_token))
        assert resp.status_code == 200
        # No longer in active listing
        listing = client.get('/api/v1/transport/assignments', headers=auth(admin_token))
        assert listing.get_json()['data']['assignments'] == []

    def test_get_student_transport(self, client, admin_token, db):
        r = make_route(db)
        ay = make_academic_year(db)
        s = make_student(db)
        client.post('/api/v1/transport/assignments', json={
            'student_id': s.id, 'route_id': r.id, 'academic_year_id': ay.id,
        }, headers=auth(admin_token))
        resp = client.get(f'/api/v1/students/{s.id}/transport', headers=auth(admin_token))
        assert resp.status_code == 200
        assert resp.get_json()['data']['transport']['route_id'] == r.id

    def test_get_student_transport_none(self, client, admin_token, db):
        s = make_student(db)
        resp = client.get(f'/api/v1/students/{s.id}/transport', headers=auth(admin_token))
        assert resp.status_code == 200
        assert resp.get_json()['data']['transport'] is None
