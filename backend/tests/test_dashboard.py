"""
SMS-056 — Admin KPI Dashboard
Tests: all keys present, correct counts with seeded data, empty-state zeros,
       admin-only access (teacher / parent → 403).
"""
from datetime import date, timedelta

from app.models.user import User
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.class_ import Class
from app.models.section import Section
from app.models.academic_year import AcademicYear
from app.models.attendance import Attendance
from app.models.announcement import Announcement
from app.models.fee_structure import FeeStructure
from app.models.fee_record import FeeRecord
from app.models.fee_payment import FeePayment
from app.models.leave_application import LeaveApplication
from app.models.parent import Parent


_counter = 0


def _uid():
    global _counter
    _counter += 1
    return _counter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_student(db, is_active=True):
    uid = _uid()
    u = User(email=f'dstu_{uid}@test.sms', role='student',
             first_name=f'Stu{uid}', last_name='Dash')
    u.set_password('Student@123')
    db.session.add(u)
    db.session.flush()
    s = Student(
        user_id=u.id,
        admission_no=f'ADM-DASH-{uid:05d}',
        first_name=f'Stu{uid}',
        last_name='Dash',
        date_of_birth=date(2011, 1, 1),
        gender='Male',
        admission_date=date(2024, 6, 1),
        is_active=is_active,
    )
    db.session.add(s)
    db.session.commit()
    return s


def make_teacher(db, is_active=True):
    uid = _uid()
    u = User(email=f'dtea_{uid}@test.sms', role='teacher',
             first_name=f'Tea{uid}', last_name='Dash')
    u.set_password('Teacher@123')
    db.session.add(u)
    db.session.flush()
    t = Teacher(
        user_id=u.id,
        employee_id=f'EMP-DASH-{uid:05d}',
        first_name=f'Tea{uid}',
        last_name='Dash',
        joining_date=date(2023, 1, 1),
        is_active=is_active,
    )
    db.session.add(t)
    db.session.commit()
    return t


def make_section(db):
    uid = _uid()
    c = Class(name=f'Grade {uid}', grade_level=(uid % 12) + 1)
    db.session.add(c)
    db.session.commit()
    sec = Section(name=chr(64 + (uid % 26) + 1), class_id=c.id)
    db.session.add(sec)
    db.session.commit()
    return c, sec


def add_attendance(db, student_id, section_id, statuses, base=None):
    """statuses: list of status strings, one per consecutive day."""
    base = base or (date.today() - timedelta(days=len(statuses)))
    for i, status in enumerate(statuses):
        db.session.add(Attendance(
            student_id=student_id,
            section_id=section_id,
            date=base + timedelta(days=i),
            status=status,
        ))
    db.session.commit()


def make_announcement(db, created_by, status='published', title=None):
    uid = _uid()
    from datetime import datetime
    a = Announcement(
        title=title or f'Notice {uid}',
        content='Body',
        status=status,
        published_at=datetime.utcnow() if status == 'published' else None,
        created_by=created_by,
    )
    db.session.add(a)
    db.session.commit()
    return a


def make_overdue_fee(db, student_id):
    uid = _uid()
    c = Class(name=f'FeeCls {uid}', grade_level=1)
    db.session.add(c)
    db.session.commit()
    ay = AcademicYear(name=f'AY-{uid}', start_date=date(2024, 6, 1),
                      end_date=date(2025, 5, 31), is_current=True, is_active=True)
    db.session.add(ay)
    db.session.commit()
    fs = FeeStructure(class_id=c.id, academic_year_id=ay.id,
                      fee_type=f'Tuition {uid}', amount=5000.00,
                      is_recurring=False, frequency='one_time')
    db.session.add(fs)
    db.session.commit()
    fr = FeeRecord(student_id=student_id, fee_structure_id=fs.id,
                   amount=5000.00, discount=0, net_amount=5000.00,
                   due_date=date.today() - timedelta(days=3), status='pending')
    db.session.add(fr)
    db.session.commit()
    return fs, fr


# ---------------------------------------------------------------------------
# 1. Empty-state — all keys present, zeros / empty lists
# ---------------------------------------------------------------------------

