"""
Sprint 5 — SMS-029 Create Exam Definitions
Tests: CRUD operations, validation, authorization, filters
"""
import pytest
from datetime import date
from app.models.class_ import Class
from app.models.section import Section
from app.models.academic_year import AcademicYear


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_class(db, name='Grade 1', grade_level=1):
    c = Class(name=name, grade_level=grade_level)
    db.session.add(c)
    db.session.commit()
    return c


def make_section(db, class_id, name='A', is_active=True):
    s = Section(name=name, class_id=class_id, is_active=is_active)
    db.session.add(s)
    db.session.commit()
    return s


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


def _get_token(client, email, password):
    r = client.post(
        '/api/v1/auth/login',
        json={'email': email, 'password': password, 'school_slug': 'test'},
    )
    return r.get_json()['data']['access_token']


# ---------------------------------------------------------------------------
# TC-1: Admin creates exam successfully → 201, data returned
# ---------------------------------------------------------------------------

class TestCreateExam:

    def test_admin_creates_exam(self, client, admin_token, db):
        cls = make_class(db)
        section = make_section(db, cls.id)
        ay = make_academic_year(db)

        resp = client.post('/api/v1/exams', json={
            'name': 'Midterm 2024',
            'term': 'Term 1',
            'exam_type': 'midterm',
            'section_id': section.id,
            'academic_year_id': ay.id,
        }, headers={'Authorization': f'Bearer {admin_token}'})

        assert resp.status_code == 201
        body = resp.get_json()
        assert body['success'] is True
        assert body['data']['name'] == 'Midterm 2024'
        assert body['data']['exam_type'] == 'midterm'
        assert body['data']['section_id'] == section.id
        assert body['data']['academic_year_id'] == ay.id

    # TC-2: Create exam with invalid exam_type → 422
    def test_invalid_exam_type_returns_422(self, client, admin_token, db):
        cls = make_class(db, name='Grade 2', grade_level=2)
        section = make_section(db, cls.id, name='B')
        ay = make_academic_year(db, name='2024-2025-B')

        resp = client.post('/api/v1/exams', json={
            'name': 'Bad Exam',
            'term': 'Term 1',
            'exam_type': 'quarterly',  # not in allowed list
            'section_id': section.id,
            'academic_year_id': ay.id,
        }, headers={'Authorization': f'Bearer {admin_token}'})

        assert resp.status_code == 422
        body = resp.get_json()
        assert body['success'] is False

    # TC-3: Duplicate name + section + academic_year → 409
    def test_duplicate_exam_returns_409(self, client, admin_token, db):
        cls = make_class(db, name='Grade 3', grade_level=3)
        section = make_section(db, cls.id, name='C')
        ay = make_academic_year(db, name='2025-2026')

        payload = {
            'name': 'Final Exam',
            'term': 'Term 2',
            'exam_type': 'final',
            'section_id': section.id,
            'academic_year_id': ay.id,
        }
        # First creation succeeds
        r1 = client.post('/api/v1/exams', json=payload,
                         headers={'Authorization': f'Bearer {admin_token}'})
        assert r1.status_code == 201

        # Second with same name + section + academic_year should conflict
        r2 = client.post('/api/v1/exams', json=payload,
                         headers={'Authorization': f'Bearer {admin_token}'})
        assert r2.status_code == 409
        assert r2.get_json()['success'] is False


# ---------------------------------------------------------------------------
# TC-4: List exams — admin sees all, filter by section_id works
# ---------------------------------------------------------------------------

