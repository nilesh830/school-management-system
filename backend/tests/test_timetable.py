"""
Sprint 3 — SMS-022 Timetable Creation
"""
import pytest
from datetime import date
from app.models.academic_year import AcademicYear
from app.models.class_ import Class
from app.models.section import Section
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.user import User
from app.models.timetable import Timetable


def make_section(db):
    c = Class(name='Grade 10', grade_level=10)
    db.session.add(c)
    db.session.flush()
    sec = Section(name='A', class_id=c.id, capacity=40)
    db.session.add(sec)
    db.session.commit()
    return sec


def make_subject(db, code='MATH101'):
    s = Subject(code=code, name='Mathematics', max_marks=100, pass_marks=35)
    db.session.add(s)
    db.session.commit()
    return s


def make_teacher(db, employee_id='EMP_TT', email='ttest@test.sms'):
    u = User(email=email, role='teacher', first_name='T', last_name='Teacher')
    u.set_password('x')
    db.session.add(u)
    db.session.flush()
    t = Teacher(user_id=u.id, employee_id=employee_id,
                first_name='T', last_name='Teacher', joining_date=date(2022, 1, 1))
    db.session.add(t)
    db.session.commit()
    return t


class TestTimetableCreate:

    def test_create_timetable_entry(self, client, db, admin_token):
        sec = make_section(db)
        subj = make_subject(db)
        teacher = make_teacher(db)

        resp = client.post('/api/v1/timetables', json={
            'section_id': sec.id,
            'subject_id': subj.id,
            'teacher_id': teacher.id,
            'day_of_week': 0,
            'period_no': 1,
            'start_time': '08:00',
            'end_time': '08:45',
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 201
        data = resp.get_json()['data']
        assert data['day_of_week'] == 0
        assert data['period_no'] == 1

    def test_teacher_double_booking_returns_409(self, client, db, admin_token):
        sec = make_section(db)
        c2 = Class(name='Grade 9', grade_level=9)
        db.session.add(c2)
        db.session.flush()
        sec2 = Section(name='A', class_id=c2.id, capacity=40)
        db.session.add(sec2)
        db.session.commit()

        subj = make_subject(db)
        teacher = make_teacher(db)

        client.post('/api/v1/timetables', json={
            'section_id': sec.id,
            'subject_id': subj.id,
            'teacher_id': teacher.id,
            'day_of_week': 1,
            'period_no': 2,
            'start_time': '09:00',
            'end_time': '09:45',
        }, headers={'Authorization': f'Bearer {admin_token}'})

        resp = client.post('/api/v1/timetables', json={
            'section_id': sec2.id,
            'subject_id': subj.id,
            'teacher_id': teacher.id,
            'day_of_week': 1,
            'period_no': 2,
            'start_time': '09:00',
            'end_time': '09:45',
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 409

    def test_section_slot_conflict_returns_409(self, client, db, admin_token):
        sec = make_section(db)
        subj1 = make_subject(db, 'MATH101')
        subj2 = make_subject(db, 'SCI201')
        teacher = make_teacher(db)

        u2 = User(email='t2@test.sms', role='teacher', first_name='B', last_name='T')
        u2.set_password('x')
        db.session.add(u2)
        db.session.flush()
        t2 = Teacher(user_id=u2.id, employee_id='EMP_T2',
                     first_name='B', last_name='T', joining_date=date(2022, 1, 1))
        db.session.add(t2)
        db.session.commit()

        client.post('/api/v1/timetables', json={
            'section_id': sec.id,
            'subject_id': subj1.id,
            'teacher_id': teacher.id,
            'day_of_week': 2,
            'period_no': 3,
            'start_time': '10:00',
            'end_time': '10:45',
        }, headers={'Authorization': f'Bearer {admin_token}'})

        resp = client.post('/api/v1/timetables', json={
            'section_id': sec.id,
            'subject_id': subj2.id,
            'teacher_id': t2.id,
            'day_of_week': 2,
            'period_no': 3,
            'start_time': '10:00',
            'end_time': '10:45',
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 409

    def test_missing_required_field_400(self, client, db, admin_token):
        sec = make_section(db)
        resp = client.post('/api/v1/timetables', json={'section_id': sec.id},
                           headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 400

    def test_teacher_cannot_create_timetable(self, client, teacher_token):
        resp = client.post('/api/v1/timetables', json={
            'section_id': 1, 'subject_id': 1, 'teacher_id': 1,
            'day_of_week': 0, 'period_no': 1,
            'start_time': '08:00', 'end_time': '08:45',
        }, headers={'Authorization': f'Bearer {teacher_token}'})
        assert resp.status_code == 403


class TestTimetableRead:

    def test_get_timetable_by_section(self, client, db, admin_token):
        sec = make_section(db)
        subj = make_subject(db)
        teacher = make_teacher(db)

        client.post('/api/v1/timetables', json={
            'section_id': sec.id,
            'subject_id': subj.id,
            'teacher_id': teacher.id,
            'day_of_week': 0,
            'period_no': 1,
            'start_time': '08:00',
            'end_time': '08:45',
        }, headers={'Authorization': f'Bearer {admin_token}'})

        resp = client.get(f'/api/v1/timetables?section_id={sec.id}',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        assert len(resp.get_json()['data']['timetable']) == 1

    def test_get_timetable_by_teacher(self, client, db, admin_token):
        sec = make_section(db)
        subj = make_subject(db)
        teacher = make_teacher(db)

        client.post('/api/v1/timetables', json={
            'section_id': sec.id,
            'subject_id': subj.id,
            'teacher_id': teacher.id,
            'day_of_week': 3,
            'period_no': 2,
            'start_time': '09:00',
            'end_time': '09:45',
        }, headers={'Authorization': f'Bearer {admin_token}'})

        resp = client.get(f'/api/v1/timetables?teacher_id={teacher.id}',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        assert len(resp.get_json()['data']['timetable']) == 1


class TestTimetableDelete:

    def test_admin_deletes_timetable_entry(self, client, db, admin_token):
        sec = make_section(db)
        subj = make_subject(db)
        teacher = make_teacher(db)

        create_resp = client.post('/api/v1/timetables', json={
            'section_id': sec.id,
            'subject_id': subj.id,
            'teacher_id': teacher.id,
            'day_of_week': 0,
            'period_no': 1,
            'start_time': '08:00',
            'end_time': '08:45',
        }, headers={'Authorization': f'Bearer {admin_token}'})
        entry_id = create_resp.get_json()['data']['id']

        resp = client.delete(f'/api/v1/timetables/{entry_id}',
                             headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
