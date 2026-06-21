"""
SMS-037 — Record Fee Payment
Tests: payment recording, partial payments, overpayment guard, authorization,
       fee records listing, and sequential receipt number generation.
"""
import pytest
from datetime import date

from app.models.class_ import Class
from app.models.academic_year import AcademicYear
from app.models.fee_structure import FeeStructure
from app.models.fee_record import FeeRecord
from app.models.section import Section
from app.models.student import Student
from app.models.student_section import StudentSection
from app.models.user import User


# ---------------------------------------------------------------------------
# Module-level counter used to generate unique identifiers within this file
# ---------------------------------------------------------------------------

_counter = 0


def _uid():
    global _counter
    _counter += 1
    return _counter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_class(db, name=None, grade_level=1):
    uid = _uid()
    c = Class(name=name or f'Grade {uid}', grade_level=grade_level)
    db.session.add(c)
    db.session.commit()
    return c


def make_academic_year(db, name=None):
    uid = _uid()
    ay = AcademicYear(
        name=name or f'AY-{uid}',
        start_date=date(2024, 6, 1),
        end_date=date(2025, 5, 31),
        is_current=True,
        is_active=True,
    )
    db.session.add(ay)
    db.session.commit()
    return ay


def make_fee_structure(db, class_id, academic_year_id, fee_type=None, amount=5000.00):
    uid = _uid()
    fs = FeeStructure(
        class_id=class_id,
        academic_year_id=academic_year_id,
        fee_type=fee_type or f'Fee Type {uid}',
        amount=amount,
        is_recurring=False,
        frequency='one_time',
    )
    db.session.add(fs)
    db.session.commit()
    return fs


def make_section(db, class_id, name=None):
    uid = _uid()
    sec = Section(name=name or chr(64 + (uid % 26) + 1), class_id=class_id)
    db.session.add(sec)
    db.session.commit()
    return sec


def make_student_user(db, suffix=None):
    """Create a User + Student pair. Returns the Student instance."""
    uid = _uid()
    tag = suffix or uid
    u = User(
        email=f'student_{tag}@test.sms',
        role='student',
        first_name=f'Student{tag}',
        last_name='Testpay',
    )
    u.set_password('Student@123')
    db.session.add(u)
    db.session.flush()

    s = Student(
        user_id=u.id,
        admission_no=f'ADM-PAY-{uid:05d}',
        first_name=f'Student{tag}',
        last_name='Testpay',
        date_of_birth=date(2010, 1, 1),
        gender='Male',
        admission_date=date(2024, 6, 1),
    )
    db.session.add(s)
    db.session.commit()
    return s


def enroll(db, student, section):
    """Enroll a student in a section for the current academic year."""
    ss = StudentSection(
        student_id=student.id,
        section_id=section.id,
        academic_year='2024-2025',
        start_date=date(2024, 6, 1),
        is_current=True,
    )
    db.session.add(ss)
    db.session.commit()
    return ss


def make_fee_record(db, student_id, fee_structure_id, net_amount=5000.00, status='pending'):
    """Create a FeeRecord directly (bypassing generate_records_for_class)."""
    fr = FeeRecord(
        student_id=student_id,
        fee_structure_id=fee_structure_id,
        amount=net_amount,
        discount=0,
        net_amount=net_amount,
        due_date=date(2025, 3, 31),
        status=status,
    )
    db.session.add(fr)
    db.session.commit()
    return fr


def _post_payment(client, token, fee_record_id, amount, method='cash', pay_date=None):
    pay_date = pay_date or date.today().isoformat()
    return client.post(
        '/api/v1/fees/payments',
        json={
            'fee_record_id': fee_record_id,
            'amount_paid': amount,
            'payment_method': method,
            'payment_date': pay_date,
        },
        headers={'Authorization': f'Bearer {token}'},
    )


# ---------------------------------------------------------------------------
# 1. TestRecordPaymentSuccess
# ---------------------------------------------------------------------------

class TestRecordPaymentSuccess:

    def test_full_payment_marks_paid(self, client, admin_token, db):
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=5000.00)
        student = make_student_user(db)
        section = make_section(db, cls.id)
        enroll(db, student, section)
        fee_record = make_fee_record(db, student.id, fs.id, net_amount=5000.00)

        resp = _post_payment(client, admin_token, fee_record.id, 5000)

        assert resp.status_code == 201
        body = resp.get_json()
        assert body['success'] is True
        data = body['data']
        assert data['amount_paid'] == 5000.0
        assert data['balance_due'] == 0.0
        assert data['receipt_no'].startswith('REC-')

        # Confirm fee record status updated to 'paid'
        db.session.refresh(fee_record)
        assert fee_record.status == 'paid'


# ---------------------------------------------------------------------------
# 2. TestPartialPayment
# ---------------------------------------------------------------------------

class TestPartialPayment:

    def test_partial_payment_marks_partial(self, client, admin_token, db):
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=5000.00)
        student = make_student_user(db)
        section = make_section(db, cls.id)
        enroll(db, student, section)
        fee_record = make_fee_record(db, student.id, fs.id, net_amount=5000.00)

        resp = _post_payment(client, admin_token, fee_record.id, 2000)

        assert resp.status_code == 201
        body = resp.get_json()
        assert body['success'] is True
        data = body['data']
        assert data['amount_paid'] == 2000.0
        assert data['balance_due'] == 3000.0

        db.session.refresh(fee_record)
        assert fee_record.status == 'partial'