class TestListExams:

    def test_admin_lists_all_exams(self, client, admin_token, db):
        cls = make_class(db, name='Grade 4', grade_level=4)
        section_a = make_section(db, cls.id, name='D')
        section_b = make_section(db, cls.id, name='E')
        ay = make_academic_year(db, name='2026-2027')

        for sname, sid, etype in [
            ('Exam A', section_a.id, 'midterm'),
            ('Exam B', section_b.id, 'final'),
        ]:
            client.post('/api/v1/exams', json={
                'name': sname, 'term': 'Term 1', 'exam_type': etype,
                'section_id': sid, 'academic_year_id': ay.id,
            }, headers={'Authorization': f'Bearer {admin_token}'})

        resp = client.get('/api/v1/exams',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        assert len(body['data']['exams']) == 2

    def test_filter_by_section_id(self, client, admin_token, db):
        cls = make_class(db, name='Grade 5', grade_level=5)
        section_a = make_section(db, cls.id, name='F')
        section_b = make_section(db, cls.id, name='G')
        ay = make_academic_year(db, name='2027-2028')

        client.post('/api/v1/exams', json={
            'name': 'Exam F', 'term': 'Term 1', 'exam_type': 'midterm',
            'section_id': section_a.id, 'academic_year_id': ay.id,
        }, headers={'Authorization': f'Bearer {admin_token}'})
        client.post('/api/v1/exams', json={
            'name': 'Exam G', 'term': 'Term 1', 'exam_type': 'final',
            'section_id': section_b.id, 'academic_year_id': ay.id,
        }, headers={'Authorization': f'Bearer {admin_token}'})

        resp = client.get(
            f'/api/v1/exams?section_id={section_a.id}',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 200
        exams = resp.get_json()['data']['exams']
        assert len(exams) == 1
        assert exams[0]['section_id'] == section_a.id


# ---------------------------------------------------------------------------
# TC-5: Teacher can list exams (GET /api/v1/exams) → 200
# ---------------------------------------------------------------------------

class TestTeacherListExams:

    def test_teacher_can_list_exams(self, client, teacher_user, db):
        token = _get_token(client, 'teacher@test.sms', 'Teacher@123')

        cls = make_class(db, name='Grade 6', grade_level=6)
        section = make_section(db, cls.id, name='H')
        ay = make_academic_year(db, name='2028-2029')

        # Seed an exam directly via model to avoid admin-only route dependency
        from app.models.exam import Exam
        exam = Exam(
            name='Teacher Test Exam',
            term='Term 1',
            exam_type='unit_test',
            section_id=section.id,
            academic_year_id=ay.id,
        )
        db.session.add(exam)
        db.session.commit()

        resp = client.get('/api/v1/exams',
                          headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        assert len(body['data']['exams']) >= 1


# ---------------------------------------------------------------------------
# TC-6: Teacher cannot create exam (POST /api/v1/exams) → 403
# ---------------------------------------------------------------------------

class TestTeacherCannotCreateExam:

    def test_teacher_create_returns_403(self, client, teacher_user, db):
        token = _get_token(client, 'teacher@test.sms', 'Teacher@123')

        cls = make_class(db, name='Grade 7', grade_level=7)
        section = make_section(db, cls.id, name='I')
        ay = make_academic_year(db, name='2029-2030')

        resp = client.post('/api/v1/exams', json={
            'name': 'Unauthorized Exam',
            'term': 'Term 1',
            'exam_type': 'midterm',
            'section_id': section.id,
            'academic_year_id': ay.id,
        }, headers={'Authorization': f'Bearer {token}'})

        assert resp.status_code == 403
        assert resp.get_json()['success'] is False


# ---------------------------------------------------------------------------
# TC-7: Get single exam by id → 200
# ---------------------------------------------------------------------------

class TestGetSingleExam:

    def test_get_exam_by_id(self, client, admin_token, db):
        cls = make_class(db, name='Grade 8', grade_level=8)
        section = make_section(db, cls.id, name='J')
        ay = make_academic_year(db, name='2030-2031')

        create_resp = client.post('/api/v1/exams', json={
            'name': 'Practical Exam',
            'term': 'Term 2',
            'exam_type': 'practical',
            'section_id': section.id,
            'academic_year_id': ay.id,
            'conducted_date': '2030-10-15',
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert create_resp.status_code == 201
        exam_id = create_resp.get_json()['data']['id']

        resp = client.get(f'/api/v1/exams/{exam_id}',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        assert body['data']['id'] == exam_id
        assert body['data']['exam_type'] == 'practical'
        assert body['data']['conducted_date'] == '2030-10-15'

    # TC-8: Get non-existent exam → 404
    def test_get_nonexistent_exam_returns_404(self, client, admin_token):
        resp = client.get('/api/v1/exams/99999',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 404
        assert resp.get_json()['success'] is False


# ---------------------------------------------------------------------------
# TC-9: Admin updates exam → 200
# ---------------------------------------------------------------------------

class TestUpdateExam:

    def test_admin_updates_exam(self, client, admin_token, db):
        cls = make_class(db, name='Grade 9', grade_level=9)
        section = make_section(db, cls.id, name='K')
        ay = make_academic_year(db, name='2031-2032')

        create_resp = client.post('/api/v1/exams', json={
            'name': 'Unit Test 1',
            'term': 'Term 1',
            'exam_type': 'unit_test',
            'section_id': section.id,
            'academic_year_id': ay.id,
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert create_resp.status_code == 201
        exam_id = create_resp.get_json()['data']['id']

        resp = client.put(f'/api/v1/exams/{exam_id}', json={
            'name': 'Unit Test 1 (Revised)',
            'exam_type': 'midterm',
            'is_active': False,
        }, headers={'Authorization': f'Bearer {admin_token}'})

        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        assert body['data']['name'] == 'Unit Test 1 (Revised)'
        assert body['data']['exam_type'] == 'midterm'
        assert body['data']['is_active'] is False

    def test_update_nonexistent_exam_returns_404(self, client, admin_token):
        resp = client.put('/api/v1/exams/88888', json={'name': 'Ghost'},
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# TC-10: Student cannot access exams → 403
# ---------------------------------------------------------------------------

class TestStudentCannotAccessExams:

    def test_student_list_returns_403(self, client, student_user):
        token = _get_token(client, 'alice@test.sms', 'Student@123')

        resp = client.get('/api/v1/exams',
                          headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 403
        assert resp.get_json()['success'] is False

    def test_student_create_returns_403(self, client, student_user, db):
        token = _get_token(client, 'alice@test.sms', 'Student@123')

        cls = make_class(db, name='Grade 10', grade_level=10)
        section = make_section(db, cls.id, name='L')
        ay = make_academic_year(db, name='2032-2033')

        resp = client.post('/api/v1/exams', json={
            'name': 'Student Sneak',
            'term': 'Term 1',
            'exam_type': 'midterm',
            'section_id': section.id,
            'academic_year_id': ay.id,
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 403
