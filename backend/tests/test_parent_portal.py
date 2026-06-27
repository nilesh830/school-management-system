"""
Sprint 7 — Parent Portal: Core
Tests for ParentPortalService real ORM implementations and HTTP routes.

Coverage:
  - Dashboard: structure, no-children, role guard
  - Child Attendance: current month, specific month/year filter, data isolation
  - Child Grades: exams list, empty, data isolation
  - Child Fees: totals + records, data isolation
  - Notifications: list, mark-read
"""
import pytest
from datetime import date, timedelta

from app.models.user import User
from app.models.student import Student
from app.models.parent import Parent, student_parent
from app.models.attendance import Attendance
from app.models.section import Section
from app.models.class_ import Class
from app.models.student_section import StudentSection
from app.models.academic_year import AcademicYear
from app.models.fee_structure import FeeStructure
from app.models.fee_record import FeeRecord
from app.models.fee_payment import FeePayment
from app.models.exam import Exam
from app.models.exam_result import ExamResult
from app.models.subject import Subject
from app.models.notification import Notification


# ---------------------------------------------------------------------------
# Module-level unique-ID generator (avoids collisions across tests)
# ---------------------------------------------------------------------------

_counter = 0


def _uid():
    global _counter
    _counter += 1
    return _counter


# ---------------------------------------------------------------------------
# Low-level helpers (no fixtures needed, take db explicitly)
# ---------------------------------------------------------------------------

def make_class(db):
    uid = _uid()
    c = Class(name=f'PP-Grade-{uid}', grade_level=(uid % 12) + 1)
    db.session.add(c)
    db.session.commit()
    return c


def make_section(db, class_id):
    uid = _uid()
    s = Section(name=f'PP{uid}', class_id=class_id)
    db.session.add(s)
    db.session.commit()
    return s


def make_academic_year(db):
    uid = _uid()
    ay = AcademicYear(
        name=f'AY-PP-{uid}',
        start_date=date(2024, 6, 1),
        end_date=date(2025, 5, 31),
        is_current=True,
        is_active=True,
    )
    db.session.add(ay)
    db.session.commit()
    return ay


def enroll(db, student_id, section_id):
    ss = StudentSection(
        student_id=student_id,
        section_id=section_id,
        academic_year='2024-2025',
        start_date=date(2024, 6, 1),
        is_current=True,
    )
    db.session.add(ss)
    db.session.commit()
    return ss


def make_student_user(db):
    """Create a User + Student pair. Returns (user, student)."""
    uid = _uid()
    u = User(
        email=f'pp_student_{uid}@test.sms',
        role='student',
        first_name=f'PPStudent{uid}',
        last_name='Test',
    )
    u.set_password('Student@123')
    db.session.add(u)
    db.session.flush()

    s = Student(
        user_id=u.id,
        admission_no=f'PP-ADM-{uid:05d}',
        first_name=f'PPStudent{uid}',
        last_name='Test',
        date_of_birth=date(2012, 1, 1),
        gender='Female',
        admission_date=date(2024, 6, 1),
    )
    db.session.add(s)
    db.session.commit()
    return u, s


def make_parent_user(db):
    """Create a User + Parent pair. Returns (user, parent)."""
    uid = _uid()
    u = User(
        email=f'pp_parent_{uid}@test.sms',
        role='parent',
        first_name=f'PPParent{uid}',
        last_name='Test',
    )
    u.set_password('Parent@123')
    db.session.add(u)
    db.session.flush()

    p = Parent(
        user_id=u.id,
        first_name=f'PPParent{uid}',
        last_name='Test',
        relationship_type='Father',
        phone_primary='+91-9000000001',
    )
    db.session.add(p)
    db.session.commit()
    return u, p


def link_parent_student(db, parent_id, student_id):
    db.session.execute(
        student_parent.insert().values(
            parent_id=parent_id,
            student_id=student_id,
            is_primary_contact=True,
        )
    )
    db.session.commit()


