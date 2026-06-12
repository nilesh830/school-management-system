"""
Sprint 3 — SMS-019 Class & Subject Catalog
"""
import pytest
from datetime import date
from app.models.academic_year import AcademicYear
from app.models.class_ import Class
from app.models.subject import Subject
from app.models.section import Section


def make_ay(db, name='2024-2025'):
    ay = AcademicYear(name=name, start_date=date(2024, 4, 1), end_date=date(2025, 3, 31))
    db.session.add(ay)
    db.session.commit()
    return ay


def make_class(db, ay_id=None, name='Grade 10', grade_level=10):
    c = Class(name=name, grade_level=grade_level, academic_year_id=ay_id)
    db.session.add(c)
    db.session.commit()
    return c


def make_subject(db, code='MATH101', name='Mathematics'):
    s = Subject(code=code, name=name, max_marks=100, pass_marks=35)
    db.session.add(s)
    db.session.commit()
    return s


# ---------------------------------------------------------------------------
# Class tests
# ---------------------------------------------------------------------------

class TestClassCreate:

    def test_admin_creates_class(self, client, db, admin_token):
        ay = make_ay(db)
        resp = client.post('/api/v1/classes', json={
            'name': 'Grade 10',
            'grade_level': 10,
            'academic_year_id': ay.id,
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 201
        assert resp.get_json()['data']['name'] == 'Grade 10'

    def test_missing_name_returns_400(self, client, admin_token):
        resp = client.post('/api/v1/classes', json={'grade_level': 10},
                           headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 400

    def test_teacher_cannot_create_class(self, client, teacher_token):
        resp = client.post('/api/v1/classes', json={'name': 'Grade 10', 'grade_level': 10},
                           headers={'Authorization': f'Bearer {teacher_token}'})
        assert resp.status_code == 403


class TestClassRead:

    def test_list_classes(self, client, db, admin_token):
        make_class(db, name='Grade 10')
        make_class(db, name='Grade 11', grade_level=11)
        resp = client.get('/api/v1/classes', headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        assert resp.get_json()['data']['meta']['total'] == 2

    def test_get_class_by_id(self, client, db, admin_token):
        c = make_class(db)
        resp = client.get(f'/api/v1/classes/{c.id}',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        assert resp.get_json()['data']['name'] == 'Grade 10'

    def test_get_nonexistent_class_404(self, client, admin_token):
        resp = client.get('/api/v1/classes/9999',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 404


class TestClassUpdate:

    def test_admin_updates_class(self, client, db, admin_token):
        c = make_class(db)
        resp = client.put(f'/api/v1/classes/{c.id}', json={'description': 'Senior secondary'},
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        assert resp.get_json()['data']['description'] == 'Senior secondary'


class TestClassDelete:

    def test_soft_delete_class_without_sections(self, client, db, admin_token):
        c = make_class(db)
        resp = client.delete(f'/api/v1/classes/{c.id}',
                             headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200

    def test_cannot_delete_class_with_active_sections(self, client, db, admin_token, teacher_user):
        from app.models.teacher import Teacher
        from datetime import date
        t = Teacher(user_id=teacher_user.id, employee_id='EMP001',
                    first_name='X', last_name='Y', joining_date=date(2022, 1, 1))
        db.session.add(t)
        db.session.flush()

        c = make_class(db)
        sec = Section(name='A', class_id=c.id, capacity=30)
        db.session.add(sec)
        db.session.commit()

        resp = client.delete(f'/api/v1/classes/{c.id}',
                             headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Subject tests
# ---------------------------------------------------------------------------

class TestSubjectCreate:

    def test_admin_creates_subject(self, client, admin_token):
        resp = client.post('/api/v1/subjects', json={
            'code': 'MATH101',
            'name': 'Mathematics',
            'max_marks': 100,
            'pass_marks': 35,
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 201
        data = resp.get_json()['data']
        assert data['code'] == 'MATH101'

    def test_code_is_uppercased(self, client, admin_token):
        resp = client.post('/api/v1/subjects', json={
            'code': 'sci201',
            'name': 'Science',
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 201
        assert resp.get_json()['data']['code'] == 'SCI201'

    def test_duplicate_code_returns_409(self, client, db, admin_token):
        make_subject(db, 'MATH101')
        resp = client.post('/api/v1/subjects', json={
            'code': 'MATH101',
            'name': 'Advanced Maths',
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 409

    def test_missing_code_returns_400(self, client, admin_token):
        resp = client.post('/api/v1/subjects', json={'name': 'Mathematics'},
                           headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 400


class TestSubjectRead:

    def test_list_subjects(self, client, db, admin_token):
        make_subject(db, 'MATH101', 'Mathematics')
        make_subject(db, 'SCI201', 'Science')
        resp = client.get('/api/v1/subjects', headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        assert resp.get_json()['data']['meta']['total'] == 2

    def test_search_subjects(self, client, db, admin_token):
        make_subject(db, 'MATH101', 'Mathematics')
        make_subject(db, 'ENG101', 'English')
        resp = client.get('/api/v1/subjects?search=math',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.get_json()['data']['meta']['total'] == 1


class TestSubjectDelete:

    def test_soft_delete_subject(self, client, db, admin_token):
        s = make_subject(db)
        resp = client.delete(f'/api/v1/subjects/{s.id}',
                             headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
