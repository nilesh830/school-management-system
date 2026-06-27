"""
Sprint 8 — Parent-Teacher Messaging Tests (SMS-048)
"""
import pytest
from datetime import date

from app.models.user import User
from app.models.student import Student
from app.models.parent import Parent, student_parent
from app.models.section import Section
from app.models.class_ import Class
from app.models.student_section import StudentSection
from app.models.teacher import Teacher
from app.models.academic_year import AcademicYear


_counter = 0

def _uid():
    global _counter
    _counter += 1
    return _counter


def make_class(db):
    uid = _uid()
    c = Class(name=f'MSG-Grade-{uid}', grade_level=(uid % 12) + 1)
    db.session.add(c)
    db.session.commit()
    return c


def make_student_user(db):
    uid = _uid()
    u = User(email=f'msg_student_{uid}@test.sms', role='student',
             first_name=f'MSGStudent{uid}', last_name='Test')
    u.set_password('Student@123')
    db.session.add(u)
    db.session.flush()
    s = Student(
        user_id=u.id,
        admission_no=f'MSG-ADM-{uid:05d}',
        first_name=f'MSGStudent{uid}',
        last_name='Test',
        date_of_birth=date(2012, 1, 1),
        gender='Male',
        admission_date=date(2024, 6, 1),
    )
    db.session.add(s)
    db.session.commit()
    return u, s


def make_parent_user(db):
    uid = _uid()
    u = User(email=f'msg_parent_{uid}@test.sms', role='parent',
             first_name=f'MSGParent{uid}', last_name='Test')
    u.set_password('Parent@123')
    db.session.add(u)
    db.session.flush()
    p = Parent(
        user_id=u.id,
        first_name=f'MSGParent{uid}',
        last_name='Test',
        relationship_type='Mother',
        phone_primary='+91-9111111111',
    )
    db.session.add(p)
    db.session.commit()
    return u, p


def make_teacher_user(db):
    uid = _uid()
    u = User(email=f'msg_teacher_{uid}@test.sms', role='teacher',
             first_name=f'MSGTeacher{uid}', last_name='Test')
    u.set_password('Teacher@123')
    db.session.add(u)
    db.session.flush()
    t = Teacher(
        user_id=u.id,
        employee_id=f'EMP-MSG-{uid:04d}',
        first_name=f'MSGTeacher{uid}',
        last_name='Test',
        joining_date=date(2022, 6, 1),
    )
    db.session.add(t)
    db.session.commit()
    return u, t


def link_parent_student(db, parent_id, student_id):
    db.session.execute(
        student_parent.insert().values(
            parent_id=parent_id,
            student_id=student_id,
            is_primary_contact=True,
        )
    )
    db.session.commit()


def _login(client, email, password):
    resp = client.post('/api/v1/auth/login', json={
        'email': email, 'password': password, 'school_slug': 'test'
    })
    return resp.get_json()['data']


def _h(token):
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def msg_setup(db, client):
    """
    Creates: parent + student + teacher, student enrolled in section with teacher as class_teacher.
    """
    parent_user, parent = make_parent_user(db)
    _, student = make_student_user(db)
    link_parent_student(db, parent.id, student.id)

    teacher_user, teacher = make_teacher_user(db)

    cls = make_class(db)
    # Create section with class_teacher_id set
    uid = _uid()
    section = Section(name=f'M{uid}', class_id=cls.id, class_teacher_id=teacher.id)
    db.session.add(section)
    db.session.commit()

    # Enroll student in section
    ss = StudentSection(
        student_id=student.id,
        section_id=section.id,
        academic_year='2024-2025',
        start_date=date(2024, 6, 1),
        is_current=True,
    )
    db.session.add(ss)
    db.session.commit()

    parent_token = _login(client, parent_user.email, 'Parent@123')['access_token']
    teacher_token = _login(client, teacher_user.email, 'Teacher@123')['access_token']

    return {
        'parent_user': parent_user,
        'parent': parent,
        'student': student,
        'teacher_user': teacher_user,
        'teacher': teacher,
        'section': section,
        'parent_token': parent_token,
        'teacher_token': teacher_token,
    }


class TestMessages:

    def test_parent_creates_thread_returns_201(self, client, msg_setup):
        """T-048-1: Parent creates a message thread successfully."""
        resp = client.post('/api/v1/parent-portal/messages/threads', json={
            'student_id': msg_setup['student'].id,
            'subject': 'Homework query',
            'message': 'Hello teacher, I have a question about homework.',
        }, headers=_h(msg_setup['parent_token']))
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['success'] is True
        assert data['data']['subject'] == 'Homework query'
        assert 'messages' in data['data']
        assert len(data['data']['messages']) == 1

    def test_parent_sends_reply_returns_201(self, client, msg_setup):
        """T-048-2: Parent sends a reply to an existing thread."""
        # Create thread first
        create_resp = client.post('/api/v1/parent-portal/messages/threads', json={
            'student_id': msg_setup['student'].id,
            'subject': 'Reply test',
            'message': 'First message',
        }, headers=_h(msg_setup['parent_token']))
        assert create_resp.status_code == 201
        thread_id = create_resp.get_json()['data']['id']

        # Reply as teacher
        reply_resp = client.post(
            f'/api/v1/parent-portal/messages/threads/{thread_id}/reply',
            json={'message': 'Teacher reply here'},
            headers=_h(msg_setup['teacher_token']),
        )
        assert reply_resp.status_code == 201
        data = reply_resp.get_json()
        assert data['success'] is True
        assert data['data']['body'] == 'Teacher reply here'

    def test_teacher_sees_thread_returns_200(self, client, msg_setup):
        """T-048-3: Teacher can retrieve their thread."""
        create_resp = client.post('/api/v1/parent-portal/messages/threads', json={
            'student_id': msg_setup['student'].id,
            'subject': 'Teacher view test',
            'message': 'Can you see this?',
        }, headers=_h(msg_setup['parent_token']))
        assert create_resp.status_code == 201
        thread_id = create_resp.get_json()['data']['id']

        resp = client.get(
            f'/api/v1/parent-portal/messages/threads/{thread_id}',
            headers=_h(msg_setup['teacher_token']),
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['data']['id'] == thread_id

    def test_other_teacher_cannot_see_thread(self, client, db, msg_setup):
        """T-048-4: Teacher not in thread gets 404."""
        # Create thread
        create_resp = client.post('/api/v1/parent-portal/messages/threads', json={
            'student_id': msg_setup['student'].id,
            'subject': 'Private thread',
            'message': 'Secret message',
        }, headers=_h(msg_setup['parent_token']))
        assert create_resp.status_code == 201
        thread_id = create_resp.get_json()['data']['id']

        # Another teacher
        other_teacher_user, _ = make_teacher_user(db)
        other_token = _login(client, other_teacher_user.email, 'Teacher@123')['access_token']

        resp = client.get(
            f'/api/v1/parent-portal/messages/threads/{thread_id}',
            headers=_h(other_token),
        )
        assert resp.status_code == 404

    def test_mark_thread_read_returns_200(self, client, msg_setup):
        """T-048-5: Mark thread as read returns 200."""
        create_resp = client.post('/api/v1/parent-portal/messages/threads', json={
            'student_id': msg_setup['student'].id,
            'subject': 'Read test',
            'message': 'Please mark me as read',
        }, headers=_h(msg_setup['parent_token']))
        assert create_resp.status_code == 201
        thread_id = create_resp.get_json()['data']['id']

        resp = client.put(
            f'/api/v1/parent-portal/messages/threads/{thread_id}/read',
            headers=_h(msg_setup['teacher_token']),
        )
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True