def make_fee_setup(db, student_id):
    """Create FeeStructure + FeeRecord for a student. Returns (fee_structure, fee_record)."""
    cls = make_class(db)
    ay = make_academic_year(db)
    uid = _uid()
    fs = FeeStructure(
        class_id=cls.id,
        academic_year_id=ay.id,
        fee_type=f'Tuition-PP-{uid}',
        amount=5000.00,
        is_recurring=False,
        frequency='one_time',
    )
    db.session.add(fs)
    db.session.flush()

    fr = FeeRecord(
        student_id=student_id,
        fee_structure_id=fs.id,
        amount=5000.00,
        discount=0,
        net_amount=5000.00,
        due_date=date(2025, 3, 31),
        status='pending',
    )
    db.session.add(fr)
    db.session.commit()
    return fs, fr


def make_fee_payment(db, fee_record_id, amount=2000.00):
    uid = _uid()
    pay = FeePayment(
        fee_record_id=fee_record_id,
        amount_paid=amount,
        payment_method='cash',
        payment_date=date(2025, 1, 15),
        receipt_no=f'REC-PP-{uid:06d}',
    )
    db.session.add(pay)
    db.session.commit()
    return pay


def make_exam_and_results(db, student_id, section_id, academic_year_id):
    """Create an Exam + Subject + ExamResults. Returns (exam, subject, results)."""
    uid = _uid()
    exam = Exam(
        name=f'Midterm PP {uid}',
        term='Term 1',
        exam_type='midterm',
        section_id=section_id,
        conducted_date=date(2025, 1, 20),
        academic_year_id=academic_year_id,
        is_active=True,
    )
    db.session.add(exam)
    db.session.flush()

    subject = Subject(
        name=f'Mathematics PP {uid}',
        code=f'MATH-PP-{uid}',
        max_marks=100,
        pass_marks=35,
    )
    db.session.add(subject)
    db.session.flush()

    result = ExamResult(
        exam_id=exam.id,
        student_id=student_id,
        subject_id=subject.id,
        marks_obtained=75.0,
        grade='B+',
        gpa=3.3,
        status='finalized',
    )
    db.session.add(result)
    db.session.commit()
    return exam, subject, result


def _login(client, email, password, school_slug='test'):
    resp = client.post('/api/v1/auth/login', json={
        'email': email, 'password': password, 'school_slug': school_slug
    })
    return resp.get_json()['data']


def _get_parent_token(client, parent_user_email):
    return _login(client, parent_user_email, 'Parent@123')['access_token']


# ---------------------------------------------------------------------------
# Reusable fixture: full parent portal setup (parent + child + data)
# ---------------------------------------------------------------------------

@pytest.fixture
def parent_setup(db, client):
    """
    Creates:
      - A parent User + Parent record
      - A student User + Student record, enrolled in a section
      - student_parent link
      - 3 Attendance rows for 2026-06 (2 present, 1 absent)
      - 1 FeeRecord (pending) + 1 FeePayment
      - 1 Exam + 1 Subject + 1 ExamResult
    Returns a dict with all created objects and the parent's access token.
    """
    parent_user, parent = make_parent_user(db)
    _, student = make_student_user(db)
    link_parent_student(db, parent.id, student.id)

    cls = make_class(db)
    section = make_section(db, cls.id)
    enroll(db, student.id, section.id)
    ay = make_academic_year(db)

    # Attendance: June 2026 — 2 present, 1 absent
    for day, status in [(1, 'present'), (2, 'present'), (3, 'absent')]:
        db.session.add(Attendance(
            student_id=student.id,
            section_id=section.id,
            date=date(2026, 6, day),
            status=status,
        ))
    db.session.commit()

    # Fees
    fee_structure, fee_record = make_fee_setup(db, student.id)
    payment = make_fee_payment(db, fee_record.id, amount=2000.00)

    # Exam results
    exam, subject, result = make_exam_and_results(db, student.id, section.id, ay.id)

    token = _get_parent_token(client, parent_user.email)

    return {
        'parent_user': parent_user,
        'parent': parent,
        'student': student,
        'section': section,
        'cls': cls,
        'ay': ay,
        'fee_structure': fee_structure,
        'fee_record': fee_record,
        'payment': payment,
        'exam': exam,
        'subject': subject,
        'result': result,
        'token': token,
    }


