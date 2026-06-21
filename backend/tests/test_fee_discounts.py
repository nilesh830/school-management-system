"""
SMS-040 — Discount & Scholarship Management (T-040-05)
Tests: apply discount, net_amount recalculation, paid-record guard,
       not-found guard, RBAC enforcement, and GET single fee-record endpoint.
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
# Module-level counter for unique identifiers
# ---------------------------------------------------------------------------

_counter = 0


def _uid():
    global _counter
    _counter += 1
    return _counter


# ---------------------------------------------------------------------------
# Helpers (mirror test_fee_payments.py patterns)
# ---------------------------------------------------------------------------

def make_class(db, grade_level=1):
    uid = _uid()
    c = Class(name=f'Grade {uid}', grade_level=grade_level)
    db.session.add(c)
    db.session.commit()
    return c


def make_academic_year(db):
    uid = _uid()
    ay = AcademicYear(
        name=f'AY-{uid}',
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


def make_section(db, class_id):
    uid = _uid()
    sec = Section(name=chr(64 + (uid % 26) + 1), class_id=class_id)
    db.session.add(sec)
    db.session.commit()
    return sec


def make_student_user(db):
    uid = _uid()
    u = User(
        email=f'student_disc_{uid}@test.sms',
        role='student',
        first_name=f'Student{uid}',
        last_name='DiscTest',
    )
    u.set_password('Student@123')
    db.session.add(u)
    db.session.flush()

    s = Student(
        user_id=u.id,
        admission_no=f'ADM-DISC-{uid:05d}',
        first_name=f'Student{uid}',
        last_name='DiscTest',
        date_of_birth=date(2010, 1, 1),
        gender='Male',
        admission_date=date(2024, 6, 1),
    )
    db.session.add(s)
    db.session.commit()
    return s


def make_fee_record(db, student_id, fee_structure_id, amount=5000.00, status='pending'):
    fr = FeeRecord(
        student_id=student_id,
        fee_structure_id=fee_structure_id,
        amount=amount,
        discount=0,
        net_amount=amount,
        due_date=date(2025, 3, 31),
        status=status,
    )
    db.session.add(fr)
    db.session.commit()
    return fr


def _post_discount(client, token, record_id, discount_type='scholarship', amount=500.0, reason=None):
    payload = {
        'discount_type': discount_type,
        'amount': amount,
    }
    if reason is not None:
        payload['reason'] = reason
    return client.post(
        f'/api/v1/fees/records/{record_id}/discount',
        json=payload,
        headers={'Authorization': f'Bearer {token}'},
    )


# ---------------------------------------------------------------------------
# 1. test_apply_discount_success
# ---------------------------------------------------------------------------

class TestApplyDiscountSuccess:

    def test_apply_discount_success(self, client, admin_token, db):
        """Apply a scholarship discount; verify net_amount is recalculated and 201 returned."""
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=5000.00)
        student = make_student_user(db)
        fee_record = make_fee_record(db, student.id, fs.id, amount=5000.00)

        resp = _post_discount(client, admin_token, fee_record.id,
                              discount_type='scholarship', amount=1000.0,
                              reason='Merit award')

        assert resp.status_code == 201
        body = resp.get_json()
        assert body['success'] is True
        data = body['data']
        assert data['discount_type'] == 'scholarship'
        assert data['amount'] == 1000.0
        assert data['reason'] == 'Merit award'
        assert data['fee_record_id'] == fee_record.id
        assert data['approved_by'] is not None

        # Confirm net_amount updated: 5000 - 1000 = 4000
        db.session.refresh(fee_record)
        assert float(fee_record.net_amount) == 4000.0
        assert fee_record.status == 'pending'


# ---------------------------------------------------------------------------
# 2. test_apply_discount_recalculates_net
# ---------------------------------------------------------------------------

class TestApplyDiscountRecalculatesNet:

    def test_apply_discount_recalculates_net(self, client, admin_token, db):
        """Two sequential discounts: net_amount = amount_due - sum of both discounts."""
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=6000.00)
        student = make_student_user(db)
        fee_record = make_fee_record(db, student.id, fs.id, amount=6000.00)

        # First discount: 1000
        resp1 = _post_discount(client, admin_token, fee_record.id,
                               discount_type='sibling', amount=1000.0)
        assert resp1.status_code == 201
        db.session.refresh(fee_record)
        assert float(fee_record.net_amount) == 5000.0

        # Second discount: 500
        resp2 = _post_discount(client, admin_token, fee_record.id,
                               discount_type='staff', amount=500.0)
        assert resp2.status_code == 201
        db.session.refresh(fee_record)
        # net_amount = 6000 - (1000 + 500) = 4500
        assert float(fee_record.net_amount) == 4500.0


# ---------------------------------------------------------------------------
# 3. test_apply_discount_rejects_paid_record
# ---------------------------------------------------------------------------

class TestApplyDiscountRejectsPaidRecord:

    def test_apply_discount_rejects_paid_record(self, client, admin_token, db):
        """Returns 422 when the fee record is already in 'paid' status."""
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=3000.00)
        student = make_student_user(db)
        fee_record = make_fee_record(db, student.id, fs.id, amount=3000.00, status='paid')

        resp = _post_discount(client, admin_token, fee_record.id,
                              discount_type='custom', amount=200.0)

        assert resp.status_code == 422
        body = resp.get_json()
        assert body['success'] is False
        assert 'paid' in body['message'].lower()

    def test_apply_discount_rejects_waived_record(self, client, admin_token, db):
        """Returns 422 when the fee record is already in 'waived' status."""
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=3000.00)
        student = make_student_user(db)
        fee_record = make_fee_record(db, student.id, fs.id, amount=3000.00, status='waived')

        resp = _post_discount(client, admin_token, fee_record.id,
                              discount_type='custom', amount=200.0)

        assert resp.status_code == 422
        body = resp.get_json()
        assert body['success'] is False
        assert 'waived' in body['message'].lower()


# ---------------------------------------------------------------------------
# 4. test_apply_discount_record_not_found
# ---------------------------------------------------------------------------

class TestApplyDiscountRecordNotFound:

    def test_apply_discount_record_not_found(self, client, admin_token):
        """Returns 404 when the referenced fee_record_id does not exist."""
        resp = _post_discount(client, admin_token, record_id=99999,
                              discount_type='scholarship', amount=100.0)

        assert resp.status_code == 404
        body = resp.get_json()
        assert body['success'] is False


# ---------------------------------------------------------------------------
# 5. test_apply_discount_requires_admin
# ---------------------------------------------------------------------------

class TestApplyDiscountRequiresAdmin:

    def test_teacher_gets_403(self, client, teacher_token, admin_token, db):
        """Teacher cannot apply a discount — must receive 403."""
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=4000.00)
        student = make_student_user(db)
        fee_record = make_fee_record(db, student.id, fs.id, amount=4000.00)

        resp = _post_discount(client, teacher_token, fee_record.id,
                              discount_type='custom', amount=200.0)

        assert resp.status_code == 403
        body = resp.get_json()
        assert body['success'] is False

    def test_unauthenticated_gets_401(self, client, db):
        """Request without JWT must be rejected (401/422)."""
        resp = client.post(
            '/api/v1/fees/records/1/discount',
            json={'discount_type': 'scholarship', 'amount': 100.0},
        )
        assert resp.status_code in (401, 422)


# ---------------------------------------------------------------------------
# 6. TestGetFeeRecord (GET /api/v1/fees/records/<id>)
# ---------------------------------------------------------------------------

class TestGetFeeRecord:

    def test_get_fee_record_with_discounts(self, client, admin_token, db):
        """GET single fee record returns record dict with embedded discounts list."""
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=8000.00)
        student = make_student_user(db)
        fee_record = make_fee_record(db, student.id, fs.id, amount=8000.00)

        # Apply one discount first
        _post_discount(client, admin_token, fee_record.id,
                       discount_type='scholarship', amount=2000.0)

        resp = client.get(
            f'/api/v1/fees/records/{fee_record.id}',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        data = body['data']
        assert data['id'] == fee_record.id
        assert 'discounts' in data
        assert len(data['discounts']) == 1
        assert data['discounts'][0]['discount_type'] == 'scholarship'
        assert data['discounts'][0]['amount'] == 2000.0

    def test_get_fee_record_not_found(self, client, admin_token):
        """Returns 404 for a non-existent record id."""
        resp = client.get(
            '/api/v1/fees/records/99999',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 404
        body = resp.get_json()
        assert body['success'] is False

    def test_get_fee_record_teacher_gets_403(self, client, teacher_token, db):
        """Teacher cannot access the single-record endpoint."""
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=3000.00)
        student = make_student_user(db)
        fee_record = make_fee_record(db, student.id, fs.id, amount=3000.00)

        resp = client.get(
            f'/api/v1/fees/records/{fee_record.id}',
            headers={'Authorization': f'Bearer {teacher_token}'},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# 7. TestDiscountValidation
# ---------------------------------------------------------------------------

class TestDiscountValidation:

    def test_invalid_discount_type_returns_422(self, client, admin_token, db):
        """Marshmallow must reject unknown discount_type values."""
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=3000.00)
        student = make_student_user(db)
        fee_record = make_fee_record(db, student.id, fs.id, amount=3000.00)

        resp = client.post(
            f'/api/v1/fees/records/{fee_record.id}/discount',
            json={'discount_type': 'invalid_type', 'amount': 100.0},
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 422
        body = resp.get_json()
        assert body['success'] is False

    def test_zero_amount_returns_422(self, client, admin_token, db):
        """Marshmallow must reject amount=0."""
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=3000.00)
        student = make_student_user(db)
        fee_record = make_fee_record(db, student.id, fs.id, amount=3000.00)

        resp = client.post(
            f'/api/v1/fees/records/{fee_record.id}/discount',
            json={'discount_type': 'scholarship', 'amount': 0},
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 422
        body = resp.get_json()
        assert body['success'] is False

    def test_missing_discount_type_returns_422(self, client, admin_token, db):
        """Marshmallow must reject payload missing discount_type."""
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=3000.00)
        student = make_student_user(db)
        fee_record = make_fee_record(db, student.id, fs.id, amount=3000.00)

        resp = client.post(
            f'/api/v1/fees/records/{fee_record.id}/discount',
            json={'amount': 100.0},
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 422
        body = resp.get_json()
        assert body['success'] is False


# ---------------------------------------------------------------------------
# 8. TestDiscountFlipsStatusToPaid
# ---------------------------------------------------------------------------

class TestDiscountFlipsStatusToPaid:

    def test_discount_covering_full_balance_marks_paid(self, client, admin_token, db):
        """
        If discount equals amount_due and no prior payments exist,
        status should flip to 'paid' after applying the discount.
        """
        cls = make_class(db)
        ay = make_academic_year(db)
        fs = make_fee_structure(db, cls.id, ay.id, amount=2000.00)
        student = make_student_user(db)
        fee_record = make_fee_record(db, student.id, fs.id, amount=2000.00)

        resp = _post_discount(client, admin_token, fee_record.id,
                              discount_type='scholarship', amount=2000.0,
                              reason='Full scholarship')

        assert resp.status_code == 201
        db.session.refresh(fee_record)
        assert float(fee_record.net_amount) == 0.0
        assert fee_record.status == 'paid'
