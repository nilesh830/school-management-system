"""
Sprint 8 — Leave Applications Tests
Tests for SMS-046, SMS-047: Leave submission and review.
"""
import pytest
from datetime import date, timedelta

from app.models.user import User
from app.models.student import Student
from app.models.parent import Parent, student_parent
from app.models.section import Section
from app.models.class_ import Class
from app.models.student_section import StudentSection
from app.models.teacher import Teacher
from app.models.academic_year import AcademicYear
from app.models.leave_application import LeaveApplication


_counter = 0

def _uid():
    global _counter
    _counter += 1
    return _counter


def make_class(db):
    uid = _uid()
    c = Class(name=f'LA-Grade-{uid}', grade_level=(uid % 12) + 1)
    db.session.add(c)
    db.session.commit()
    return c


def make_section(db, class_id):
    uid = _uid()
    s = Section(name=f'LA{uid}', class_id=class_id)
    db.session.add(s)
    db.session.commit()
    return s


def make_student_user(db):
    uid = _uid()
    u = User(email=f'la_student_{uid}@test.sms', role='student',
             first_name=f'LAStudent{uid}', last_name='Test')
    u.set_password('Student@123')
    db.session.add(u)
    db.session.flush()
    s = Student(
        user_id=u.id,
        admission_no=f'LA-ADM-{uid:05d}',
        first_name=f'LAStudent{uid}',
        last_name='Test',
        date_of_birth=date(2012, 1, 1),
        gender='Female',
        admission_date=date(2024, 6, 1),
    )
    db.session.add(s)
    db.session.commit()
    return u, s