# ---------------------------------------------------------------------------
# Helper: build auth header
# ---------------------------------------------------------------------------

def _h(token):
    return {'Authorization': f'Bearer {token}'}


# ===========================================================================
# Dashboard tests
# ===========================================================================

class TestDashboard:

    def test_dashboard_returns_child_summary(self, client, parent_setup):
        resp = client.get(
            '/api/v1/parent-portal/dashboard',
            headers=_h(parent_setup['token']),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True

        data = body['data']
        assert 'parent' in data
        assert 'children' in data
        assert 'unread_notifications' in data
        assert len(data['children']) == 1

        child = data['children'][0]
        assert 'student' in child
        assert child['student']['id'] == parent_setup['student'].id
        assert 'attendance_summary' in child
        assert 'pending_fees' in child
        assert 'recent_grades' in child

    def test_dashboard_attendance_summary_counts(self, client, parent_setup):
        """Attendance summary for current month reflects seeded data only if today is June 2026.
        The service uses date.today(), so we verify the structure is correct."""
        resp = client.get(
            '/api/v1/parent-portal/dashboard',
            headers=_h(parent_setup['token']),
        )
        data = resp.get_json()['data']
        summary = data['children'][0]['attendance_summary']
        assert 'month' in summary
        assert 'year' in summary
        assert 'present' in summary
        assert 'absent' in summary
        assert 'late' in summary
        assert 'percentage' in summary

    def test_dashboard_no_children_returns_empty_list(self, client, db):
        """Parent with no linked children gets empty children list."""
        parent_user, parent = make_parent_user(db)
        token = _get_parent_token(client, parent_user.email)

        resp = client.get(
            '/api/v1/parent-portal/dashboard',
            headers=_h(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['children'] == []

    def test_dashboard_requires_parent_role(self, client, admin_token):
        """Admin JWT must be rejected with 403."""
        resp = client.get(
            '/api/v1/parent-portal/dashboard',
            headers=_h(admin_token),
        )
        assert resp.status_code == 403

    def test_dashboard_unauthenticated_returns_401(self, client):
        resp = client.get('/api/v1/parent-portal/dashboard')
        assert resp.status_code == 401


# ===========================================================================
# Children list tests
# ===========================================================================

class TestListChildren:

    def test_list_children_returns_linked_students(self, client, parent_setup):
        resp = client.get(
            '/api/v1/parent-portal/children',
            headers=_h(parent_setup['token']),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        children = body['data']['children']
        assert len(children) == 1
        assert children[0]['id'] == parent_setup['student'].id

    def test_list_children_empty_for_new_parent(self, client, db):
        parent_user, _ = make_parent_user(db)
        token = _get_parent_token(client, parent_user.email)
        resp = client.get(
            '/api/v1/parent-portal/children',
            headers=_h(token),
        )
        assert resp.status_code == 200
        assert resp.get_json()['data']['children'] == []


# ===========================================================================
# Child Attendance tests
# ===========================================================================

class TestChildAttendance:

    def test_child_attendance_current_month_structure(self, client, parent_setup):
        s = parent_setup['student']
        resp = client.get(
            f'/api/v1/parent-portal/children/{s.id}/attendance',
            headers=_h(parent_setup['token']),
        )
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['student_id'] == s.id
        assert 'month' in data
        assert 'year' in data
        assert 'records' in data
        assert 'summary' in data
        summary = data['summary']
        assert 'present' in summary
        assert 'absent' in summary
        assert 'late' in summary
        assert 'holidays' in summary
        assert 'percentage' in summary

    def test_child_attendance_specific_month_returns_correct_counts(self, client, parent_setup):
        """Query June 2026 explicitly — should return 2 present + 1 absent from fixture."""
        s = parent_setup['student']
        resp = client.get(
            f'/api/v1/parent-portal/children/{s.id}/attendance?month=6&year=2026',
            headers=_h(parent_setup['token']),
        )
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['month'] == 6
        assert data['year'] == 2026
        assert len(data['records']) == 3

        summary = data['summary']
        assert summary['present'] == 2
        assert summary['absent'] == 1
        assert summary['late'] == 0
        assert summary['holidays'] == 0
        # percentage = 2 / (2+1) * 100 = 66.7
        assert summary['percentage'] == round(2 / 3 * 100, 1)

    def test_child_attendance_other_month_returns_empty(self, client, parent_setup, db):
        """Query July 2026 — no rows seeded for that month, expect empty records."""
        s = parent_setup['student']
        resp = client.get(
            f'/api/v1/parent-portal/children/{s.id}/attendance?month=7&year=2026',
            headers=_h(parent_setup['token']),
        )
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['records'] == []
        assert data['summary']['present'] == 0
        assert data['summary']['percentage'] == 0.0

    def test_child_attendance_records_sorted_by_date(self, client, parent_setup):
        s = parent_setup['student']
        resp = client.get(
            f'/api/v1/parent-portal/children/{s.id}/attendance?month=6&year=2026',
            headers=_h(parent_setup['token']),
        )
        records = resp.get_json()['data']['records']
        dates = [r['date'] for r in records]
        assert dates == sorted(dates)

    def test_child_attendance_data_isolation(self, client, db, parent_setup):
        """Another parent cannot access the child's attendance."""
        other_parent_user, _ = make_parent_user(db)
        other_token = _get_parent_token(client, other_parent_user.email)

        s = parent_setup['student']
        resp = client.get(
            f'/api/v1/parent-portal/children/{s.id}/attendance',
            headers=_h(other_token),
        )
        assert resp.status_code == 403


# ===========================================================================
# Child Grades tests
# ===========================================================================

class TestChildGrades:

    def test_child_grades_returns_exams_with_subject_breakdown(self, client, parent_setup):
        s = parent_setup['student']
        resp = client.get(
            f'/api/v1/parent-portal/children/{s.id}/grades',
            headers=_h(parent_setup['token']),
        )
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['student_id'] == s.id
        assert 'exams' in data
        assert len(data['exams']) == 1

        exam_data = data['exams'][0]
        assert exam_data['exam_id'] == parent_setup['exam'].id
        assert exam_data['exam_name'] == parent_setup['exam'].name
        assert exam_data['term'] == parent_setup['exam'].term
        assert 'subjects' in exam_data
        assert len(exam_data['subjects']) == 1
        assert 'average_percentage' in exam_data
        assert 'overall_grade' in exam_data
        assert 'gpa' in exam_data

        subject_entry = exam_data['subjects'][0]
        assert subject_entry['subject_id'] == parent_setup['subject'].id
        assert subject_entry['marks_obtained'] == 75.0
        assert subject_entry['max_marks'] == float(parent_setup['subject'].max_marks)
        assert subject_entry['grade'] == 'B+'

    def test_child_grades_average_percentage_calculation(self, client, parent_setup):
        """75 / 100 * 100 = 75.0%"""
        s = parent_setup['student']
        resp = client.get(
            f'/api/v1/parent-portal/children/{s.id}/grades',
            headers=_h(parent_setup['token']),
        )
        exam_data = resp.get_json()['data']['exams'][0]
        assert exam_data['average_percentage'] == 75.0

    def test_child_grades_empty_for_student_with_no_results(self, client, db, parent_setup):
        """A freshly linked student with no exam results returns empty exams list."""
        parent_user, parent = make_parent_user(db)
        _, new_student = make_student_user(db)
        link_parent_student(db, parent.id, new_student.id)

        token = _get_parent_token(client, parent_user.email)
        resp = client.get(
            f'/api/v1/parent-portal/children/{new_student.id}/grades',
            headers=_h(token),
        )
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['exams'] == []

    def test_child_grades_multiple_subjects(self, client, db, parent_setup):
        """Add a second subject result to the existing exam and verify both appear."""
        uid = _uid()
        new_subject = Subject(
            name=f'Science PP {uid}',
            code=f'SCI-PP-{uid}',
            max_marks=100,
            pass_marks=35,
        )
        db.session.add(new_subject)
        db.session.flush()

        db.session.add(ExamResult(
            exam_id=parent_setup['exam'].id,
            student_id=parent_setup['student'].id,
            subject_id=new_subject.id,
            marks_obtained=85.0,
            grade='A',
            gpa=4.0,
            status='finalized',
        ))
        db.session.commit()

        resp = client.get(
            f'/api/v1/parent-portal/children/{parent_setup["student"].id}/grades',
            headers=_h(parent_setup['token']),
        )
        exam_data = resp.get_json()['data']['exams'][0]
        assert len(exam_data['subjects']) == 2
        # avg pct = (75 + 85) / 2 = 80.0
        assert exam_data['average_percentage'] == 80.0

    def test_child_grades_data_isolation(self, client, db, parent_setup):
        """Another parent cannot access a child's grades."""
        other_parent_user, _ = make_parent_user(db)
        other_token = _get_parent_token(client, other_parent_user.email)

        resp = client.get(
            f'/api/v1/parent-portal/children/{parent_setup["student"].id}/grades',
            headers=_h(other_token),
        )
        assert resp.status_code == 403


# ===========================================================================
# Child Fees tests
# ===========================================================================

class TestChildFees:

    def test_child_fees_returns_correct_structure(self, client, parent_setup):
        s = parent_setup['student']
        resp = client.get(
            f'/api/v1/parent-portal/children/{s.id}/fees',
            headers=_h(parent_setup['token']),
        )
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['student_id'] == s.id
        assert 'total_due' in data
        assert 'total_paid' in data
        assert 'records' in data

    def test_child_fees_total_due_excludes_nothing_for_pending(self, client, parent_setup):
        """FeeRecord is pending with net_amount=5000 — total_due should be 5000."""
        s = parent_setup['student']
        resp = client.get(
            f'/api/v1/parent-portal/children/{s.id}/fees',
            headers=_h(parent_setup['token']),
        )
        data = resp.get_json()['data']
        assert data['total_due'] == 5000.0

    def test_child_fees_total_paid_sums_payments(self, client, parent_setup):
        """One payment of 2000 was made — total_paid should be 2000."""
        s = parent_setup['student']
        resp = client.get(
            f'/api/v1/parent-portal/children/{s.id}/fees',
            headers=_h(parent_setup['token']),
        )
        data = resp.get_json()['data']
        assert data['total_paid'] == 2000.0

    def test_child_fees_record_has_payment_info(self, client, parent_setup):
        s = parent_setup['student']
        resp = client.get(
            f'/api/v1/parent-portal/children/{s.id}/fees',
            headers=_h(parent_setup['token']),
        )
        records = resp.get_json()['data']['records']
        assert len(records) == 1
        record = records[0]
        assert record['id'] == parent_setup['fee_record'].id
        assert record['status'] == 'pending'
        assert record['fee_type'] == parent_setup['fee_structure'].fee_type
        assert record['amount'] == 5000.0
        assert record['net_amount'] == 5000.0
        assert record['payment_id'] == parent_setup['payment'].id
        assert record['receipt_no'] == parent_setup['payment'].receipt_no

    def test_child_fees_no_payments_shows_none(self, client, db):
        """FeeRecord with no payments has payment_id=None and receipt_no=None."""
        parent_user, parent = make_parent_user(db)
        _, student = make_student_user(db)
        link_parent_student(db, parent.id, student.id)
        _, fee_record = make_fee_setup(db, student.id)
        # No payment added

        token = _get_parent_token(client, parent_user.email)
        resp = client.get(
            f'/api/v1/parent-portal/children/{student.id}/fees',
            headers=_h(token),
        )
        data = resp.get_json()['data']
        assert data['total_paid'] == 0.0
        assert len(data['records']) == 1
        rec = data['records'][0]
        assert rec['payment_id'] is None
        assert rec['receipt_no'] is None

    def test_child_fees_paid_record_not_in_total_due(self, client, db):
        """A paid FeeRecord should NOT appear in total_due."""
        parent_user, parent = make_parent_user(db)
        _, student = make_student_user(db)
        link_parent_student(db, parent.id, student.id)

        cls = make_class(db)
        ay = make_academic_year(db)
        uid = _uid()
        fs = FeeStructure(
            class_id=cls.id,
            academic_year_id=ay.id,
            fee_type=f'Tuition-Paid-{uid}',
            amount=3000.00,
            is_recurring=False,
            frequency='one_time',
        )
        db.session.add(fs)
        db.session.flush()

        paid_record = FeeRecord(
            student_id=student.id,
            fee_structure_id=fs.id,
            amount=3000.00,
            discount=0,
            net_amount=3000.00,
            due_date=date(2025, 1, 31),
            status='paid',
        )
        db.session.add(paid_record)
        db.session.commit()

        token = _get_parent_token(client, parent_user.email)
        resp = client.get(
            f'/api/v1/parent-portal/children/{student.id}/fees',
            headers=_h(token),
        )
        data = resp.get_json()['data']
        assert data['total_due'] == 0.0

    def test_child_fees_data_isolation(self, client, db, parent_setup):
        """Another parent cannot access a child's fee records."""
        other_parent_user, _ = make_parent_user(db)
        other_token = _get_parent_token(client, other_parent_user.email)

        resp = client.get(
            f'/api/v1/parent-portal/children/{parent_setup["student"].id}/fees',
            headers=_h(other_token),
        )
        assert resp.status_code == 403


# ===========================================================================
# Notifications tests
# ===========================================================================

class TestNotifications:

    def _create_notification(self, db, user_id, title='Test Notification', is_read=False):
        n = Notification(
            user_id=user_id,
            type='general',
            title=title,
            body='This is a test notification body.',
            is_read=is_read,
        )
        db.session.add(n)
        db.session.commit()
        return n

    def test_list_notifications_returns_own_notifications(self, client, parent_setup, db):
        parent_user = parent_setup['parent_user']
        self._create_notification(db, parent_user.id, title='Fee Due')
        self._create_notification(db, parent_user.id, title='Exam Result')

        resp = client.get(
            '/api/v1/notifications',
            headers=_h(parent_setup['token']),
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        notifications = body['data']['notifications']
        assert len(notifications) == 2
        titles = {n['title'] for n in notifications}
        assert 'Fee Due' in titles
        assert 'Exam Result' in titles

    def test_list_notifications_unread_filter(self, client, parent_setup, db):
        parent_user = parent_setup['parent_user']
        self._create_notification(db, parent_user.id, title='Unread One', is_read=False)
        self._create_notification(db, parent_user.id, title='Already Read', is_read=True)

        resp = client.get(
            '/api/v1/notifications?unread=true',
            headers=_h(parent_setup['token']),
        )
        notifications = resp.get_json()['data']['notifications']
        assert all(not n['is_read'] for n in notifications)
        titles = [n['title'] for n in notifications]
        assert 'Unread One' in titles
        assert 'Already Read' not in titles

    def test_list_notifications_does_not_leak_other_user_notifications(self, client, parent_setup, db):
        """Notifications for a different user are NOT returned."""
        # Create another user and add a notification for them
        uid = _uid()
        other_user = User(
            email=f'other_{uid}@test.sms',
            role='parent',
            first_name='Other',
            last_name='User',
        )
        other_user.set_password('Parent@123')
        db.session.add(other_user)
        db.session.commit()
        self._create_notification(db, other_user.id, title='Other User Notif')

        resp = client.get(
            '/api/v1/notifications',
            headers=_h(parent_setup['token']),
        )
        notifications = resp.get_json()['data']['notifications']
        titles = [n['title'] for n in notifications]
        assert 'Other User Notif' not in titles

    def test_mark_notification_read(self, client, parent_setup, db):
        parent_user = parent_setup['parent_user']
        notif = self._create_notification(db, parent_user.id, is_read=False)
        assert notif.is_read is False

        resp = client.put(
            f'/api/v1/notifications/{notif.id}/read',
            headers=_h(parent_setup['token']),
        )
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True

        db.session.refresh(notif)
        assert notif.is_read is True

    def test_mark_notification_read_other_user_returns_404(self, client, parent_setup, db):
        """Cannot mark another user's notification as read."""
        uid = _uid()
        other_user = User(
            email=f'notif_other_{uid}@test.sms',
            role='parent',
            first_name='Other',
            last_name='Notif',
        )
        other_user.set_password('Parent@123')
        db.session.add(other_user)
        db.session.commit()
        notif = self._create_notification(db, other_user.id, title='Secret')

        resp = client.put(
            f'/api/v1/notifications/{notif.id}/read',
            headers=_h(parent_setup['token']),
        )
        assert resp.status_code == 404

    def test_list_notifications_admin_can_access(self, client, admin_token, db, admin_user):
        """The notifications endpoint is open to admin role too."""
        n = Notification(
            user_id=admin_user.id,
            type='general',
            title='Admin Notice',
            body='Something for admin.',
            is_read=False,
        )
        db.session.add(n)
        db.session.commit()

        resp = client.get(
            '/api/v1/notifications',
            headers=_h(admin_token),
        )
        assert resp.status_code == 200


# ===========================================================================
# Service-layer unit tests (bypass HTTP, call service directly)
# ===========================================================================

class TestParentPortalServiceUnit:

    def test_get_attendance_summary_correct_counts(self, app, db, parent_setup):
        """_get_attendance_summary uses date.today(); seed today's data to verify counts."""
        from app.services.parent_portal_service import ParentPortalService

        student = parent_setup['student']
        section = parent_setup['section']
        today = date.today()

        # Clear any existing rows for today (clean_db runs between tests so none should exist)
        db.session.add(Attendance(
            student_id=student.id,
            section_id=section.id,
            date=today,
            status='present',
        ))
        db.session.commit()

        with app.app_context():
            summary = ParentPortalService._get_attendance_summary(student.id)

        assert summary['month'] == today.month
        assert summary['year'] == today.year
        assert summary['present'] >= 1
        assert 'percentage' in summary

    def test_get_pending_fees_returns_correct_total(self, app, db, parent_setup):
        from app.services.parent_portal_service import ParentPortalService

        with app.app_context():
            result = ParentPortalService._get_pending_fees(parent_setup['student'].id)

        assert result['total_due'] == 5000.0
        assert 'overdue_count' in result

    def test_get_pending_fees_empty_for_new_student(self, app, db):
        from app.services.parent_portal_service import ParentPortalService

        _, student = make_student_user(db)

        with app.app_context():
            result = ParentPortalService._get_pending_fees(student.id)

        assert result['total_due'] == 0.0
        assert result['overdue_count'] == 0

    def test_get_recent_grades_returns_latest_exam(self, app, db, parent_setup):
        from app.services.parent_portal_service import ParentPortalService

        with app.app_context():
            result = ParentPortalService._get_recent_grades(parent_setup['student'].id)

        assert result is not None
        assert result['exam'] == parent_setup['exam'].name
        assert result['average_marks'] == 75.0
        assert result['grade'] == 'B+'

    def test_get_recent_grades_returns_none_for_no_results(self, app, db):
        from app.services.parent_portal_service import ParentPortalService

        _, student = make_student_user(db)

        with app.app_context():
            result = ParentPortalService._get_recent_grades(student.id)

        assert result is None

    def test_verify_child_access_raises_403_for_wrong_parent(self, app, db, parent_setup):
        from app.services.parent_portal_service import ParentPortalService
        from werkzeug.exceptions import Forbidden

        _, other_student = make_student_user(db)

        with app.app_context(), pytest.raises(Forbidden):
            ParentPortalService._verify_child_access(
                parent_setup['parent'].id,
                other_student.id,
            )
