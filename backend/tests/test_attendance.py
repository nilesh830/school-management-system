"""
Sprint 4 — SMS-024 Mark Daily Attendance
Tests: mark, duplicate guard, teacher auth, student view, report, today-summary
"""
import pytest
from datetime import date
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.section import Section
from app.models.class_ import Class
from app.models.student_section import StudentSection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_class(db, name='Grade 1', grade_level=1):
    c = Class(name=name, grade_level=grade_level)
    db.session.add(c)
    db.session.commit()
    return c


def make_teacher_record(db, user_id, employee_id='T001'):
    t = Teacher(
        user_id=user_id,
        employee_id=employee_id,
        first_name='Priya',
        last_name='Sharma',
        joining_date=date(2022, 6, 1),
    )
    db.session.add(t)
    db.session.commit()
    return t


def make_section(db, class_id, name='A', class_teacher_id=None):
    s = Section(name=name, class_id=class_id, class_teacher_id=class_teacher_id)
    db.session.add(s)
    db.session.commit()
    return s


def make_student(db, user_id, admission_no='ADM001'):
    s = Student(
        user_id=user_id,
        admission_no=admission_no,
        first_name='Alice',
        last_name='Test',
        date_of_birth=date(2012, 1, 1),
        gender='Female',
        admission_date=date(2024, 6, 1),
    )
    db.session.add(s)
    db.session.commit()
    return s


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


# ---------------------------------------------------------------------------
# TC-1: Admin marks attendance successfully
# ---------------------------------------------------------------------------

