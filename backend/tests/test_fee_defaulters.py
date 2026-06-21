"""
SMS-039 — Fee Defaulters Report
Tests: overdue records returned, current records excluded, class_id filter,
       partial payment reflected, 403 for non-admin.
"""
import pytest
from datetime import date, timedelta

from app.models.class_ import Class
from app.models.academic_year import AcademicYear
from app.models.fee_structure import FeeStructure
from app.models.fee_record import FeeRecord
from app.models.fee_payment import FeePayment
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
# Helpers (mirrors test_fee_payments.py conventions)
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
        last_name='Defaulter',
    )
    u.set_password('Student@123')
    db.session.add(u)
    db.session.flush()

    s = Student(
        user_id=u.id,
        admission_no=f'ADM-DEF-{uid:05d}',
        first_name=f'Student{tag}',
        last_name='Defaulter',
        date_of_birth=date(2010, 1, 1),
        gender='Male',
        admission_date=date(2024, 6, 1),
    )
    db.session.add(s)
    db.session.commit()
    return s


def make_fee_record(db, student_id, fee_structure_id, net_amount=5000.00,
                    status='pending', due_date=None):
    """Create a FeeRecord directly (bypassing generate_records_for_class)."""
    if due_date is None:
        due_date = date(2025, 3, 31)
    fr = FeeRecord(
        student_id=student_id,
        fee_structure_id=fee_structure_id,
        amount=net_amount,
        discount=0,
        net_amount=net_amount,
        due_date=due_date,
        status=status,
    )
    db.session.add(fr)
    db.session.commit()
    return fr


def make_payment(db, fee_record_id, amount_paid, uid_suffix=None):
    """Create a FeePayment for a given fee record."""
    uid = _uid()
    pay = FeePayment(
        fee_record_id=fee_record_id,
        amount_paid=amount_paid,
        payment_method='cash',
        payment_date=date.today(),
        receipt_no=f'REC-TEST-{uid:06d}',
    )
    db.session.add(pay)
    db.session.commit()
    return pay


# ---------------------------------------------------------------------------
# 1. Overdue records are returned
# ---------------------------------------------------------------------------

class TestOverdueRecordsReturned:

    def test_overdue_pending_record_appears_with_correct_days(self, client, admin_token, db):
        """A pending fee record with due_date yesterday must appear in defaulters."""
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=3000.00)
        student = make_student_user(db)

        yesterday = date.today() - timedelta(days=1)
        fee_record = make_fee_record(
            db, student.id, fs.id, net_amount=3000.00,
            status='pending', due_date=yesterday,
        )

        resp = client.get(
            '/api/v1/fees/defaulters',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        defaulters = body['data']['defaulters']
        count = body['data']['count']

        student_ids = [d['student_id'] for d in defaulters]
        assert student.id in student_ids, 'Overdue student must appear in defaulters'

        # Find the specific entry
        entry = next(d for d in defaulters if d['student_id'] == student.id)
        assert entry['fee_record_id'] == fee_record.id
        assert entry['days_overdue'] >= 1
        assert entry['balance_due'] == 3000.0
        assert entry['total_paid'] == 0.0
        assert entry['due_date'] == yesterday.isoformat()
        assert count == len(defaulters)


# ---------------------------------------------------------------------------
# 2. Current (non-overdue) records are excluded
# ---------------------------------------------------------------------------

class TestCurrentRecordsExcluded:

    def test_future_due_date_not_in_defaulters(self, client, admin_token, db):
        """A pending record with due_date today or in the future must NOT appear."""
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=2000.00)
        student = make_student_user(db)

        tomorrow = date.today() + timedelta(days=1)
        make_fee_record(
            db, student.id, fs.id, net_amount=2000.00,
            status='pending', due_date=tomorrow,
        )

        resp = client.get(
            '/api/v1/fees/defaulters',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 200
        body = resp.get_json()
        student_ids = [d['student_id'] for d in body['data']['defaulters']]
        assert student.id not in student_ids, (
            'Student with future due_date must not appear in defaulters'
        )

    def test_today_due_date_not_in_defaulters(self, client, admin_token, db):
        """A pending record due today is NOT yet overdue."""
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=1500.00)
        student = make_student_user(db)

        make_fee_record(
            db, student.id, fs.id, net_amount=1500.00,
            status='pending', due_date=date.today(),
        )

        resp = client.get(
            '/api/v1/fees/defaulters',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 200
        student_ids = [d['student_id'] for d in resp.get_json()['data']['defaulters']]
        assert student.id not in student_ids


# ---------------------------------------------------------------------------
# 3. class_id filter — only records for that class are returned
# ---------------------------------------------------------------------------

class TestClassFilter:

    def test_class_filter_returns_only_matching_class(self, client, admin_token, db):
        """With ?class_id=X only defaulters in class X should be returned."""
        ay = make_academic_year(db)

        cls_a = make_class(db, name='Class A', grade_level=1)
        cls_b = make_class(db, name='Class B', grade_level=2)

        fs_a = make_fee_structure(db, cls_a.id, ay.id, fee_type='Tuition A', amount=4000.00)
        fs_b = make_fee_structure(db, cls_b.id, ay.id, fee_type='Tuition B', amount=4000.00)

        student_a = make_student_user(db)
        student_b = make_student_user(db)

        overdue = date.today() - timedelta(days=5)

        make_fee_record(db, student_a.id, fs_a.id, net_amount=4000.00,
                        status='pending', due_date=overdue)
        make_fee_record(db, student_b.id, fs_b.id, net_amount=4000.00,
                        status='pending', due_date=overdue)

        resp = client.get(
            f'/api/v1/fees/defaulters?class_id={cls_a.id}',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 200
        body = resp.get_json()
        defaulters = body['data']['defaulters']
        student_ids = [d['student_id'] for d in defaulters]

        assert student_a.id in student_ids, 'Student from class A must be in filtered results'
        assert student_b.id not in student_ids, 'Student from class B must not appear'


# ---------------------------------------------------------------------------
# 4. Partial payment is reflected in total_paid and balance_due
# ---------------------------------------------------------------------------

class TestPartialPaymentReflected:

    def test_partial_payment_totals_correct(self, client, admin_token, db):
        """When a partial payment exists, total_paid and balance_due must reflect it."""
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=6000.00)
        student = make_student_user(db)

        overdue = date.today() - timedelta(days=10)
        fee_record = make_fee_record(
            db, student.id, fs.id, net_amount=6000.00,
            status='partial', due_date=overdue,
        )

        # Record a partial payment of 2000
        make_payment(db, fee_record.id, amount_paid=2000.00)

        resp = client.get(
            '/api/v1/fees/defaulters',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 200
        defaulters = resp.get_json()['data']['defaulters']

        entry = next(
            (d for d in defaulters if d['fee_record_id'] == fee_record.id), None
        )
        assert entry is not None, 'Partially-paid overdue record must appear in defaulters'
        assert entry['total_paid'] == 2000.0
        assert entry['balance_due'] == 4000.0
        assert entry['net_amount'] == 6000.0


# ---------------------------------------------------------------------------
# 5. 403 for non-admin roles
# ---------------------------------------------------------------------------

class TestNonAdminForbidden:

    def test_teacher_cannot_access_defaulters(self, client, teacher_token):
        resp = client.get(
            '/api/v1/fees/defaulters',
            headers={'Authorization': f'Bearer {teacher_token}'},
        )

        assert resp.status_code == 403
        body = resp.get_json()
        assert body['success'] is False