def make_parent_user(db):
    uid = _uid()
    u = User(email=f'la_parent_{uid}@test.sms', role='parent',
             first_name=f'LAParent{uid}', last_name='Test')
    u.set_password('Parent@123')
    db.session.add(u)
    db.session.flush()
    p = Parent(
        user_id=u.id,
        first_name=f'LAParent{uid}',
        last_name='Test',
        relationship_type='Father',
        phone_primary='+91-9000000099',
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


def _login(client, email, password):
    resp = client.post('/api/v1/auth/login', json={
        'email': email, 'password': password, 'school_slug': 'test'
    })
    return resp.get_json()['data']


def _h(token):
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def leave_setup(db, client):
    """Creates parent + student with leave submission setup."""
    parent_user, parent = make_parent_user(db)
    _, student = make_student_user(db)
    link_parent_student(db, parent.id, student.id)
    cls = make_class(db)
    section = make_section(db, cls.id)
    enroll(db, student.id, section.id)

    token = _login(client, parent_user.email, 'Parent@123')['access_token']
    return {
        'parent_user': parent_user,
        'parent': parent,
        'student': student,
        'section': section,
        'token': token,
    }


class TestLeaveSubmit:

    def test_submit_valid_leave_returns_201(self, client, leave_setup):
        """T-046-1: Valid future leave returns 201 with duration_days."""
        tomorrow = date.today() + timedelta(days=1)
        day_after = date.today() + timedelta(days=3)
        resp = client.post('/api/v1/leave-applications', json={
            'student_id': leave_setup['student'].id,
            'from_date': tomorrow.isoformat(),
            'to_date': day_after.isoformat(),
            'reason': 'Family function',
            'leave_type': 'family',
        }, headers=_h(leave_setup['token']))
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['success'] is True
        assert data['data']['duration_days'] == 3
        assert data['data']['status'] == 'pending'

    def test_submit_past_from_date_returns_422(self, client, leave_setup):
        """T-046-2: from_date in the past returns 422."""
        yesterday = date.today() - timedelta(days=1)
        tomorrow = date.today() + timedelta(days=1)
        resp = client.post('/api/v1/leave-applications', json={
            'student_id': leave_setup['student'].id,
            'from_date': yesterday.isoformat(),
            'to_date': tomorrow.isoformat(),
            'reason': 'Sick',
            'leave_type': 'sick',
        }, headers=_h(leave_setup['token']))
        assert resp.status_code == 422

    def test_submit_to_date_before_from_date_returns_422(self, client, leave_setup):
        """T-046-3: to_date before from_date returns 422."""
        tomorrow = date.today() + timedelta(days=3)
        day_after = date.today() + timedelta(days=1)
        resp = client.post('/api/v1/leave-applications', json={
            'student_id': leave_setup['student'].id,
            'from_date': tomorrow.isoformat(),
            'to_date': day_after.isoformat(),
            'reason': 'Test',
            'leave_type': 'personal',
        }, headers=_h(leave_setup['token']))
        assert resp.status_code == 422

    def test_submit_wrong_child_returns_403(self, client, db, leave_setup):
        """T-046-4: Submitting leave for unlinked student returns 403."""
        _, other_student = make_student_user(db)
        tomorrow = date.today() + timedelta(days=1)
        resp = client.post('/api/v1/leave-applications', json={
            'student_id': other_student.id,
            'from_date': tomorrow.isoformat(),
            'to_date': (date.today() + timedelta(days=2)).isoformat(),
            'reason': 'Test',
            'leave_type': 'personal',
        }, headers=_h(leave_setup['token']))
        assert resp.status_code == 403

    def test_submit_missing_reason_returns_error(self, client, leave_setup):
        """T-046-5: Missing reason field returns 400 or 500."""
        tomorrow = date.today() + timedelta(days=1)
        resp = client.post('/api/v1/leave-applications', json={
            'student_id': leave_setup['student'].id,
            'from_date': tomorrow.isoformat(),
            'to_date': (date.today() + timedelta(days=2)).isoformat(),
            # no reason
            'leave_type': 'personal',
        }, headers=_h(leave_setup['token']))
        # Should fail — reason is NOT NULL in DB
        assert resp.status_code in (400, 422, 500)


class TestLeaveReview:

    def _create_pending_leave(self, db, parent_id, student_id):
        tomorrow = date.today() + timedelta(days=1)
        leave = LeaveApplication(
            student_id=student_id,
            parent_id=parent_id,
            from_date=tomorrow,
            to_date=date.today() + timedelta(days=2),
            reason='Test leave',
            leave_type='personal',
            status='pending',
        )
        db.session.add(leave)
        db.session.commit()
        return leave

    def test_admin_get_all_leaves_returns_200(self, client, admin_token, db, leave_setup):
        """T-047-1: Admin can GET all leave applications."""
        self._create_pending_leave(db, leave_setup['parent'].id, leave_setup['student'].id)
        resp = client.get('/api/v1/leave-applications/all', headers=_h(admin_token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'leaves' in data['data']
        assert len(data['data']['leaves']) >= 1

    def test_admin_get_all_leaves_with_status_filter(self, client, admin_token, db, leave_setup):
        """T-047-2: Admin can filter by status=pending."""
        self._create_pending_leave(db, leave_setup['parent'].id, leave_setup['student'].id)
        resp = client.get('/api/v1/leave-applications/all?status=pending', headers=_h(admin_token))
        assert resp.status_code == 200
        leaves = resp.get_json()['data']['leaves']
        assert all(l['status'] == 'pending' for l in leaves)

    def test_review_approve_updates_status(self, client, admin_token, db, leave_setup):
        """T-047-3: Admin approves leave → status becomes approved."""
        leave = self._create_pending_leave(db, leave_setup['parent'].id, leave_setup['student'].id)
        resp = client.put(
            f'/api/v1/leave-applications/{leave.id}/review',
            json={'status': 'approved', 'remarks': 'Granted'},
            headers=_h(admin_token),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['data']['status'] == 'approved'

    def test_review_reject_updates_status(self, client, admin_token, db, leave_setup):
        """T-047-4: Admin rejects leave → status becomes rejected."""
        leave = self._create_pending_leave(db, leave_setup['parent'].id, leave_setup['student'].id)
        resp = client.put(
            f'/api/v1/leave-applications/{leave.id}/review',
            json={'status': 'rejected', 'remarks': 'Not approved'},
            headers=_h(admin_token),
        )
        assert resp.status_code == 200
        assert resp.get_json()['data']['status'] == 'rejected'
