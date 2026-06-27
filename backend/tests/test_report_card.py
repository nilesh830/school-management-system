"""
SMS-032 — Student Report Card PDF
T-032-06: pytest test suite

Test cases:
  TC-1  Admin downloads report card → 200, Content-Type: application/pdf, non-empty bytes
  TC-2  Student downloads own report card → 200, PDF returned
  TC-3  Student cannot download another student's report card → 403
  TC-4  Non-existent exam → 404
  TC-5  Non-existent student → 404
  TC-6  Report card with no marks yet → still generates PDF (empty subjects)

xhtml2pdf is mocked with a stub that writes b'%PDF-FAKE' so tests remain fast.
The real service path (template rendering, data assembly) is exercised; only
the final PDF conversion step is short-circuited.
"""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from app.models.class_ import Class
from app.models.section import Section
from app.models.academic_year import AcademicYear
from app.models.subject import Subject
from app.models.student import Student
from app.models.exam import Exam
from app.models.exam_result import ExamResult
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_token(client, email, password):
    r = client.post(
        '/api/v1/auth/login',
        json={'email': email, 'password': password, 'school_slug': 'test'},
    )
    return r.get_json()['data']['access_token']


def _fake_pisa(html, dest, **kwargs):
    """xhtml2pdf stub: writes a minimal fake PDF signature, no errors."""
    dest.write(b'%PDF-FAKE')
    mock_result = MagicMock()
    mock_result.err = 0
    return mock_result


def make_class(db, name='RC Class', grade_level=5):
    c = Class(name=name, grade_level=grade_level)
    db.session.add(c)
    db.session.commit()
    return c


def make_section(db, class_id, name='A'):
    s = Section(name=name, class_id=class_id, is_active=True)
    db.session.add(s)
    db.session.commit()
    return s


def make_academic_year(db, name='2024-2025-rc'):
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


def make_subject(db, code='MATH_RC', name='Mathematics', max_marks=100):
    s = Subject(name=name, code=code, max_marks=max_marks, pass_marks=35)
    db.session.add(s)
    db.session.commit()
    return s


def make_exam(db, section_id, academic_year_id, name='RC Midterm'):
    e = Exam(
        name=name,
        term='Term 1',
        exam_type='midterm',
        section_id=section_id,
        academic_year_id=academic_year_id,
        conducted_date=date(2024, 9, 15),
        is_active=True,
    )
    db.session.add(e)
    db.session.commit()
    return e


def make_student_user(db, email, first='Test', last='Student', admission_no='ADM-RC-001'):
    u = User(email=email, role='student', first_name=first, last_name=last)
    u.set_password('Student@123')
    db.session.add(u)
    db.session.flush()
    s = Student(
        user_id=u.id,
        admission_no=admission_no,
        first_name=first,
        last_name=last,
        date_of_birth=date(2012, 3, 15),
        gender='Male',
        admission_date=date(2024, 6, 1),
    )
    db.session.add(s)
    db.session.commit()
    return u, s


def seed_result(db, exam_id, student_id, subject_id, marks, grade, gpa):
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


# ---------------------------------------------------------------------------
# TC-1: Admin downloads report card → 200, Content-Type: application/pdf
# ---------------------------------------------------------------------------

