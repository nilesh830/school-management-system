"""
SMS-034 — Marks Edit & Approval Workflow
pytest test suite

Tests cover:
  TC-1  Update marks on a draft result → 200, marks/grade/gpa recalculated
  TC-2  Update marks on a finalized result → 409 Conflict
  TC-3  Update marks with wrong exam_id → 404
  TC-4  marks_obtained > max_marks → 422
  TC-5  Finalize exam with draft results → 200, finalized_count > 0
  TC-6  Finalize exam with no drafts → 400
  TC-7  Teacher cannot call finalize → 403
  TC-8  Finalize then try to edit → 409
"""
import pytest
from datetime import date

from app.models.class_ import Class
from app.models.section import Section
from app.models.academic_year import AcademicYear
from app.models.subject import Subject
from app.models.student import Student
from app.models.exam import Exam
from app.models.exam_result import ExamResult
from app.models.user import User


# ---------------------------------------------------------------------------
# Local helpers (same pattern as test_exam_marks.py)
# ---------------------------------------------------------------------------

def _get_token(client, email, password):
    r = client.post(
        '/api/v1/auth/login',
        json={'email': email, 'password': password, 'school_slug': 'test'},
    )
    return r.get_json()['data']['access_token']


def make_class(db, name='MA Class', grade_level=10):
    c = Class(name=name, grade_level=grade_level)
    db.session.add(c)
    db.session.commit()
    return c


def make_section(db, class_id, name='MA'):
    s = Section(name=name, class_id=class_id, is_active=True)
    db.session.add(s)
    db.session.commit()
    return s


def make_academic_year(db, name='2025-2026-ma'):
    ay = AcademicYear(
        name=name,
        start_date=date(2025, 6, 1),
        end_date=date(2026, 5, 31),
        is_current=True,
        is_active=True,
    )
    db.session.add(ay)
    db.session.commit()
    return ay


def make_subject(db, code='MA_SUBJ', max_marks=100):
    s = Subject(name='Maths Approval', code=code, max_marks=max_marks, pass_marks=35)
    db.session.add(s)
    db.session.commit()
    return s


def make_exam(db, section_id, academic_year_id):
    e = Exam(
        name='Approval Test Exam',
        term='Term 1',
        exam_type='midterm',
        section_id=section_id,
        academic_year_id=academic_year_id,
        is_active=True,
    )
    db.session.add(e)
    db.session.commit()
    return e


def make_student(db, user_id, admission_no='ADM-MA-001'):
    s = Student(
        user_id=user_id,
        admission_no=admission_no,
        first_name='Approval',
        last_name='Student',
        date_of_birth=date(2010, 5, 1),
        gender='Male',
        admission_date=date(2025, 6, 1),
    )
    db.session.add(s)
    db.session.commit()
    return s


def make_draft_result(db, exam_id, student_id, subject_id, marks=75.0, max_marks=100.0):
    """Insert a draft ExamResult directly and return it."""
    from app.services.exam_service import ExamService
    grade, gpa = ExamService.calculate_grade(marks, max_marks)
    r = ExamResult(
        exam_id=exam_id,
        student_id=student_id,
        subject_id=subject_id,
        marks_obtained=marks,
        grade=grade,
        gpa=gpa,
        status='draft',
    )
    db.session.add(r)
    db.session.commit()
    return r


def make_finalized_result(db, exam_id, student_id, subject_id, marks=80.0, max_marks=100.0):
    """Insert an already-finalized ExamResult directly and return it."""
    from app.services.exam_service import ExamService
    grade, gpa = ExamService.calculate_grade(marks, max_marks)
    r = ExamResult(
        exam_id=exam_id,
        student_id=student_id,
        subject_id=subject_id,
        marks_obtained=marks,
        grade=grade,
        gpa=gpa,
        status='finalized',
    )
    db.session.add(r)
    db.session.commit()
    return r


# ---------------------------------------------------------------------------
# Shared fixture: a teacher user (for TC-7)
# ---------------------------------------------------------------------------

@pytest.fixture
def teacher_user_ma(db):
    u = User(
        email='teacher_ma@test.sms',
        role='teacher',
        first_name='Teacher',
        last_name='MA',
    )
    u.set_password('Teacher@123')
    db.session.add(u)
    db.session.commit()
    return u


# ---------------------------------------------------------------------------
# TC-1: Update marks on a draft result → 200, values recalculated
# ---------------------------------------------------------------------------

