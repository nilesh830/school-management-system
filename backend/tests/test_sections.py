"""
Sprint 3 — SMS-020 Section Management
          SMS-021 Enroll Students into Sections
"""
import pytest
from datetime import date
from app.models.academic_year import AcademicYear
from app.models.class_ import Class
from app.models.section import Section
from app.models.student import Student
from app.models.user import User


def make_ay(db):
    ay = AcademicYear(name='2024-2025', start_date=date(2024, 4, 1), end_date=date(2025, 3, 31))
    db.session.add(ay)
    db.session.commit()
    return ay


def make_class(db, name='Grade 10'):
    c = Class(name=name, grade_level=10)
    db.session.add(c)
    db.session.commit()
    return c


def make_section(db, class_id, name='A'):
    sec = Section(name=name, class_id=class_id, capacity=40)
    db.session.add(sec)
    db.session.commit()
    return sec


def make_student(db, admission_no='ADM001'):
    u = User(email=f'{admission_no}@test.sms', role='student',
             first_name='Alice', last_name='Test')
    u.set_password('x')
    db.session.add(u)
    db.session.flush()
    s = Student(
        user_id=u.id,
        admission_no=admission_no,
        first_name='Alice',
        last_name='Test',
        date_of_birth=date(2010, 1, 1),
        gender='Female',
        admission_date=date(2024, 4, 1),
    )
    db.session.add(s)
    db.session.commit()
    return s


# ---------------------------------------------------------------------------
# SMS-020 — Section CRUD
# ---------------------------------------------------------------------------

class TestSectionCreate:

    def test_admin_creates_section(self, client, db, admin_token):
        c = make_class(db)
        resp = client.post('/api/v1/sections', json={
            'name': 'A',
            'class_id': c.id,
            'capacity': 40,
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 201
        data = resp.get_json()['data']
        assert data['name'] == 'A'
        assert data['class_id'] == c.id

    def test_duplicate_section_name_in_class_returns_409(self, client, db, admin_token):
        c = make_class(db)
        make_section(db, c.id, 'A')
        resp = client.post('/api/v1/sections', json={
            'name': 'A',
            'class_id': c.id,
            'capacity': 40,
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 409

    def test_same_name_in_different_class_is_ok(self, client, db, admin_token):
        c1 = make_class(db, 'Grade 10')
        c2 = make_class(db, 'Grade 11')
        make_section(db, c1.id, 'A')
        resp = client.post('/api/v1/sections', json={
            'name': 'A',
            'class_id': c2.id,
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 201

    def test_missing_class_id_returns_400(self, client, admin_token):
        resp = client.post('/api/v1/sections', json={'name': 'A'},
                           headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 400

    def test_teacher_cannot_create_section(self, client, teacher_token):
        resp = client.post('/api/v1/sections', json={'name': 'A', 'class_id': 1},
                           headers={'Authorization': f'Bearer {teacher_token}'})
        assert resp.status_code == 403


class TestSectionRead:

    def test_list_sections(self, client, db, admin_token):
        c = make_class(db)
        make_section(db, c.id, 'A')
        make_section(db, c.id, 'B')
        resp = client.get('/api/v1/sections', headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        assert resp.get_json()['data']['meta']['total'] == 2

    def test_list_sections_filter_by_class(self, client, db, admin_token):
        c1 = make_class(db, 'Grade 10')
        c2 = make_class(db, 'Grade 11')
        make_section(db, c1.id, 'A')
        make_section(db, c2.id, 'A')
        resp = client.get(f'/api/v1/sections?class_id={c1.id}',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.get_json()['data']['meta']['total'] == 1

    def test_get_section_by_id(self, client, db, admin_token):
        c = make_class(db)
        sec = make_section(db, c.id)
        resp = client.get(f'/api/v1/sections/{sec.id}',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['name'] == 'A'
        assert 'class_name' in data


class TestSectionDelete:

    def test_soft_delete_empty_section(self, client, db, admin_token):
        c = make_class(db)
        sec = make_section(db, c.id)
        resp = client.delete(f'/api/v1/sections/{sec.id}',
                             headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200

    def test_cannot_delete_section_with_enrolled_students(self, client, db, admin_token):
        c = make_class(db)
        sec = make_section(db, c.id)
        student = make_student(db)
        ay = make_ay(db)

        client.post(f'/api/v1/sections/{sec.id}/enroll', json={
            'student_id': student.id,
            'academic_year_id': ay.id,
        }, headers={'Authorization': f'Bearer {admin_token}'})

        resp = client.delete(f'/api/v1/sections/{sec.id}',
                             headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# SMS-021 — Student enrollment
# ---------------------------------------------------------------------------

class TestStudentEnrollment:

    def test_enroll_student_in_section(self, client, db, admin_token):
        c = make_class(db)
        sec = make_section(db, c.id)
        student = make_student(db)
        ay = make_ay(db)

        resp = client.post(f'/api/v1/sections/{sec.id}/enroll', json={
            'student_id': student.id,
            'academic_year_id': ay.id,
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 201
        data = resp.get_json()['data']
        assert data['section_id'] == sec.id
        assert data['student_id'] == student.id
        assert data['is_current'] is True

    def test_enroll_closes_previous_enrollment(self, client, db, admin_token):
        c = make_class(db)
        sec1 = make_section(db, c.id, 'A')
        sec2 = make_section(db, c.id, 'B')
        student = make_student(db)
        ay = make_ay(db)

        # First enrollment
        client.post(f'/api/v1/sections/{sec1.id}/enroll', json={
            'student_id': student.id,
            'academic_year_id': ay.id,
        }, headers={'Authorization': f'Bearer {admin_token}'})

        # Second enrollment (should close first)
        resp = client.post(f'/api/v1/sections/{sec2.id}/enroll', json={
            'student_id': student.id,
            'academic_year_id': ay.id,
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 201

        # First enrollment should be closed
        from app.models.student_section import StudentSection
        from app import db as _db
        old = _db.session.query(StudentSection).filter_by(
            student_id=student.id, section_id=sec1.id
        ).first()
        assert old is not None
        assert old.is_current is False

    def test_unenroll_student(self, client, db, admin_token):
        c = make_class(db)
        sec = make_section(db, c.id)
        student = make_student(db)
        ay = make_ay(db)

        client.post(f'/api/v1/sections/{sec.id}/enroll', json={
            'student_id': student.id,
            'academic_year_id': ay.id,
        }, headers={'Authorization': f'Bearer {admin_token}'})

        resp = client.delete(f'/api/v1/sections/{sec.id}/students/{student.id}',
                             headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200

    def test_enroll_missing_student_id_400(self, client, db, admin_token):
        c = make_class(db)
        sec = make_section(db, c.id)
        resp = client.post(f'/api/v1/sections/{sec.id}/enroll', json={},
                           headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 400

    def test_enroll_nonexistent_student_404(self, client, db, admin_token):
        c = make_class(db)
        sec = make_section(db, c.id)
        resp = client.post(f'/api/v1/sections/{sec.id}/enroll', json={
            'student_id': 9999,
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 404