class TestEmptyState:

    def test_returns_all_keys_with_zeros(self, client, admin_token):
        resp = client.get('/api/v1/dashboard/admin',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        data = body['data']

        for key in (
            'total_students', 'total_teachers', 'attendance_today',
            'fee_collection_this_month', 'pending_leave_applications',
            'recent_announcements', 'low_attendance_students',
            'fee_defaulters_count',
        ):
            assert key in data, f'missing key {key}'

        assert data['total_students'] == 0
        assert data['total_teachers'] == 0
        assert data['attendance_today']['percentage'] == 0.0
        assert data['attendance_today']['present'] == 0
        assert data['fee_collection_this_month'] == {'collected': 0.0, 'pending': 0.0}
        assert data['pending_leave_applications'] == 0
        assert data['recent_announcements'] == []
        assert data['low_attendance_students'] == []
        assert data['fee_defaulters_count'] == 0


# ---------------------------------------------------------------------------
# 2. Correct counts with seeded data
# ---------------------------------------------------------------------------

class TestSeededCounts:

    def test_student_teacher_counts_exclude_inactive(self, client, admin_token, db):
        make_student(db)
        make_student(db)
        make_student(db, is_active=False)  # inactive — excluded
        make_teacher(db)
        make_teacher(db, is_active=False)  # inactive — excluded

        resp = client.get('/api/v1/dashboard/admin',
                          headers={'Authorization': f'Bearer {admin_token}'})
        data = resp.get_json()['data']
        assert data['total_students'] == 2
        assert data['total_teachers'] == 1

    def test_attendance_today_percentage(self, client, admin_token, db, admin_user):
        _c, sec = make_section(db)
        s1 = make_student(db)
        s2 = make_student(db)
        s3 = make_student(db)
        today = date.today()
        db.session.add_all([
            Attendance(student_id=s1.id, section_id=sec.id, date=today, status='present'),
            Attendance(student_id=s2.id, section_id=sec.id, date=today, status='present'),
            Attendance(student_id=s3.id, section_id=sec.id, date=today, status='absent'),
        ])
        db.session.commit()

        resp = client.get('/api/v1/dashboard/admin',
                          headers={'Authorization': f'Bearer {admin_token}'})
        att = resp.get_json()['data']['attendance_today']
        assert att['present'] == 2
        assert att['absent'] == 1
        assert att['percentage'] == round((2 / 3) * 100, 2)

    def test_pending_leave_and_announcements_and_defaulters(
        self, client, admin_token, db, admin_user, parent_user
    ):
        parent = db.session.query(Parent).filter_by(user_id=parent_user.id).first()
        student = db.session.query(Student).filter_by(admission_no='ADM-TEST-001').first()

        # 2 pending + 1 approved leave
        db.session.add_all([
            LeaveApplication(student_id=student.id, parent_id=parent.id,
                             from_date=date.today(), to_date=date.today(),
                             reason='sick', status='pending'),
            LeaveApplication(student_id=student.id, parent_id=parent.id,
                             from_date=date.today(), to_date=date.today(),
                             reason='trip', status='pending'),
            LeaveApplication(student_id=student.id, parent_id=parent.id,
                             from_date=date.today(), to_date=date.today(),
                             reason='done', status='approved'),
        ])
        db.session.commit()

        make_announcement(db, admin_user.id, status='published')
        make_announcement(db, admin_user.id, status='draft')  # excluded

        make_overdue_fee(db, student.id)

        resp = client.get('/api/v1/dashboard/admin',
                          headers={'Authorization': f'Bearer {admin_token}'})
        data = resp.get_json()['data']
        assert data['pending_leave_applications'] == 2
        assert len(data['recent_announcements']) == 1
        assert data['recent_announcements'][0]['status'] == 'published'
        assert data['fee_defaulters_count'] == 1

    def test_recent_announcements_capped_at_five(self, client, admin_token, db, admin_user):
        for _ in range(7):
            make_announcement(db, admin_user.id, status='published')
        resp = client.get('/api/v1/dashboard/admin',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert len(resp.get_json()['data']['recent_announcements']) == 5

    def test_low_attendance_students_flagged(self, client, admin_token, db):
        _c, sec = make_section(db)
        low = make_student(db)
        high = make_student(db)
        # low: 1 present / 4 total = 25%
        add_attendance(db, low.id, sec.id, ['present', 'absent', 'absent', 'absent'])
        # high: 4 present / 4 = 100%
        add_attendance(db, high.id, sec.id, ['present', 'present', 'present', 'present'])

        resp = client.get('/api/v1/dashboard/admin',
                          headers={'Authorization': f'Bearer {admin_token}'})
        low_list = resp.get_json()['data']['low_attendance_students']
        ids = [e['student_id'] for e in low_list]
        assert low.id in ids
        assert high.id not in ids
        entry = next(e for e in low_list if e['student_id'] == low.id)
        assert entry['percentage'] == 25.0
        assert 'name' in entry


# ---------------------------------------------------------------------------
# 3. Admin-only access
# ---------------------------------------------------------------------------

class TestAdminOnly:

    def test_teacher_forbidden(self, client, teacher_token):
        resp = client.get('/api/v1/dashboard/admin',
                          headers={'Authorization': f'Bearer {teacher_token}'})
        assert resp.status_code == 403

    def test_parent_forbidden(self, client, parent_token):
        resp = client.get('/api/v1/dashboard/admin',
                          headers={'Authorization': f'Bearer {parent_token}'})
        assert resp.status_code == 403

    def test_unauthenticated_rejected(self, client):
        resp = client.get('/api/v1/dashboard/admin')
        assert resp.status_code == 401