class TestAdminDownloadsReportCard:

    def test_admin_gets_pdf_response(self, client, admin_token, db):
        cls = make_class(db, 'Grade 5 RC1', 5)
        sec = make_section(db, cls.id, 'B')
        ay = make_academic_year(db, '2024-2025-rc1')
        subj = make_subject(db, 'MATH_RC1', 'Mathematics RC1', 100)
        exam = make_exam(db, sec.id, ay.id, 'RC Midterm 1')
        _, stu = make_student_user(db, 'stu_rc1@test.sms', 'Alice', 'RC1', 'ADM-RC1-01')

        seed_result(db, exam.id, stu.id, subj.id, 80, 'A', 3.7)

        with patch('xhtml2pdf.pisa.CreatePDF', side_effect=_fake_pisa):
            resp = client.get(
                f'/api/v1/exams/{exam.id}/report-card/{stu.id}',
                headers={'Authorization': f'Bearer {admin_token}'},
            )

        assert resp.status_code == 200
        assert 'application/pdf' in resp.content_type
        assert len(resp.data) > 0

    def test_admin_response_contains_pdf_bytes(self, client, admin_token, db):
        cls = make_class(db, 'Grade 5 RC2', 5)
        sec = make_section(db, cls.id, 'C')
        ay = make_academic_year(db, '2024-2025-rc2')
        subj = make_subject(db, 'SCI_RC2', 'Science RC2', 100)
        exam = make_exam(db, sec.id, ay.id, 'RC Final 2')
        _, stu = make_student_user(db, 'stu_rc2@test.sms', 'Bob', 'RC2', 'ADM-RC2-01')

        seed_result(db, exam.id, stu.id, subj.id, 92, 'A+', 4.0)

        with patch('xhtml2pdf.pisa.CreatePDF', side_effect=_fake_pisa):
            resp = client.get(
                f'/api/v1/exams/{exam.id}/report-card/{stu.id}',
                headers={'Authorization': f'Bearer {admin_token}'},
            )

        assert resp.status_code == 200
        # Our fake pisa stub writes b'%PDF-FAKE'
        assert resp.data == b'%PDF-FAKE'

    def test_response_has_content_disposition_attachment(self, client, admin_token, db):
        cls = make_class(db, 'Grade 5 RC3', 5)
        sec = make_section(db, cls.id, 'D')
        ay = make_academic_year(db, '2024-2025-rc3')
        subj = make_subject(db, 'ENG_RC3', 'English RC3', 100)
        exam = make_exam(db, sec.id, ay.id, 'RC Unit 3')
        _, stu = make_student_user(db, 'stu_rc3@test.sms', 'Carol', 'RC3', 'ADM-RC3-01')

        seed_result(db, exam.id, stu.id, subj.id, 75, 'B', 3.0)

        with patch('xhtml2pdf.pisa.CreatePDF', side_effect=_fake_pisa):
            resp = client.get(
                f'/api/v1/exams/{exam.id}/report-card/{stu.id}',
                headers={'Authorization': f'Bearer {admin_token}'},
            )

        assert resp.status_code == 200
        cd = resp.headers.get('Content-Disposition', '')
        assert 'attachment' in cd


# ---------------------------------------------------------------------------
# TC-2: Student downloads own report card → 200
# ---------------------------------------------------------------------------

class TestStudentDownloadsOwnReportCard:

    def test_student_can_download_own_report_card(self, client, db):
        cls = make_class(db, 'Grade 6 Own', 6)
        sec = make_section(db, cls.id, 'E')
        ay = make_academic_year(db, '2024-2025-own')
        subj = make_subject(db, 'MATH_OWN', 'Mathematics Own', 100)
        exam = make_exam(db, sec.id, ay.id, 'Own Midterm')
        stu_user, stu = make_student_user(
            db, 'stu_own@test.sms', 'Dave', 'Own', 'ADM-OWN-01'
        )

        seed_result(db, exam.id, stu.id, subj.id, 60, 'C', 2.3)

        token = _get_token(client, 'stu_own@test.sms', 'Student@123')

        with patch('xhtml2pdf.pisa.CreatePDF', side_effect=_fake_pisa):
            resp = client.get(
                f'/api/v1/exams/{exam.id}/report-card/{stu.id}',
                headers={'Authorization': f'Bearer {token}'},
            )

        assert resp.status_code == 200
        assert 'application/pdf' in resp.content_type
        assert len(resp.data) > 0


# ---------------------------------------------------------------------------
# TC-3: Student cannot download another student's report card → 403
# ---------------------------------------------------------------------------

class TestStudentDeniedOtherReportCard:

    def test_student_cannot_view_another_students_report_card(self, client, db):
        cls = make_class(db, 'Grade 7 Deny', 7)
        sec = make_section(db, cls.id, 'F')
        ay = make_academic_year(db, '2024-2025-deny')
        subj = make_subject(db, 'MATH_DENY', 'Mathematics Deny', 100)
        exam = make_exam(db, sec.id, ay.id, 'Deny Midterm')

        stu_user1, stu1 = make_student_user(
            db, 'stu_deny1@test.sms', 'Eve', 'Deny1', 'ADM-DENY-01'
        )
        _, stu2 = make_student_user(
            db, 'stu_deny2@test.sms', 'Frank', 'Deny2', 'ADM-DENY-02'
        )

        seed_result(db, exam.id, stu2.id, subj.id, 88, 'A', 3.7)

        token = _get_token(client, 'stu_deny1@test.sms', 'Student@123')

        # stu1 tries to download stu2's report card
        resp = client.get(
            f'/api/v1/exams/{exam.id}/report-card/{stu2.id}',
            headers={'Authorization': f'Bearer {token}'},
        )

        assert resp.status_code == 403
        body = resp.get_json()
        assert body['success'] is False