class TestUpdateMarksDraftSuccess:

    def test_update_marks_draft_success(self, client, admin_token, db):
        cls = make_class(db, 'MA Class TC1', 11)
        sec = make_section(db, cls.id, 'TC1')
        ay = make_academic_year(db, 'MA-AY-TC1')
        subj = make_subject(db, 'MA_TC1', 100)
        exam = make_exam(db, sec.id, ay.id)

        u = User(email='stu_ma_tc1@test.sms', role='student', first_name='S', last_name='1')
        u.set_password('x')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-MA-TC1')

        result = make_draft_result(db, exam.id, stu.id, subj.id, marks=55.0)

        resp = client.put(
            f'/api/v1/exams/{exam.id}/results/{result.id}',
            json={'marks_obtained': 90},
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        assert body['data']['marks_obtained'] == 90.0
        assert body['data']['grade'] == 'A+'
        assert body['data']['gpa'] == 4.0
        assert body['data']['status'] == 'draft'

        # Verify persisted in DB
        db.session.expire(result)
        assert float(result.marks_obtained) == 90.0
        assert result.grade == 'A+'


# ---------------------------------------------------------------------------
# TC-2: Update marks on a finalized result → 409 Conflict
# ---------------------------------------------------------------------------

class TestUpdateMarksFinalizedBlocked:

    def test_update_marks_finalized_blocked(self, client, admin_token, db):
        cls = make_class(db, 'MA Class TC2', 12)
        sec = make_section(db, cls.id, 'TC2')
        ay = make_academic_year(db, 'MA-AY-TC2')
        subj = make_subject(db, 'MA_TC2', 100)
        exam = make_exam(db, sec.id, ay.id)

        u = User(email='stu_ma_tc2@test.sms', role='student', first_name='S', last_name='2')
        u.set_password('x')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-MA-TC2')

        result = make_finalized_result(db, exam.id, stu.id, subj.id, marks=80.0)

        resp = client.put(
            f'/api/v1/exams/{exam.id}/results/{result.id}',
            json={'marks_obtained': 50},
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 409
        body = resp.get_json()
        assert body['success'] is False
        assert 'finalized' in body['message'].lower()


# ---------------------------------------------------------------------------
# TC-3: Update marks with wrong exam_id (result belongs to a different exam)
# ---------------------------------------------------------------------------

class TestUpdateMarksWrongExam:

    def test_update_marks_wrong_exam_returns_404(self, client, admin_token, db):
        # Create two separate exams
        cls = make_class(db, 'MA Class TC3', 13)
        sec = make_section(db, cls.id, 'TC3')
        ay = make_academic_year(db, 'MA-AY-TC3')
        subj = make_subject(db, 'MA_TC3', 100)

        exam_a = make_exam(db, sec.id, ay.id)

        # Second exam — share the same section/ay for simplicity
        exam_b = Exam(
            name='Approval Test Exam B',
            term='Term 1',
            exam_type='final',
            section_id=sec.id,
            academic_year_id=ay.id,
            is_active=True,
        )
        db.session.add(exam_b)
        db.session.commit()

        u = User(email='stu_ma_tc3@test.sms', role='student', first_name='S', last_name='3')
        u.set_password('x')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-MA-TC3')

        # Result belongs to exam_a
        result = make_draft_result(db, exam_a.id, stu.id, subj.id)

        # But we pass exam_b's id in the URL
        resp = client.put(
            f'/api/v1/exams/{exam_b.id}/results/{result.id}',
            json={'marks_obtained': 60},
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 404
        body = resp.get_json()
        assert body['success'] is False


# ---------------------------------------------------------------------------
# TC-4: marks_obtained > max_marks → 422
# ---------------------------------------------------------------------------

class TestUpdateMarksExceedsMax:

    def test_update_marks_exceeds_max_returns_422(self, client, admin_token, db):
        cls = make_class(db, 'MA Class TC4', 14)
        sec = make_section(db, cls.id, 'TC4')
        ay = make_academic_year(db, 'MA-AY-TC4')
        subj = make_subject(db, 'MA_TC4', 50)   # max_marks = 50
        exam = make_exam(db, sec.id, ay.id)

        u = User(email='stu_ma_tc4@test.sms', role='student', first_name='S', last_name='4')
        u.set_password('x')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-MA-TC4')

        result = make_draft_result(db, exam.id, stu.id, subj.id, marks=40.0, max_marks=50.0)

        resp = client.put(
            f'/api/v1/exams/{exam.id}/results/{result.id}',
            json={'marks_obtained': 75},   # exceeds max of 50
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 422
        body = resp.get_json()
        assert body['success'] is False
        assert '50' in body['message']


# ---------------------------------------------------------------------------
# TC-5: Finalize exam with draft results → 200, finalized_count > 0
# ---------------------------------------------------------------------------

class TestFinalizeExamSuccess:

    def test_finalize_exam_success(self, client, admin_token, db):
        cls = make_class(db, 'MA Class TC5', 15)
        sec = make_section(db, cls.id, 'TC5')
        ay = make_academic_year(db, 'MA-AY-TC5')
        subj = make_subject(db, 'MA_TC5', 100)
        exam = make_exam(db, sec.id, ay.id)

        u = User(email='stu_ma_tc5@test.sms', role='student', first_name='S', last_name='5')
        u.set_password('x')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-MA-TC5')

        make_draft_result(db, exam.id, stu.id, subj.id, marks=70.0)

        resp = client.put(
            f'/api/v1/exams/{exam.id}/finalize',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        assert body['data']['finalized_count'] > 0

        # Verify DB state
        result_row = ExamResult.query.filter_by(exam_id=exam.id).first()
        assert result_row.status == 'finalized'


# ---------------------------------------------------------------------------
# TC-6: Finalize exam when no draft results exist → 400
# ---------------------------------------------------------------------------

class TestFinalizeExamNoDrafts:

    def test_finalize_exam_no_drafts_returns_400(self, client, admin_token, db):
        cls = make_class(db, 'MA Class TC6', 16)
        sec = make_section(db, cls.id, 'TC6')
        ay = make_academic_year(db, 'MA-AY-TC6')
        exam = make_exam(db, sec.id, ay.id)
        # No ExamResult rows at all

        resp = client.put(
            f'/api/v1/exams/{exam.id}/finalize',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 400
        body = resp.get_json()
        assert body['success'] is False
        assert 'draft' in body['message'].lower()


# ---------------------------------------------------------------------------
# TC-7: Teacher cannot call finalize → 403
# ---------------------------------------------------------------------------

class TestFinalizeExamTeacherForbidden:

    def test_finalize_exam_teacher_forbidden(self, client, db, teacher_user_ma):
        token = _get_token(client, 'teacher_ma@test.sms', 'Teacher@123')

        cls = make_class(db, 'MA Class TC7', 17)
        sec = make_section(db, cls.id, 'TC7')
        ay = make_academic_year(db, 'MA-AY-TC7')
        exam = make_exam(db, sec.id, ay.id)

        resp = client.put(
            f'/api/v1/exams/{exam.id}/finalize',
            headers={'Authorization': f'Bearer {token}'},
        )

        assert resp.status_code == 403
        assert resp.get_json()['success'] is False


# ---------------------------------------------------------------------------
# TC-8: Finalize then try to edit → 409
# ---------------------------------------------------------------------------

class TestFinalizeThenEditBlocked:

    def test_finalize_then_edit_blocked(self, client, admin_token, db):
        cls = make_class(db, 'MA Class TC8', 18)
        sec = make_section(db, cls.id, 'TC8')
        ay = make_academic_year(db, 'MA-AY-TC8')
        subj = make_subject(db, 'MA_TC8', 100)
        exam = make_exam(db, sec.id, ay.id)

        u = User(email='stu_ma_tc8@test.sms', role='student', first_name='S', last_name='8')
        u.set_password('x')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-MA-TC8')

        result = make_draft_result(db, exam.id, stu.id, subj.id, marks=65.0)

        headers = {'Authorization': f'Bearer {admin_token}'}

        # Finalize the exam
        fin_resp = client.put(f'/api/v1/exams/{exam.id}/finalize', headers=headers)
        assert fin_resp.status_code == 200
        assert fin_resp.get_json()['data']['finalized_count'] == 1

        # Now attempt to edit the finalized result
        edit_resp = client.put(
            f'/api/v1/exams/{exam.id}/results/{result.id}',
            json={'marks_obtained': 80},
            headers=headers,
        )

        assert edit_resp.status_code == 409
        body = edit_resp.get_json()
        assert body['success'] is False
        assert 'finalized' in body['message'].lower()