class TestMarkAttendance:

    def test_admin_marks_attendance(self, client, admin_token, db, student_user):
        cls = make_class(db)
        section = make_section(db, cls.id)
        student = make_student(db, student_user.id)
        enroll(db, student.id, section.id)

        resp = client.post('/api/v1/attendance/mark', json={
            'section_id': section.id,
            'date': '2026-06-10',
            'records': [{'student_id': student.id, 'status': 'present'}],
        }, headers={'Authorization': f'Bearer {admin_token}'})

        assert resp.status_code == 201
        data = resp.get_json()
        assert data['success'] is True
        assert data['data']['records_saved'] == 1

    # TC-2: Duplicate mark returns 409
    def test_duplicate_mark_returns_409(self, client, admin_token, db, student_user):
        cls = make_class(db, name='Grade 2', grade_level=2)
        section = make_section(db, cls.id, name='B')
        student = make_student(db, student_user.id, admission_no='ADM002')
        enroll(db, student.id, section.id)

        payload = {
            'section_id': section.id,
            'date': '2026-06-11',
            'records': [{'student_id': student.id, 'status': 'present'}],
        }
        client.post('/api/v1/attendance/mark', json=payload,
                    headers={'Authorization': f'Bearer {admin_token}'})
        resp = client.post('/api/v1/attendance/mark', json=payload,
                           headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 409

    # TC-3: Teacher can mark attendance for their own section
    def test_teacher_marks_own_section(self, client, teacher_token, teacher_user, db, student_user):
        cls = make_class(db, name='Grade 3', grade_level=3)
        teacher = make_teacher_record(db, teacher_user.id, employee_id='T003')
        section = make_section(db, cls.id, name='C', class_teacher_id=teacher.id)
        student = make_student(db, student_user.id, admission_no='ADM003')
        enroll(db, student.id, section.id)

        resp = client.post('/api/v1/attendance/mark', json={
            'section_id': section.id,
            'date': '2026-06-12',
            'records': [{'student_id': student.id, 'status': 'present'}],
        }, headers={'Authorization': f'Bearer {teacher_token}'})
        assert resp.status_code == 201

    # TC-4: Teacher cannot mark attendance for a section they don't teach
    def test_teacher_cannot_mark_other_section(self, client, teacher_token, teacher_user, db, student_user):
        cls = make_class(db, name='Grade 4', grade_level=4)
        teacher = make_teacher_record(db, teacher_user.id, employee_id='T004')
        # section has a different class teacher (None means no class teacher assigned)
        section = make_section(db, cls.id, name='D', class_teacher_id=None)
        student = make_student(db, student_user.id, admission_no='ADM004')
        enroll(db, student.id, section.id)

        resp = client.post('/api/v1/attendance/mark', json={
            'section_id': section.id,
            'date': '2026-06-13',
            'records': [{'student_id': student.id, 'status': 'present'}],
        }, headers={'Authorization': f'Bearer {teacher_token}'})
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# TC-5: Student views their own attendance
# ---------------------------------------------------------------------------

class TestGetAttendance:

    def test_student_views_own_attendance(self, client, db, student_user):
        from app import create_app
        from tests.conftest import _login

        cls = make_class(db, name='Grade 5', grade_level=5)
        section = make_section(db, cls.id, name='E')
        student = make_student(db, student_user.id, admission_no='ADM005')
        enroll(db, student.id, section.id)

        # Seed one attendance row directly
        from app.models.attendance import Attendance
        row = Attendance(
            student_id=student.id,
            section_id=section.id,
            date=date(2026, 6, 1),
            status='present',
        )
        db.session.add(row)
        db.session.commit()

        token = _login(client, 'alice@test.sms', 'Student@123')['access_token']
        resp = client.get(
            f'/api/v1/attendance?student_id={student.id}&month=6&year=2026',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body['data']['attendance']) == 1
        assert body['data']['attendance'][0]['status'] == 'present'


# ---------------------------------------------------------------------------
# TC-6: Admin gets attendance report for a section
# ---------------------------------------------------------------------------

class TestAttendanceReport:

    def test_admin_gets_report(self, client, admin_token, db, student_user):
        cls = make_class(db, name='Grade 6', grade_level=6)
        section = make_section(db, cls.id, name='F')
        student = make_student(db, student_user.id, admission_no='ADM006')
        enroll(db, student.id, section.id)

        from app.models.attendance import Attendance
        for day in [1, 2, 3]:
            db.session.add(Attendance(
                student_id=student.id,
                section_id=section.id,
                date=date(2026, 6, day),
                status='present' if day != 2 else 'absent',
            ))
        db.session.commit()

        resp = client.get(
            f'/api/v1/attendance/report?section_id={section.id}&from_date=2026-06-01&to_date=2026-06-30',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['data']['total_records'] == 3
        summaries = body['data']['student_summaries']
        assert len(summaries) == 1
        assert summaries[0]['present'] == 2
        assert summaries[0]['absent'] == 1


# ---------------------------------------------------------------------------
# TC-7: Admin gets today summary
# ---------------------------------------------------------------------------

class TestTodaySummary:

    def test_admin_gets_today_summary(self, client, admin_token, db, student_user):
        cls = make_class(db, name='Grade 7', grade_level=7)
        section = make_section(db, cls.id, name='G')
        student = make_student(db, student_user.id, admission_no='ADM007')
        enroll(db, student.id, section.id)

        from app.models.attendance import Attendance
        db.session.add(Attendance(
            student_id=student.id,
            section_id=section.id,
            date=date.today(),
            status='present',
        ))
        db.session.commit()

        resp = client.get('/api/v1/attendance/today-summary',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['data']['total'] >= 1
        assert body['data']['present'] >= 1


# ---------------------------------------------------------------------------
# TC-8–12: Attendance Report endpoint — date/section filtering, edge cases,
#           auth/authorisation guards
# ---------------------------------------------------------------------------

class TestAttendanceReportEndpoint:

    # TC-8: Date range filters correctly — rows outside the range are excluded
    def test_date_range_filters_correctly(self, client, admin_token, db, student_user):
        from app.models.attendance import Attendance

        cls = make_class(db, name='Grade 8', grade_level=8)
        section = make_section(db, cls.id, name='H')
        student = make_student(db, student_user.id, admission_no='RPT001')
        enroll(db, student.id, section.id)

        # 2 rows in June, 1 row in July — only the June rows should be counted
        for d in [date(2026, 6, 1), date(2026, 6, 15)]:
            db.session.add(Attendance(
                student_id=student.id,
                section_id=section.id,
                date=d,
                status='present',
            ))
        db.session.add(Attendance(
            student_id=student.id,
            section_id=section.id,
            date=date(2026, 7, 1),
            status='present',
        ))
        db.session.commit()

        resp = client.get(
            f'/api/v1/attendance/report'
            f'?section_id={section.id}&from_date=2026-06-01&to_date=2026-06-30',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['data']['total_records'] == 2

    # TC-9: Section filter isolates sections — query one section, get only its records
    def test_section_filter_isolates_sections(self, client, admin_token, db, student_user):
        from app.models.attendance import Attendance
        from app.models.user import User

        cls = make_class(db, name='Grade 9', grade_level=9)
        section_a = make_section(db, cls.id, name='IA')
        section_b = make_section(db, cls.id, name='IB')

        # Student 1 in section_a
        student_a = make_student(db, student_user.id, admission_no='RPT002')
        enroll(db, student_a.id, section_a.id)

        # Student 2 in section_b — needs its own User row
        user_b = User(
            email='bob.rpt@test.sms',
            role='student',
            first_name='Bob',
            last_name='Rpt',
        )
        user_b.set_password('Student@123')
        db.session.add(user_b)
        db.session.commit()
        student_b = make_student(db, user_b.id, admission_no='RPT003')
        enroll(db, student_b.id, section_b.id)

        target_date = date(2026, 6, 5)
        db.session.add(Attendance(
            student_id=student_a.id,
            section_id=section_a.id,
            date=target_date,
            status='present',
        ))
        db.session.add(Attendance(
            student_id=student_b.id,
            section_id=section_b.id,
            date=target_date,
            status='absent',
        ))
        db.session.commit()

        resp = client.get(
            f'/api/v1/attendance/report'
            f'?section_id={section_a.id}&from_date=2026-06-01&to_date=2026-06-30',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        summaries = body['data']['student_summaries']
        # Only student_a should appear; student_b is in a different section
        student_ids_in_response = [s['student_id'] for s in summaries]
        assert student_a.id in student_ids_in_response
        assert student_b.id not in student_ids_in_response

    # TC-10: Empty date range — no rows match, totals are zero
    def test_empty_date_range_returns_zero(self, client, admin_token, db, student_user):
        from app.models.attendance import Attendance

        cls = make_class(db, name='Grade 10', grade_level=10)
        section = make_section(db, cls.id, name='J')
        student = make_student(db, student_user.id, admission_no='RPT004')
        enroll(db, student.id, section.id)

        # Seed rows in June — querying July should return nothing
        db.session.add(Attendance(
            student_id=student.id,
            section_id=section.id,
            date=date(2026, 6, 10),
            status='present',
        ))
        db.session.commit()

        resp = client.get(
            f'/api/v1/attendance/report'
            f'?section_id={section.id}&from_date=2026-07-01&to_date=2026-07-31',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['data']['total_records'] == 0
        assert body['data']['student_summaries'] == []

    # TC-11: Missing query params return 400
    def test_missing_params_returns_400(self, client, admin_token, db):
        cls = make_class(db, name='Grade 11', grade_level=11)
        section = make_section(db, cls.id, name='K')

        # Provide only section_id — omit both date params
        resp = client.get(
            f'/api/v1/attendance/report?section_id={section.id}',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 400

    # TC-12: Student role is forbidden from the report endpoint
    def test_student_role_forbidden(self, client, db, student_user):
        from tests.conftest import _login

        cls = make_class(db, name='Grade 12', grade_level=12)
        section = make_section(db, cls.id, name='L')

        token = _login(client, 'alice@test.sms', 'Student@123')['access_token']
        resp = client.get(
            f'/api/v1/attendance/report'
            f'?section_id={section.id}&from_date=2026-06-01&to_date=2026-06-30',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# TC-13: GET /api/v1/attendance/today-summary returns 401 when unauthenticated
# ---------------------------------------------------------------------------

class TestTodaySummaryAuth:

    def test_today_summary_unauthenticated_returns_401(self, client):
        resp = client.get('/api/v1/attendance/today-summary')
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# TC-14: Mark attendance with an invalid status value returns 422
# ---------------------------------------------------------------------------

class TestMarkAttendanceValidation:

    def test_invalid_status_returns_422(self, client, admin_token, db, student_user):
        cls = make_class(db, name='Grade 13', grade_level=1)
        section = make_section(db, cls.id, name='M')
        student = make_student(db, student_user.id, admission_no='ADM013')
        enroll(db, student.id, section.id)

        resp = client.post('/api/v1/attendance/mark', json={
            'section_id': section.id,
            'date': '2026-06-14',
            'records': [{'student_id': student.id, 'status': 'unknown'}],
        }, headers={'Authorization': f'Bearer {admin_token}'})

        assert resp.status_code == 422
        body = resp.get_json()
        # Marshmallow validation error — success must be False
        assert body['success'] is False

    # TC-15: Empty records list is rejected by the schema (min=1)
    def test_empty_records_rejected_by_schema(self, client, admin_token, db):
        cls = make_class(db, name='Grade 14', grade_level=2)
        section = make_section(db, cls.id, name='N')

        # Marshmallow AttendanceMarkSchema enforces records Length(min=1),
        # so an empty array is a validation error, not a service-layer result.
        resp = client.post('/api/v1/attendance/mark', json={
            'section_id': section.id,
            'date': '2026-06-15',
            'records': [],
        }, headers={'Authorization': f'Bearer {admin_token}'})

        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# TC-16: Teacher without a section assignment cannot mark any attendance (403)
# ---------------------------------------------------------------------------

class TestTeacherWithoutSection:

    def test_teacher_with_no_section_gets_403(self, client, teacher_token, teacher_user, db, student_user):
        cls = make_class(db, name='Grade 15', grade_level=3)
        # Section has NO class teacher assigned
        section = make_section(db, cls.id, name='O', class_teacher_id=None)
        student = make_student(db, student_user.id, admission_no='ADM015')
        enroll(db, student.id, section.id)

        # teacher_user has NO Teacher profile row — the route checks for one
        # and returns 403 when it cannot be found
        resp = client.post('/api/v1/attendance/mark', json={
            'section_id': section.id,
            'date': '2026-06-16',
            'records': [{'student_id': student.id, 'status': 'present'}],
        }, headers={'Authorization': f'Bearer {teacher_token}'})

        assert resp.status_code == 403
        body = resp.get_json()
        assert body['success'] is False


# ---------------------------------------------------------------------------
# TC-17: GET /api/v1/attendance without student_id param returns 400
# ---------------------------------------------------------------------------

class TestGetAttendanceMissingParams:

    def test_missing_student_id_returns_400(self, client, admin_token):
        # Provide month and year but omit student_id entirely
        resp = client.get(
            '/api/v1/attendance?month=6&year=2026',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert body['success'] is False
        assert 'student_id' in body['message']

    def test_missing_month_returns_400(self, client, admin_token):
        # Provide student_id and year but omit month
        resp = client.get(
            '/api/v1/attendance?student_id=1&year=2026',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 400

    def test_missing_year_returns_400(self, client, admin_token):
        # Provide student_id and month but omit year
        resp = client.get(
            '/api/v1/attendance?student_id=1&month=6',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# TC-18: Attendance percentage calculation — seeded data matches summary counts
# ---------------------------------------------------------------------------

class TestAttendancePercentageCalculation:

    def test_summary_counts_match_seeded_data(self, client, admin_token, db, student_user):
        """
        Seed 8 present + 2 absent rows for one student.
        Query the report endpoint and assert per-student summary counts are exact.
        The report endpoint returns student_summaries with per-status counts;
        no percentage field is computed server-side, so we assert counts only.
        """
        from app.models.attendance import Attendance

        cls = make_class(db, name='Grade 16', grade_level=5)
        section = make_section(db, cls.id, name='P')
        student = make_student(db, student_user.id, admission_no='ADM018')
        enroll(db, student.id, section.id)

        # 8 present rows on days 1–8, 2 absent rows on days 9–10
        for day in range(1, 9):
            db.session.add(Attendance(
                student_id=student.id,
                section_id=section.id,
                date=date(2026, 5, day),
                status='present',
            ))
        for day in range(9, 11):
            db.session.add(Attendance(
                student_id=student.id,
                section_id=section.id,
                date=date(2026, 5, day),
                status='absent',
            ))
        db.session.commit()

        resp = client.get(
            f'/api/v1/attendance/report'
            f'?section_id={section.id}&from_date=2026-05-01&to_date=2026-05-31',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['data']['total_records'] == 10

        summaries = body['data']['student_summaries']
        assert len(summaries) == 1
        summary = summaries[0]
        assert summary['student_id'] == student.id
        assert summary['present'] == 8
        assert summary['absent'] == 2
        assert summary['late'] == 0
        assert summary['leave'] == 0

        # Verify the percentage that the frontend calendar would compute:
        # attended = present + late = 8 + 0 = 8
        # total    = present + absent + late + leave = 8 + 2 + 0 + 0 = 10
        # expected = round(8 / 10 * 100) = 80
        attended = summary['present'] + summary['late']
        total = summary['present'] + summary['absent'] + summary['late'] + summary['leave']
        computed_pct = round((attended / total) * 100)
        assert computed_pct == 80