# ---------------------------------------------------------------------------
# TC-4: Non-existent exam → 404
# ---------------------------------------------------------------------------

class TestNonExistentExamReportCard:

    def test_nonexistent_exam_returns_404(self, client, admin_token, db):
        with patch('xhtml2pdf.pisa.CreatePDF', side_effect=_fake_pisa):
            resp = client.get(
                '/api/v1/exams/99999/report-card/1',
                headers={'Authorization': f'Bearer {admin_token}'},
            )

        assert resp.status_code == 404
        body = resp.get_json()
        assert body['success'] is False
        assert 'not found' in body['message'].lower()


# ---------------------------------------------------------------------------
# TC-5: Non-existent student → 404
# ---------------------------------------------------------------------------

class TestNonExistentStudentReportCard:

    def test_nonexistent_student_returns_404(self, client, admin_token, db):
        cls = make_class(db, 'Grade 8 NS', 8)
        sec = make_section(db, cls.id, 'G')
        ay = make_academic_year(db, '2024-2025-ns')
        exam = make_exam(db, sec.id, ay.id, 'NS Midterm')

        with patch('xhtml2pdf.pisa.CreatePDF', side_effect=_fake_pisa):
            resp = client.get(
                f'/api/v1/exams/{exam.id}/report-card/99999',
                headers={'Authorization': f'Bearer {admin_token}'},
            )

        assert resp.status_code == 404
        body = resp.get_json()
        assert body['success'] is False
        assert 'not found' in body['message'].lower()


# ---------------------------------------------------------------------------
# TC-6: Report card with no marks yet → still generates PDF (empty subjects)
# ---------------------------------------------------------------------------

class TestReportCardNoMarks:

    def test_report_card_generated_with_no_marks(self, client, admin_token, db):
        cls = make_class(db, 'Grade 9 NoMarks', 9)
        sec = make_section(db, cls.id, 'H')
        ay = make_academic_year(db, '2024-2025-nm')
        exam = make_exam(db, sec.id, ay.id, 'NoMarks Midterm')
        _, stu = make_student_user(
            db, 'stu_nm@test.sms', 'Grace', 'NoMarks', 'ADM-NM-01'
        )

        # No ExamResult rows seeded — empty subjects should still yield a PDF

        with patch('xhtml2pdf.pisa.CreatePDF', side_effect=_fake_pisa):
            resp = client.get(
                f'/api/v1/exams/{exam.id}/report-card/{stu.id}',
                headers={'Authorization': f'Bearer {admin_token}'},
            )

        assert resp.status_code == 200
        assert 'application/pdf' in resp.content_type
        assert len(resp.data) > 0

    def test_service_returns_pdf_bytes_for_no_marks(self, db):
        """
        Unit-level check: ExamService.generate_report_card_pdf returns bytes,
        not an error, even when no marks exist.
        """
        from flask import current_app
        from app.services.exam_service import ExamService

        cls = make_class(db, 'Grade 9 SvcNM', 9)
        sec = make_section(db, cls.id, 'I')
        ay = make_academic_year(db, '2024-2025-svcnm')
        exam = make_exam(db, sec.id, ay.id, 'SvcNoMarks Exam')
        _, stu = make_student_user(
            db, 'stu_svcnm@test.sms', 'Hank', 'SvcNM', 'ADM-SVCNM-01'
        )

        with patch('xhtml2pdf.pisa.CreatePDF', side_effect=_fake_pisa):
            pdf_bytes, err = ExamService.generate_report_card_pdf(exam.id, stu.id)

        assert err is None
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0


# ---------------------------------------------------------------------------
# Edge: Unauthenticated request → 401
# ---------------------------------------------------------------------------

class TestUnauthenticatedReportCard:

    def test_no_token_returns_401(self, client, db):
        resp = client.get('/api/v1/exams/1/report-card/1')
        assert resp.status_code == 401
