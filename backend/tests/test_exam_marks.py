"""
SMS-030 — Subject-wise Marks Entry
T-030-06: pytest test suite

Tests cover:
  TC-1  Admin enters marks successfully → 201, grade + gpa calculated
  TC-2  marks_obtained > max_marks → 422
  TC-3  Teacher enters marks for assigned subject → 201
  TC-4  Teacher enters marks for unassigned subject → 403
  TC-5  Re-entering marks (upsert) on draft → 200, values updated
  TC-6  Non-existent exam → 404
  TC-7  Non-existent subject → 404
  TC-8  Student cannot access endpoint → 403
  TC-9  Grade boundary: 89 % → A/3.7, 90 % → A+/4.0
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
from app.models.teacher import Teacher
from app.models.teacher_subject import TeacherSubject
from app.models.user import User
from app.services.exam_service import ExamService


# ---------------------------------------------------------------------------
# Local helpers
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


def make_subject(db, code='MATH101', max_marks=100):
    s = Subject(name='Mathematics', code=code, max_marks=max_marks, pass_marks=35)
    db.session.add(s)
    db.session.commit()
    return s


def make_exam(db, section_id, academic_year_id):
    e = Exam(
        name='Midterm',
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def student_user_local(db):
    u = User(
        email='student_marks@test.sms',
        role='student',
        first_name='Mark',
        last_name='Student',
    )
    u.set_password('Student@123')
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def teacher_with_profile(db):
    """
    Create a teacher user + Teacher profile.
    Returns (user, teacher) tuple.
    """
    u = User(
        email='teacher_marks@test.sms',
        role='teacher',
        first_name='Priya',
        last_name='Marks',
    )
    u.set_password('Teacher@123')
    db.session.add(u)
    db.session.flush()

    t = Teacher(
        user_id=u.id,
        employee_id='EMP-MARKS-01',
        first_name='Priya',
        last_name='Marks',
        joining_date=date(2020, 6, 1),
    )
    db.session.add(t)
    db.session.commit()
    return u, t


# ---------------------------------------------------------------------------
# TC-1: Admin enters marks → 201, grade + gpa present
# ---------------------------------------------------------------------------

class TestAdminEntersMarks:

    def test_admin_enters_marks_successfully(self, client, admin_token, db):
        cls = make_class(db, 'Grade 1', 1)
        sec = make_section(db, cls.id, 'A')
        ay = make_academic_year(db, '2024-2025-m1')
        subj = make_subject(db, 'MATH_M1', 100)
        exam = make_exam(db, sec.id, ay.id)

        u = User(email='stu_m1@test.sms', role='student', first_name='S', last_name='1')
        u.set_password('x')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-M1-01')

        resp = client.post(
            f'/api/v1/exams/{exam.id}/marks',
            json={
                'subject_id': subj.id,
                'section_id': sec.id,
                'marks': [{'student_id': stu.id, 'marks_obtained': 82}],
            },
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 201
        body = resp.get_json()
        assert body['success'] is True
        assert body['data']['saved'] == 1
        assert body['data']['exam_id'] == exam.id
        assert body['data']['subject_id'] == subj.id

        # Verify grade + gpa were persisted
        saved = ExamResult.query.filter_by(
            exam_id=exam.id, student_id=stu.id, subject_id=subj.id
        ).first()
        assert saved is not None
        assert saved.grade == 'A'
        assert float(saved.gpa) == 3.7


# ---------------------------------------------------------------------------
# TC-2: marks_obtained > max_marks → 422
# ---------------------------------------------------------------------------

class TestMarksExceedMaxMarks:

    def test_marks_exceed_max_marks_returns_422(self, client, admin_token, db):
        cls = make_class(db, 'Grade 2', 2)
        sec = make_section(db, cls.id, 'B')
        ay = make_academic_year(db, '2024-2025-m2')
        subj = make_subject(db, 'MATH_M2', 100)
        exam = make_exam(db, sec.id, ay.id)

        u = User(email='stu_m2@test.sms', role='student', first_name='S', last_name='2')
        u.set_password('x')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-M2-01')

        resp = client.post(
            f'/api/v1/exams/{exam.id}/marks',
            json={
                'subject_id': subj.id,
                'section_id': sec.id,
                'marks': [{'student_id': stu.id, 'marks_obtained': 105}],
            },
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 422
        assert resp.get_json()['success'] is False


# ---------------------------------------------------------------------------
# TC-3: Teacher enters marks for assigned subject → 201
# ---------------------------------------------------------------------------

class TestTeacherAssignedSubject:

    def test_teacher_assigned_subject_enters_marks(
        self, client, db, teacher_with_profile
    ):
        teacher_user, teacher = teacher_with_profile
        token = _get_token(client, 'teacher_marks@test.sms', 'Teacher@123')

        cls = make_class(db, 'Grade 3', 3)
        sec = make_section(db, cls.id, 'C')
        ay = make_academic_year(db, '2024-2025-m3')
        subj = make_subject(db, 'MATH_M3', 100)
        exam = make_exam(db, sec.id, ay.id)

        # Assign teacher to subject
        ts = TeacherSubject(teacher_id=teacher.id, subject_id=subj.id)
        db.session.add(ts)
        db.session.commit()

        u = User(email='stu_m3@test.sms', role='student', first_name='S', last_name='3')
        u.set_password('x')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-M3-01')

        resp = client.post(
            f'/api/v1/exams/{exam.id}/marks',
            json={
                'subject_id': subj.id,
                'section_id': sec.id,
                'marks': [{'student_id': stu.id, 'marks_obtained': 75}],
            },
            headers={'Authorization': f'Bearer {token}'},
        )

        assert resp.status_code == 201
        assert resp.get_json()['success'] is True


# ---------------------------------------------------------------------------
# TC-4: Teacher enters marks for unassigned subject → 403
# ---------------------------------------------------------------------------

class TestTeacherUnassignedSubject:

    def test_teacher_unassigned_subject_returns_403(
        self, client, db, teacher_with_profile
    ):
        teacher_user, teacher = teacher_with_profile
        token = _get_token(client, 'teacher_marks@test.sms', 'Teacher@123')

        cls = make_class(db, 'Grade 4', 4)
        sec = make_section(db, cls.id, 'D')
        ay = make_academic_year(db, '2024-2025-m4')
        subj = make_subject(db, 'MATH_M4', 100)  # NOT assigned to teacher
        exam = make_exam(db, sec.id, ay.id)

        u = User(email='stu_m4@test.sms', role='student', first_name='S', last_name='4')
        u.set_password('x')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-M4-01')

        resp = client.post(
            f'/api/v1/exams/{exam.id}/marks',
            json={
                'subject_id': subj.id,
                'section_id': sec.id,
                'marks': [{'student_id': stu.id, 'marks_obtained': 60}],
            },
            headers={'Authorization': f'Bearer {token}'},
        )

        assert resp.status_code == 403
        assert resp.get_json()['success'] is False


# ---------------------------------------------------------------------------
# TC-5: Upsert — re-enter marks on draft → values updated
# ---------------------------------------------------------------------------

class TestUpsertDraftMarks:

    def test_reenter_draft_marks_updates_values(self, client, admin_token, db):
        cls = make_class(db, 'Grade 5', 5)
        sec = make_section(db, cls.id, 'E')
        ay = make_academic_year(db, '2024-2025-m5')
        subj = make_subject(db, 'MATH_M5', 100)
        exam = make_exam(db, sec.id, ay.id)

        u = User(email='stu_m5@test.sms', role='student', first_name='S', last_name='5')
        u.set_password('x')
        db.session.add(u)
        db.session.flush()
        stu = make_student(db, u.id, 'ADM-M5-01')

        payload = {
            'subject_id': subj.id,
            'section_id': sec.id,
            'marks': [{'student_id': stu.id, 'marks_obtained': 55}],
        }
        headers = {'Authorization': f'Bearer {admin_token}'}

        # First entry
        r1 = client.post(f'/api/v1/exams/{exam.id}/marks', json=payload, headers=headers)
        assert r1.status_code == 201

        # Verify first grade (D range)
        saved = ExamResult.query.filter_by(
            exam_id=exam.id, student_id=stu.id, subject_id=subj.id
        ).first()
        assert saved.grade == 'D'

        # Second entry with different marks
        payload['marks'][0]['marks_obtained'] = 91
        r2 = client.post(f'/api/v1/exams/{exam.id}/marks', json=payload, headers=headers)
        assert r2.status_code == 201

        # Row count must still be 1
        count = ExamResult.query.filter_by(
            exam_id=exam.id, student_id=stu.id, subject_id=subj.id
        ).count()
        assert count == 1

        # Grade must be updated
        db.session.expire(saved)
        assert saved.grade == 'A+'
        assert float(saved.marks_obtained) == 91.0


# ---------------------------------------------------------------------------
# TC-6: Non-existent exam → 404
# ---------------------------------------------------------------------------

class TestNonExistentExam:

    def test_nonexistent_exam_returns_404(self, client, admin_token, db):
        subj = make_subject(db, 'MATH_M6', 100)

        resp = client.post(
            '/api/v1/exams/99999/marks',
            json={
                'subject_id': subj.id,
                'section_id': 1,
                'marks': [{'student_id': 1, 'marks_obtained': 50}],
            },
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 404
        assert resp.get_json()['success'] is False


# ---------------------------------------------------------------------------
# TC-7: Non-existent subject → 404
# ---------------------------------------------------------------------------

class TestNonExistentSubject:

    def test_nonexistent_subject_returns_404(self, client, admin_token, db):
        cls = make_class(db, 'Grade 7', 7)
        sec = make_section(db, cls.id, 'G')
        ay = make_academic_year(db, '2024-2025-m7')
        exam = make_exam(db, sec.id, ay.id)

        resp = client.post(
            f'/api/v1/exams/{exam.id}/marks',
            json={
                'subject_id': 88888,
                'section_id': sec.id,
                'marks': [{'student_id': 1, 'marks_obtained': 50}],
            },
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 404
        assert resp.get_json()['success'] is False


# ---------------------------------------------------------------------------
# TC-8: Student cannot access endpoint → 403
# ---------------------------------------------------------------------------

class TestStudentCannotEnterMarks:

    def test_student_enter_marks_returns_403(self, client, db, student_user_local):
        token = _get_token(client, 'student_marks@test.sms', 'Student@123')

        cls = make_class(db, 'Grade 8', 8)
        sec = make_section(db, cls.id, 'H')
        ay = make_academic_year(db, '2024-2025-m8')
        subj = make_subject(db, 'MATH_M8', 100)
        exam = make_exam(db, sec.id, ay.id)

        resp = client.post(
            f'/api/v1/exams/{exam.id}/marks',
            json={
                'subject_id': subj.id,
                'section_id': sec.id,
                'marks': [{'student_id': 1, 'marks_obtained': 50}],
            },
            headers={'Authorization': f'Bearer {token}'},
        )

        assert resp.status_code == 403
        assert resp.get_json()['success'] is False


# ---------------------------------------------------------------------------
# TC-9: Grade boundary — pure unit tests on calculate_grade
# ---------------------------------------------------------------------------

class TestGradeBoundaries:

    def test_89_pct_is_grade_A(self):
        grade, gpa = ExamService.calculate_grade(89, 100)
        assert grade == 'A'
        assert gpa == 3.7

    def test_90_pct_is_grade_A_plus(self):
        grade, gpa = ExamService.calculate_grade(90, 100)
        assert grade == 'A+'
        assert gpa == 4.0

    def test_100_pct_is_grade_A_plus(self):
        grade, gpa = ExamService.calculate_grade(100, 100)
        assert grade == 'A+'
        assert gpa == 4.0

    def test_0_pct_is_grade_F(self):
        grade, gpa = ExamService.calculate_grade(0, 100)
        assert grade == 'F'
        assert gpa == 0.0

    def test_max_marks_zero_edge_case(self):
        """Division-by-zero guard: max_marks=0 must return F/0.0."""
        grade, gpa = ExamService.calculate_grade(0, 0)
        assert grade == 'F'
        assert gpa == 0.0

    def test_exactly_40_pct_is_grade_E(self):
        grade, gpa = ExamService.calculate_grade(40, 100)
        assert grade == 'E'
        assert gpa == 1.0

    def test_39_pct_is_grade_F(self):
        grade, gpa = ExamService.calculate_grade(39, 100)
        assert grade == 'F'
        assert gpa == 0.0

    def test_grade_boundaries_with_non_100_max(self):
        """Percentage is relative to max_marks, not always 100."""
        # 45/50 = 90% → A+
        grade, gpa = ExamService.calculate_grade(45, 50)
        assert grade == 'A+'
        assert gpa == 4.0
