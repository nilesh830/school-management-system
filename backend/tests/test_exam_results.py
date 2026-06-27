"""
SMS-031 — Grade Calculation & GPA
T-031-04: pytest test suite

Tests cover:
  TC-1  Admin gets student results — all subject rows returned with grade/gpa
  TC-2  overall_gpa is correct average of subject GPAs
  TC-3  overall_percentage is correct (total_marks / total_max_marks * 100)
  TC-4  overall_grade matches grade scale boundary (90% → A+, 89% → A)
  TC-5  Student with no marks yet → subjects: [], overall_gpa: None
  TC-6  Admin gets all results (no student_id) → list of student summaries
  TC-7  Student role can get own results → 200
  TC-8  Student role denied for another student's results → 403
  TC-9  Teacher can get results → 200
  TC-10 Non-existent exam → exam results return empty (graceful)
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
from app.services.exam_service import ExamService


# ---------------------------------------------------------------------------
# Local helpers (mirror test_exam_marks.py pattern)
# ---------------------------------------------------------------------------

def _get_token(client, email, password):
    r = client.post(
        '/api/v1/auth/login',
        json={'email': email, 'password': password, 'school_slug': 'test'},
    )
    return r.get_json()['data']['access_token']


def make_class(db, name='Test Class', grade_level=1):
    c = Class(name=name, grade_level=grade_level)
    db.session.add(c)
    db.session.commit()
    return c


def make_section(db, class_id, name='A'):
    s = Section(name=name, class_id=class_id, is_active=True)
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


def make_subject(db, code='MATH101', name='Mathematics', max_marks=100):
    s = Subject(name=name, code=code, max_marks=max_marks, pass_marks=35)
    db.session.add(s)
    db.session.commit()
    return s


def make_exam(db, section_id, academic_year_id, name='Midterm'):
    e = Exam(
        name=name,
        term='Term 1',
        exam_type='midterm',
        section_id=section_id,
        academic_year_id=academic_year_id,
        is_active=True,
    )
    db.session.add(e)
    db.session.commit()
    return e


def make_student(db, user_id, admission_no='ADM-001'):
    s = Student(
        user_id=user_id,
        admission_no=admission_no,
        first_name='Test',
        last_name='Student',
        date_of_birth=date(2010, 1, 1),
        gender='Male',
        admission_date=date(2024, 6, 1),
    )
    db.session.add(s)
    db.session.commit()
    return s


def seed_result(db, exam_id, student_id, subject_id, marks, grade, gpa, status='draft'):
    """Directly seed an ExamResult row for test setup."""
    r = ExamResult(
        exam_id=exam_id,
        student_id=student_id,
        subject_id=subject_id,
        marks_obtained=marks,
        grade=grade,
        gpa=gpa,
        status=status,
    )
    db.session.add(r)
    db.session.commit()
    return r


# ---------------------------------------------------------------------------
# Shared fixture: sets up a class/section/academic_year used across many tests
# ---------------------------------------------------------------------------

@pytest.fixture
def base_setup(db):
    cls = make_class(db, 'Grade R1', 10)
    sec = make_section(db, cls.id, 'R')
    ay = make_academic_year(db, '2024-2025-r1')
    return sec, ay


# ---------------------------------------------------------------------------
# TC-1: Admin gets student results — all subject rows returned with grade/gpa
# ---------------------------------------------------------------------------

class TestAdminGetsStudentResults:

    def test_all_subject_rows_returned(self, client, admin_token, db, base_setup):
        sec, ay = base_setup
        subj1 = make_subject(db, 'MATH_R1', 'Mathematics', 100)
        subj2 = make_subject(db, 'SCI_R1', 'Science', 100)
        exam = make_exam(db, sec.id, ay.id)

        u = User(email='stu_r1@test.sms', role='student', first_name='R', last_name='1')
        u.set_password('x')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-R1-01')

        seed_result(db, exam.id, stu.id, subj1.id, 90, 'A+', 4.0)
        seed_result(db, exam.id, stu.id, subj2.id, 75, 'B', 3.0)

        resp = client.get(
            f'/api/v1/exams/{exam.id}/results?student_id={stu.id}',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        data = body['data']
        assert data['exam_id'] == exam.id
        assert data['student_id'] == stu.id
        assert len(data['subjects']) == 2

        # Every subject entry must carry grade and gpa
        for subj_entry in data['subjects']:
            assert subj_entry['grade'] is not None
            assert subj_entry['gpa'] is not None
            assert subj_entry['marks_obtained'] is not None
            assert subj_entry['percentage'] is not None


# ---------------------------------------------------------------------------
# TC-2: overall_gpa is correct average of subject GPAs
# ---------------------------------------------------------------------------

class TestOverallGPA:

    def test_overall_gpa_is_mean_of_subject_gpas(self, client, admin_token, db, base_setup):
        sec, ay = base_setup
        subj1 = make_subject(db, 'MATH_G1', 'Mathematics', 100)
        subj2 = make_subject(db, 'SCI_G1', 'Science', 100)
        subj3 = make_subject(db, 'ENG_G1', 'English', 100)
        exam = make_exam(db, sec.id, ay.id, 'GPA Test Exam')

        u = User(email='stu_g1@test.sms', role='student', first_name='G', last_name='1')
        u.set_password('x')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-G1-01')

        # GPAs: 4.0, 3.7, 3.0 → mean = (4.0 + 3.7 + 3.0) / 3 = 3.57
        seed_result(db, exam.id, stu.id, subj1.id, 90, 'A+', 4.0)
        seed_result(db, exam.id, stu.id, subj2.id, 89, 'A', 3.7)
        seed_result(db, exam.id, stu.id, subj3.id, 75, 'B', 3.0)

        resp = client.get(
            f'/api/v1/exams/{exam.id}/results?student_id={stu.id}',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 200
        data = resp.get_json()['data']
        expected_gpa = round((4.0 + 3.7 + 3.0) / 3, 2)
        assert data['overall_gpa'] == expected_gpa


# ---------------------------------------------------------------------------
# TC-3: overall_percentage is correct
# ---------------------------------------------------------------------------

class TestOverallPercentage:

    def test_overall_percentage_calculation(self, client, admin_token, db, base_setup):
        sec, ay = base_setup
        subj1 = make_subject(db, 'MATH_P1', 'Mathematics', 100)
        subj2 = make_subject(db, 'SCI_P1', 'Science', 50)
        exam = make_exam(db, sec.id, ay.id, 'Pct Test Exam')

        u = User(email='stu_p1@test.sms', role='student', first_name='P', last_name='1')
        u.set_password('x')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-P1-01')

        # 70 / 100 + 40 / 50 → total 110 / 150 = 73.33%
        seed_result(db, exam.id, stu.id, subj1.id, 70, 'B', 3.0)
        seed_result(db, exam.id, stu.id, subj2.id, 40, 'C', 2.3)

        resp = client.get(
            f'/api/v1/exams/{exam.id}/results?student_id={stu.id}',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['total_marks_obtained'] == 110.0
        assert data['total_max_marks'] == 150
        expected_pct = round((110 / 150) * 100, 2)
        assert data['overall_percentage'] == expected_pct


# ---------------------------------------------------------------------------
# TC-4: overall_grade matches grade scale boundary
# ---------------------------------------------------------------------------

class TestOverallGrade:

    def test_90_percent_overall_gives_A_plus(self, client, admin_token, db, base_setup):
        sec, ay = base_setup
        subj = make_subject(db, 'MATH_OG1', 'Mathematics', 100)
        exam = make_exam(db, sec.id, ay.id, 'Grade Boundary A+')

        u = User(email='stu_og1@test.sms', role='student', first_name='OG', last_name='1')
        u.set_password('x')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-OG1-01')

        seed_result(db, exam.id, stu.id, subj.id, 90, 'A+', 4.0)

        resp = client.get(
            f'/api/v1/exams/{exam.id}/results?student_id={stu.id}',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        data = resp.get_json()['data']
        assert data['overall_grade'] == 'A+'
        assert data['overall_percentage'] == 90.0

    def test_89_percent_overall_gives_A(self, client, admin_token, db, base_setup):
        sec, ay = base_setup
        subj = make_subject(db, 'MATH_OG2', 'Mathematics', 100)
        exam = make_exam(db, sec.id, ay.id, 'Grade Boundary A')

        u = User(email='stu_og2@test.sms', role='student', first_name='OG', last_name='2')
        u.set_password('x')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-OG2-01')

        seed_result(db, exam.id, stu.id, subj.id, 89, 'A', 3.7)

        resp = client.get(
            f'/api/v1/exams/{exam.id}/results?student_id={stu.id}',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        data = resp.get_json()['data']
        assert data['overall_grade'] == 'A'
        assert data['overall_percentage'] == 89.0


# ---------------------------------------------------------------------------
# TC-5: Student with no marks yet → subjects: [], overall_gpa: None
# ---------------------------------------------------------------------------

class TestStudentNoMarks:

    def test_no_marks_returns_empty_subjects_and_none_gpa(
        self, client, admin_token, db, base_setup
    ):
        sec, ay = base_setup
        exam = make_exam(db, sec.id, ay.id, 'Empty Exam')

        u = User(email='stu_nm1@test.sms', role='student', first_name='NM', last_name='1')
        u.set_password('x')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-NM1-01')

        # No ExamResult rows seeded intentionally

        resp = client.get(
            f'/api/v1/exams/{exam.id}/results?student_id={stu.id}',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['subjects'] == []
        assert data['overall_gpa'] is None
        assert data['total_marks_obtained'] is None
        assert data['overall_grade'] is None


# ---------------------------------------------------------------------------
# TC-6: Admin gets all results (no student_id) → list of student summaries
# ---------------------------------------------------------------------------

class TestAdminGetsAllResults:

    def test_all_results_returns_summaries_for_every_student(
        self, client, admin_token, db, base_setup
    ):
        sec, ay = base_setup
        subj = make_subject(db, 'MATH_ALL1', 'Mathematics', 100)
        exam = make_exam(db, sec.id, ay.id, 'All Results Exam')

        u1 = User(email='stu_all1@test.sms', role='student', first_name='All', last_name='1')
        u1.set_password('x')
        u2 = User(email='stu_all2@test.sms', role='student', first_name='All', last_name='2')
        u2.set_password('x')
        db.session.add_all([u1, u2])
        db.session.flush()

        stu1 = make_student(db, u1.id, 'ADM-ALL1-01')
        stu2 = make_student(db, u2.id, 'ADM-ALL1-02')

        seed_result(db, exam.id, stu1.id, subj.id, 85, 'A', 3.7)
        seed_result(db, exam.id, stu2.id, subj.id, 60, 'C', 2.3)

        resp = client.get(
            f'/api/v1/exams/{exam.id}/results',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        data = body['data']
        assert data['exam_id'] == exam.id
        assert len(data['results']) == 2

        student_ids = {r['student_id'] for r in data['results']}
        assert stu1.id in student_ids
        assert stu2.id in student_ids

        for summary in data['results']:
            assert 'overall_gpa' in summary
            assert 'overall_percentage' in summary
            assert 'overall_grade' in summary
            assert 'subject_count' in summary


# ---------------------------------------------------------------------------
# TC-7: Student role can get own results → 200
# ---------------------------------------------------------------------------

class TestStudentGetsOwnResults:

    def test_student_can_view_own_results(self, client, db, base_setup):
        sec, ay = base_setup
        subj = make_subject(db, 'MATH_SW1', 'Mathematics', 100)
        exam = make_exam(db, sec.id, ay.id, 'Student Own Exam')

        u = User(email='stu_sw1@test.sms', role='student', first_name='SW', last_name='1')
        u.set_password('Student@123')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-SW1-01')

        seed_result(db, exam.id, stu.id, subj.id, 80, 'A', 3.7)

        token = _get_token(client, 'stu_sw1@test.sms', 'Student@123')

        # student_id provided explicitly (own id)
        resp = client.get(
            f'/api/v1/exams/{exam.id}/results?student_id={stu.id}',
            headers={'Authorization': f'Bearer {token}'},
        )

        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['student_id'] == stu.id
        assert len(data['subjects']) == 1

    def test_student_gets_own_results_without_student_id_param(
        self, client, db, base_setup
    ):
        """When student omits student_id, the API resolves to their own id."""
        sec, ay = base_setup
        subj = make_subject(db, 'MATH_SW2', 'Mathematics', 100)
        exam = make_exam(db, sec.id, ay.id, 'Student Auto Exam')

        u = User(email='stu_sw2@test.sms', role='student', first_name='SW', last_name='2')
        u.set_password('Student@123')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-SW2-01')

        seed_result(db, exam.id, stu.id, subj.id, 72, 'B', 3.0)

        token = _get_token(client, 'stu_sw2@test.sms', 'Student@123')

        # No student_id param — should auto-resolve
        resp = client.get(
            f'/api/v1/exams/{exam.id}/results',
            headers={'Authorization': f'Bearer {token}'},
        )

        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['student_id'] == stu.id


# ---------------------------------------------------------------------------
# TC-8: Student role denied for another student's results → 403
# ---------------------------------------------------------------------------

class TestStudentDeniedOtherResults:

    def test_student_denied_another_students_results(self, client, db, base_setup):
        sec, ay = base_setup
        subj = make_subject(db, 'MATH_SD1', 'Mathematics', 100)
        exam = make_exam(db, sec.id, ay.id, 'Denied Exam')

        u1 = User(email='stu_sd1@test.sms', role='student', first_name='SD', last_name='1')
        u1.set_password('Student@123')
        u2 = User(email='stu_sd2@test.sms', role='student', first_name='SD', last_name='2')
        u2.set_password('Student@123')
        db.session.add_all([u1, u2])
        db.session.flush()

        stu1 = make_student(db, u1.id, 'ADM-SD1-01')
        stu2 = make_student(db, u2.id, 'ADM-SD1-02')

        seed_result(db, exam.id, stu2.id, subj.id, 90, 'A+', 4.0)

        token = _get_token(client, 'stu_sd1@test.sms', 'Student@123')

        # stu1 tries to view stu2's results
        resp = client.get(
            f'/api/v1/exams/{exam.id}/results?student_id={stu2.id}',
            headers={'Authorization': f'Bearer {token}'},
        )

        assert resp.status_code == 403
        assert resp.get_json()['success'] is False


# ---------------------------------------------------------------------------
# TC-9: Teacher can get results → 200
# ---------------------------------------------------------------------------

class TestTeacherGetsResults:

    def test_teacher_can_get_student_results(self, client, teacher_user, db, base_setup):
        sec, ay = base_setup
        subj = make_subject(db, 'MATH_TR1', 'Mathematics', 100)
        exam = make_exam(db, sec.id, ay.id, 'Teacher Results Exam')

        u = User(email='stu_tr1@test.sms', role='student', first_name='TR', last_name='1')
        u.set_password('x')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-TR1-01')

        seed_result(db, exam.id, stu.id, subj.id, 65, 'C', 2.3)

        token = _get_token(client, 'teacher@test.sms', 'Teacher@123')

        resp = client.get(
            f'/api/v1/exams/{exam.id}/results?student_id={stu.id}',
            headers={'Authorization': f'Bearer {token}'},
        )

        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

    def test_teacher_can_get_all_results(self, client, teacher_user, db, base_setup):
        sec, ay = base_setup
        subj = make_subject(db, 'MATH_TR2', 'Mathematics', 100)
        exam = make_exam(db, sec.id, ay.id, 'Teacher All Results Exam')

        u = User(email='stu_tr2@test.sms', role='student', first_name='TR', last_name='2')
        u.set_password('x')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-TR2-01')

        seed_result(db, exam.id, stu.id, subj.id, 70, 'B', 3.0)

        token = _get_token(client, 'teacher@test.sms', 'Teacher@123')

        # No student_id — teacher gets all
        resp = client.get(
            f'/api/v1/exams/{exam.id}/results',
            headers={'Authorization': f'Bearer {token}'},
        )

        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert len(data['results']) >= 1


# ---------------------------------------------------------------------------
# TC-10: Non-existent exam → results return gracefully (empty)
# ---------------------------------------------------------------------------

class TestNonExistentExamResults:

    def test_nonexistent_exam_returns_empty_results(self, client, admin_token, db):
        resp = client.get(
            '/api/v1/exams/99999/results?student_id=1',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        # The service never errors on missing exam — just returns no subjects
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['subjects'] == []
        assert data['overall_gpa'] is None

    def test_nonexistent_exam_all_results_returns_empty_list(
        self, client, admin_token, db
    ):
        resp = client.get(
            '/api/v1/exams/99999/results',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['results'] == []
