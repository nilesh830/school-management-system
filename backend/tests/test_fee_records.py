"""
SMS-036 — Generate Student Fee Records
Tests: bulk generation, idempotency, partial skips, not-found, authorization
"""
import pytest
from datetime import date
from app.models.user import User
from app.models.student import Student
from app.models.class_ import Class
from app.models.section import Section
from app.models.student_section import StudentSection
from app.models.academic_year import AcademicYear
from app.models.fee_structure import FeeStructure
from app.models.fee_record import FeeRecord


# ---------------------------------------------------------------------------
# Helpers (mirror the pattern from test_fee_structures.py / test_attendance.py)
# ---------------------------------------------------------------------------

def make_class(db, name='Grade 1', grade_level=1):
    c = Class(name=name, grade_level=grade_level)
    db.session.add(c)
    db.session.commit()
    return c


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


def make_fee_structure(db, class_id, academic_year_id, fee_type='Tuition Fee', amount=5000.00):
    fs = FeeStructure(
        class_id=class_id,
        academic_year_id=academic_year_id,
        fee_type=fee_type,
        amount=amount,
        is_recurring=True,
        frequency='monthly',
    )
    db.session.add(fs)
    db.session.commit()
    return fs


def make_section(db, class_id, name='A'):
    s = Section(name=name, class_id=class_id)
    db.session.add(s)
    db.session.commit()
    return s


def make_student_user(db, email, admission_no):
    u = User(
        email=email,
        role='student',
        first_name='Test',
        last_name='Student',
    )
    u.set_password('Student@123')
    db.session.add(u)
    db.session.flush()

    s = Student(
        user_id=u.id,
        admission_no=admission_no,
        first_name='Test',
        last_name='Student',
        date_of_birth=date(2012, 1, 1),
        gender='Female',
        admission_date=date(2024, 6, 1),
        is_active=True,
    )
    db.session.add(s)
    db.session.commit()
    return s


def enroll(db, student_id, section_id, is_current=True):
    ss = StudentSection(
        student_id=student_id,
        section_id=section_id,
        academic_year='2024-2025',
        start_date=date(2024, 6, 1),
        is_current=is_current,
    )
    db.session.add(ss)
    db.session.commit()
    return ss


# ---------------------------------------------------------------------------
# 1. test_generate_fee_records_for_class
#    Create class, section, 2 active enrolled students, fee structure
#    → POST generate → 200, generated=2, skipped=0
# ---------------------------------------------------------------------------

class TestGenerateFeeRecordsForClass:

    def test_generate_fee_records_for_class(self, client, admin_token, db):
        cls = make_class(db, name='Grade 1', grade_level=1)
        ay = make_academic_year(db, name='2024-2025')
        section = make_section(db, cls.id, name='A')
        fs = make_fee_structure(db, cls.id, ay.id, fee_type='Tuition Fee', amount=5000.00)

        student_a = make_student_user(db, 'student_a@test.sms', 'ADM-036-001')
        student_b = make_student_user(db, 'student_b@test.sms', 'ADM-036-002')
        enroll(db, student_a.id, section.id)
        enroll(db, student_b.id, section.id)

        resp = client.post(
            f'/api/v1/fee-structures/{fs.id}/generate',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        assert body['data']['generated'] == 2
        assert body['data']['skipped'] == 0
        assert body['data']['total_students'] == 2


# ---------------------------------------------------------------------------
# 2. test_generate_skips_already_generated
#    Generate once → generate again → generated=0, skipped=2
# ---------------------------------------------------------------------------

class TestGenerateSkipsAlreadyGenerated:

    def test_generate_skips_already_generated(self, client, admin_token, db):
        cls = make_class(db, name='Grade 2', grade_level=2)
        ay = make_academic_year(db, name='2024-2025-B')
        section = make_section(db, cls.id, name='A')
        fs = make_fee_structure(db, cls.id, ay.id, fee_type='Library Fee', amount=200.00)

        student_a = make_student_user(db, 'student_c@test.sms', 'ADM-036-003')
        student_b = make_student_user(db, 'student_d@test.sms', 'ADM-036-004')
        enroll(db, student_a.id, section.id)
        enroll(db, student_b.id, section.id)

        headers = {'Authorization': f'Bearer {admin_token}'}
        url = f'/api/v1/fee-structures/{fs.id}/generate'

        # First generation
        resp1 = client.post(url, headers=headers)
        assert resp1.status_code == 200
        assert resp1.get_json()['data']['generated'] == 2

        # Second generation — should skip both
        resp2 = client.post(url, headers=headers)
        assert resp2.status_code == 200
        body = resp2.get_json()
        assert body['success'] is True
        assert body['data']['generated'] == 0
        assert body['data']['skipped'] == 2
        assert body['data']['total_students'] == 2


# ---------------------------------------------------------------------------
# 3. test_partial_generation
#    2 enrolled students, 1 already has a record → generated=1, skipped=1
# ---------------------------------------------------------------------------

class TestPartialGeneration:

    def test_partial_generation(self, client, admin_token, db):
        cls = make_class(db, name='Grade 3', grade_level=3)
        ay = make_academic_year(db, name='2024-2025-C')
        section = make_section(db, cls.id, name='A')
        fs = make_fee_structure(db, cls.id, ay.id, fee_type='Sports Fee', amount=300.00)

        student_a = make_student_user(db, 'student_e@test.sms', 'ADM-036-005')
        student_b = make_student_user(db, 'student_f@test.sms', 'ADM-036-006')
        enroll(db, student_a.id, section.id)
        enroll(db, student_b.id, section.id)

        # Pre-create a record for student_a only
        existing_record = FeeRecord(
            student_id=student_a.id,
            fee_structure_id=fs.id,
            amount=fs.amount,
            discount=0,
            net_amount=fs.amount,
            due_date=fs.due_date,
            status='pending',
        )
        db.session.add(existing_record)
        db.session.commit()

        resp = client.post(
            f'/api/v1/fee-structures/{fs.id}/generate',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        assert body['data']['generated'] == 1
        assert body['data']['skipped'] == 1
        assert body['data']['total_students'] == 2


# ---------------------------------------------------------------------------
# 4. test_generate_fee_structure_not_found
#    POST to a non-existent fee_structure_id → 404
# ---------------------------------------------------------------------------

class TestGenerateFeeStructureNotFound:

    def test_generate_fee_structure_not_found(self, client, admin_token):
        resp = client.post(
            '/api/v1/fee-structures/99999/generate',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 404
        body = resp.get_json()
        assert body['success'] is False


# ---------------------------------------------------------------------------
# 5. test_teacher_cannot_generate
#    Teacher token → 403 (admin-only endpoint)
# ---------------------------------------------------------------------------

class TestTeacherCannotGenerate:

    def test_teacher_cannot_generate(self, client, teacher_token, admin_token, db):
        cls = make_class(db, name='Grade 4', grade_level=4)
        ay = make_academic_year(db, name='2024-2025-D')
        fs = make_fee_structure(db, cls.id, ay.id, fee_type='Exam Fee', amount=150.00)

        resp = client.post(
            f'/api/v1/fee-structures/{fs.id}/generate',
            headers={'Authorization': f'Bearer {teacher_token}'},
        )

        assert resp.status_code == 403
        body = resp.get_json()
        assert body['success'] is False