# ---------------------------------------------------------------------------
# 3. TestOverpaymentBlocked
# ---------------------------------------------------------------------------

class TestOverpaymentBlocked:

    def test_overpayment_returns_422(self, client, admin_token, db):
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=5000.00)
        student = make_student_user(db)
        section = make_section(db, cls.id)
        enroll(db, student, section)
        fee_record = make_fee_record(db, student.id, fs.id, net_amount=5000.00)

        resp = _post_payment(client, admin_token, fee_record.id, 6000)

        assert resp.status_code == 422
        body = resp.get_json()
        assert body['success'] is False
        assert 'balance due' in body['message'].lower() or 'exceeds' in body['message'].lower()


# ---------------------------------------------------------------------------
# 4. TestFeeRecordNotFound
# ---------------------------------------------------------------------------

class TestFeeRecordNotFound:

    def test_missing_fee_record_returns_404(self, client, admin_token):
        resp = _post_payment(client, admin_token, fee_record_id=99999, amount=1000)

        assert resp.status_code == 404
        body = resp.get_json()
        assert body['success'] is False


# ---------------------------------------------------------------------------
# 5. TestTeacherCannotPay
# ---------------------------------------------------------------------------

class TestTeacherCannotPay:

    def test_teacher_forbidden(self, client, teacher_token, admin_token, db):
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=3000.00)
        student = make_student_user(db)
        section = make_section(db, cls.id)
        enroll(db, student, section)
        fee_record = make_fee_record(db, student.id, fs.id, net_amount=3000.00)

        resp = _post_payment(client, teacher_token, fee_record.id, 1000)

        assert resp.status_code == 403
        body = resp.get_json()
        assert body['success'] is False


# ---------------------------------------------------------------------------
# 6. TestGetFeeRecords
# ---------------------------------------------------------------------------

class TestGetFeeRecords:

    def test_get_fee_records_returns_all_for_student(self, client, admin_token, db):
        cls = make_class(db)
        ay = make_academic_year(db)
        fs1 = make_fee_structure(db, cls.id, ay.id, fee_type='Tuition', amount=4000.00)
        fs2 = make_fee_structure(db, cls.id, ay.id, fee_type='Sports', amount=500.00)
        student = make_student_user(db)
        section = make_section(db, cls.id)
        enroll(db, student, section)
        make_fee_record(db, student.id, fs1.id, net_amount=4000.00)
        make_fee_record(db, student.id, fs2.id, net_amount=500.00)

        resp = client.get(
            f'/api/v1/fees/records?student_id={student.id}',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        records = body['data']['fee_records']
        assert len(records) == 2
        # Each record should have an embedded payments list
        for rec in records:
            assert 'payments' in rec
            assert isinstance(rec['payments'], list)

    def test_missing_student_id_returns_400(self, client, admin_token):
        resp = client.get(
            '/api/v1/fees/records',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 400

    def test_teacher_cannot_access_records(self, client, teacher_token, db):
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=1000.00)
        student = make_student_user(db)
        section = make_section(db, cls.id)
        enroll(db, student, section)
        make_fee_record(db, student.id, fs.id, net_amount=1000.00)

        resp = client.get(
            f'/api/v1/fees/records?student_id={student.id}',
            headers={'Authorization': f'Bearer {teacher_token}'},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 7. TestReceiptNoSequential
# ---------------------------------------------------------------------------

class TestReceiptNoSequential:

    def test_receipt_numbers_are_sequential(self, client, admin_token, db):
        cls = make_class(db)
        ay = make_academic_year(db)
        # Two separate fee records for two separate students so the
        # UniqueConstraint(student_id, fee_structure_id) is not violated.
        fs1 = make_fee_structure(db, cls.id, ay.id, fee_type='Reg1', amount=1000.00)
        fs2 = make_fee_structure(db, cls.id, ay.id, fee_type='Reg2', amount=1000.00)

        student_a = make_student_user(db)
        student_b = make_student_user(db)
        section = make_section(db, cls.id)
        enroll(db, student_a, section)
        enroll(db, student_b, section)

        fee_record_a = make_fee_record(db, student_a.id, fs1.id, net_amount=1000.00)
        fee_record_b = make_fee_record(db, student_b.id, fs2.id, net_amount=1000.00)

        current_year = date.today().year

        resp_a = _post_payment(client, admin_token, fee_record_a.id, 1000)
        resp_b = _post_payment(client, admin_token, fee_record_b.id, 1000)

        assert resp_a.status_code == 201
        assert resp_b.status_code == 201

        receipt_a = resp_a.get_json()['data']['receipt_no']
        receipt_b = resp_b.get_json()['data']['receipt_no']

        # Both must follow the REC-{year}-{seq:04d} format
        assert receipt_a.startswith(f'REC-{current_year}-')
        assert receipt_b.startswith(f'REC-{current_year}-')

        # The sequence numbers must differ (sequential, not duplicate)
        seq_a = int(receipt_a.split('-')[-1])
        seq_b = int(receipt_b.split('-')[-1])
        assert seq_a != seq_b
        assert abs(seq_b - seq_a) == 1
