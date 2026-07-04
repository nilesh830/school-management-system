"""
SMS-066 v2 — Student opt-in for optional flat fees.
Tests the /api/v1/fee-structures/<id>/opt-in endpoints (GET/POST/DELETE) and the
FeeStructureService opt-in methods: add (upsert/reactivate), remove (soft-delete),
list, validation and RBAC.
"""
import pytest
from datetime import date

from app.models.class_ import Class
from app.models.academic_year import AcademicYear
from app.models.user import User
from app.models.student import Student
from app.models.fee_structure import FeeStructure
from app.models.student_fee_optin import StudentFeeOptin


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_class(db, name='Grade 1', grade_level=1):
    c = Class(name=name, grade_level=grade_level)
    db.session.add(c)
    db.session.commit()
    return c


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


_seq = {'n': 0}


def make_student(db, admission_no):
    _seq['n'] += 1
    u = User(email=f'optin_stu_{_seq["n"]}@test.sms', role='student',
             first_name='Opt', last_name='Student')
    u.set_password('Student@123')
    db.session.add(u)
    db.session.flush()
    s = Student(
        user_id=u.id,
        admission_no=admission_no,
        first_name='Opt',
        last_name='Student',
        date_of_birth=date(2012, 1, 1),
        gender='Male',
        admission_date=date(2024, 6, 1),
        is_active=True,
    )
    db.session.add(s)
    db.session.commit()
    return s


def make_fee_structure(db, class_id, academic_year_id, **kwargs):
    defaults = dict(
        fee_type='Hostel',
        amount=3000.00,
        is_recurring=False,
        frequency='one_time',
        due_date=date(2024, 7, 31),
        applicability='optional',
        source_kind='flat',
        transport_route_id=None,
    )
    defaults.update(kwargs)
    fs = FeeStructure(class_id=class_id, academic_year_id=academic_year_id, **defaults)
    db.session.add(fs)
    db.session.commit()
    return fs


def _auth(token):
    return {'Authorization': f'Bearer {token}'}


# ---------------------------------------------------------------------------
# 1. Add opt-ins (POST)
# ---------------------------------------------------------------------------

class TestAddOptins:

    def test_add_success(self, client, admin_token, db):
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id)
        s1 = make_student(db, 'ADM-OPT-001')
        s2 = make_student(db, 'ADM-OPT-002')

        resp = client.post(
            f'/api/v1/fee-structures/{fs.id}/opt-in',
            json={'student_ids': [s1.id, s2.id], 'amount_override': 5000.00},
            headers=_auth(admin_token),
        )

        assert resp.status_code == 201
        body = resp.get_json()
        assert body['success'] is True
        assert sorted(body['data']['added']) == sorted([s1.id, s2.id])
        assert body['data']['reactivated'] == []
        assert body['data']['not_found'] == []

        rows = db.session.query(StudentFeeOptin).filter_by(fee_structure_id=fs.id).all()
        assert len(rows) == 2
        assert all(float(r.amount_override) == 5000.00 for r in rows)
        assert all(r.opted_in_by is not None for r in rows)

    def test_add_reports_not_found(self, client, admin_token, db):
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id)
        s1 = make_student(db, 'ADM-OPT-003')

        resp = client.post(
            f'/api/v1/fee-structures/{fs.id}/opt-in',
            json={'student_ids': [s1.id, 999999]},
            headers=_auth(admin_token),
        )

        assert resp.status_code == 201
        data = resp.get_json()['data']
        assert data['added'] == [s1.id]
        assert data['not_found'] == [999999]

    def test_readd_reactivates(self, client, admin_token, db):
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id)
        s1 = make_student(db, 'ADM-OPT-004')

        client.post(f'/api/v1/fee-structures/{fs.id}/opt-in',
                    json={'student_ids': [s1.id]}, headers=_auth(admin_token))
        client.delete(f'/api/v1/fee-structures/{fs.id}/opt-in',
                       json={'student_ids': [s1.id]}, headers=_auth(admin_token))

        resp = client.post(f'/api/v1/fee-structures/{fs.id}/opt-in',
                           json={'student_ids': [s1.id], 'amount_override': 4000.00},
                           headers=_auth(admin_token))

        assert resp.status_code == 201
        data = resp.get_json()['data']
        assert data['reactivated'] == [s1.id]
        assert data['added'] == []

        row = db.session.query(StudentFeeOptin).filter_by(
            fee_structure_id=fs.id, student_id=s1.id).one()
        assert row.is_active is True
        assert float(row.amount_override) == 4000.00

    def test_add_rejects_mandatory_structure(self, client, admin_token, db):
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, applicability='mandatory')
        s1 = make_student(db, 'ADM-OPT-005')

        resp = client.post(f'/api/v1/fee-structures/{fs.id}/opt-in',
                           json={'student_ids': [s1.id]}, headers=_auth(admin_token))
        assert resp.status_code == 422

    def test_add_validation_empty_list(self, client, admin_token, db):
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id)

        resp = client.post(f'/api/v1/fee-structures/{fs.id}/opt-in',
                           json={'student_ids': []}, headers=_auth(admin_token))
        assert resp.status_code == 422

    def test_add_missing_structure_404(self, client, admin_token, db):
        s1 = make_student(db, 'ADM-OPT-006')
        resp = client.post('/api/v1/fee-structures/999999/opt-in',
                           json={'student_ids': [s1.id]}, headers=_auth(admin_token))
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 2. List opt-ins (GET)
# ---------------------------------------------------------------------------

