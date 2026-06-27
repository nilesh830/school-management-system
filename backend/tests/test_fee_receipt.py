"""
SMS-038 — Fee Receipt PDF Generation
T-038-05: pytest test suite

Test cases:
  TC-1  TestAdminDownloadsReceipt  — Admin gets 200 PDF, correct content-type,
                                     non-empty bytes, Content-Disposition attachment
  TC-2  TestWrongPaymentId         — payment_id=99999 → 404
  TC-3  TestTeacherCanDownload     — teacher role → 200

xhtml2pdf is mocked with a stub that writes b'%PDF-FAKE' so tests stay fast.
The real service path (template rendering, data assembly) is exercised; only
the final PDF conversion step is short-circuited.
"""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from app.models.user import User
from app.models.student import Student
from app.models.class_ import Class
from app.models.academic_year import AcademicYear
from app.models.fee_structure import FeeStructure
from app.models.fee_record import FeeRecord
from app.models.fee_payment import FeePayment


# ---------------------------------------------------------------------------
# Shared xhtml2pdf stub
# ---------------------------------------------------------------------------

def _fake_pisa(html, dest, **kwargs):
    """Writes a minimal fake PDF signature and reports no errors."""
    dest.write(b'%PDF-FAKE')
    result = MagicMock()
    result.err = 0
    return result


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def make_student_user(db, email, first='Fee', last='Student', admission_no='ADM-FEE-001'):
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


def make_fee_structure(db, class_id, academic_year_id, fee_type='Tuition Fee'):
    fs = FeeStructure(
        class_id=class_id,
        academic_year_id=academic_year_id,
        fee_type=fee_type,
        amount=5000.00,
        is_recurring=False,
        frequency='one_time',
        is_active=True,
    )
    db.session.add(fs)
    db.session.commit()
    return fs


def make_fee_record(db, student_id, fee_structure_id):
    fr = FeeRecord(
        student_id=student_id,
        fee_structure_id=fee_structure_id,
        amount=5000.00,
        discount=500.00,
        net_amount=4500.00,
        due_date=date(2025, 3, 31),
        status='partial',
    )
    db.session.add(fr)
    db.session.commit()
    return fr


def make_fee_payment(db, fee_record_id, receipt_no='REC-2025-0001'):
    fp = FeePayment(
        fee_record_id=fee_record_id,
        amount_paid=2000.00,
        payment_method='cash',
        payment_date=date(2025, 1, 15),
        receipt_no=receipt_no,
        transaction_reference=None,
        remarks='First instalment',
    )
    db.session.add(fp)
    db.session.commit()
    return fp


def _seed_fee_scenario(db, suffix='01'):
    """Creates Class, AcademicYear, FeeStructure, FeeRecord, FeePayment, Student."""
    ay = AcademicYear(
        name=f'2024-2025-fr{suffix}',
        start_date=date(2024, 6, 1),
        end_date=date(2025, 5, 31),
        is_current=True,
        is_active=True,
    )
    db.session.add(ay)
    db.session.flush()

    cls = Class(name=f'Grade 5 FR{suffix}', grade_level=5)
    db.session.add(cls)
    db.session.flush()

    _, student = make_student_user(
        db,
        email=f'fee_stu_{suffix}@test.sms',
        first='Fee',
        last=f'Student{suffix}',
        admission_no=f'ADM-FR-{suffix}',
    )

    fs = make_fee_structure(db, cls.id, ay.id, fee_type='Tuition Fee')
    fr = make_fee_record(db, student.id, fs.id)
    payment = make_fee_payment(db, fr.id, receipt_no=f'REC-2025-{suffix}')
    return payment, fr, fs, student


# ---------------------------------------------------------------------------
# TC-1: Admin downloads receipt → 200, PDF content-type, non-empty, attachment
# ---------------------------------------------------------------------------

class TestAdminDownloadsReceipt:

    def test_status_200_and_pdf_content_type(self, client, admin_token, db):
        payment, *_ = _seed_fee_scenario(db, suffix='001')

        with patch('xhtml2pdf.pisa.CreatePDF', side_effect=_fake_pisa):
            resp = client.get(
                f'/api/v1/fees/payments/{payment.id}/receipt',
                headers={'Authorization': f'Bearer {admin_token}'},
            )

        assert resp.status_code == 200
        assert 'application/pdf' in resp.content_type

    def test_response_has_non_empty_bytes(self, client, admin_token, db):
        payment, *_ = _seed_fee_scenario(db, suffix='002')

        with patch('xhtml2pdf.pisa.CreatePDF', side_effect=_fake_pisa):
            resp = client.get(
                f'/api/v1/fees/payments/{payment.id}/receipt',
                headers={'Authorization': f'Bearer {admin_token}'},
            )

        assert resp.status_code == 200
        assert len(resp.data) > 0
        assert resp.data == b'%PDF-FAKE'

    def test_response_has_content_disposition_attachment(self, client, admin_token, db):
        payment, *_ = _seed_fee_scenario(db, suffix='003')

        with patch('xhtml2pdf.pisa.CreatePDF', side_effect=_fake_pisa):
            resp = client.get(
                f'/api/v1/fees/payments/{payment.id}/receipt',
                headers={'Authorization': f'Bearer {admin_token}'},
            )

        assert resp.status_code == 200
        cd = resp.headers.get('Content-Disposition', '')
        assert 'attachment' in cd

    def test_content_disposition_contains_receipt_no(self, client, admin_token, db):
        payment, *_ = _seed_fee_scenario(db, suffix='004')

        with patch('xhtml2pdf.pisa.CreatePDF', side_effect=_fake_pisa):
            resp = client.get(
                f'/api/v1/fees/payments/{payment.id}/receipt',
                headers={'Authorization': f'Bearer {admin_token}'},
            )

        assert resp.status_code == 200
        cd = resp.headers.get('Content-Disposition', '')
        assert payment.receipt_no in cd


# ---------------------------------------------------------------------------
# TC-2: Non-existent payment_id → 404
# ---------------------------------------------------------------------------

class TestWrongPaymentId:

    def test_nonexistent_payment_returns_404(self, client, admin_token, db):
        with patch('xhtml2pdf.pisa.CreatePDF', side_effect=_fake_pisa):
            resp = client.get(
                '/api/v1/fees/payments/99999/receipt',
                headers={'Authorization': f'Bearer {admin_token}'},
            )

        assert resp.status_code == 404
        body = resp.get_json()
        assert body['success'] is False
        assert 'not found' in body['message'].lower()


# ---------------------------------------------------------------------------
# TC-3: Teacher role → 200
# ---------------------------------------------------------------------------

class TestTeacherCanDownload:

    def test_teacher_can_download_receipt(self, client, teacher_token, db):
        payment, *_ = _seed_fee_scenario(db, suffix='005')

        with patch('xhtml2pdf.pisa.CreatePDF', side_effect=_fake_pisa):
            resp = client.get(
                f'/api/v1/fees/payments/{payment.id}/receipt',
                headers={'Authorization': f'Bearer {teacher_token}'},
            )

        assert resp.status_code == 200
        assert 'application/pdf' in resp.content_type
        assert len(resp.data) > 0