class TestListOptins:

    def test_list_returns_active_only(self, client, admin_token, db):
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id)
        s1 = make_student(db, 'ADM-OPT-010')
        s2 = make_student(db, 'ADM-OPT-011')

        client.post(f'/api/v1/fee-structures/{fs.id}/opt-in',
                    json={'student_ids': [s1.id, s2.id], 'amount_override': 5000.00},
                    headers=_auth(admin_token))
        client.delete(f'/api/v1/fee-structures/{fs.id}/opt-in',
                       json={'student_ids': [s2.id]}, headers=_auth(admin_token))

        resp = client.get(f'/api/v1/fee-structures/{fs.id}/opt-in', headers=_auth(admin_token))
        assert resp.status_code == 200
        optins = resp.get_json()['data']['optins']
        assert len(optins) == 1
        assert optins[0]['student_id'] == s1.id
        assert optins[0]['admission_no'] == 'ADM-OPT-010'
        assert optins[0]['amount_override'] == 5000.00


# ---------------------------------------------------------------------------
# 3. Remove opt-ins (DELETE) — soft delete
# ---------------------------------------------------------------------------

class TestRemoveOptins:

    def test_remove_soft_deletes(self, client, admin_token, db):
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id)
        s1 = make_student(db, 'ADM-OPT-020')

        client.post(f'/api/v1/fee-structures/{fs.id}/opt-in',
                    json={'student_ids': [s1.id]}, headers=_auth(admin_token))

        resp = client.delete(f'/api/v1/fee-structures/{fs.id}/opt-in',
                              json={'student_ids': [s1.id]}, headers=_auth(admin_token))
        assert resp.status_code == 200
        assert resp.get_json()['data']['removed'] == [s1.id]

        row = db.session.query(StudentFeeOptin).filter_by(
            fee_structure_id=fs.id, student_id=s1.id).one()
        assert row.is_active is False  # row kept for audit trail


# ---------------------------------------------------------------------------
# 4. RBAC — only admin
# ---------------------------------------------------------------------------

class TestOptinRbac:

    def test_teacher_forbidden(self, client, teacher_token, db):
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id)
        s1 = make_student(db, 'ADM-OPT-030')

        resp = client.post(f'/api/v1/fee-structures/{fs.id}/opt-in',
                           json={'student_ids': [s1.id]}, headers=_auth(teacher_token))
        assert resp.status_code == 403

    def test_unauthenticated_rejected(self, client, db):
        resp = client.get('/api/v1/fee-structures/1/opt-in')
        assert resp.status_code in (401, 422)
