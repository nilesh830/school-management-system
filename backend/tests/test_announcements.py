"""
Sprint 9 — Announcements & Targeted Notices
Covers:
  - SMS-051: create, publish, school-wide dispatch, class-targeted dispatch
  - SMS-052: get_for_user role/class filtering, archived exclusion (role_view)
  - SMS-045: parent notice board (/parent-portal/notices)
"""
from datetime import date

from app.models.user import User
from app.models.student import Student
from app.models.parent import Parent, student_parent
from app.models.class_ import Class
from app.models.section import Section
from app.models.student_section import StudentSection
from app.models.notification import Notification


_counter = 0


def _uid():
    global _counter
    _counter += 1
    return _counter


def _login(client, email, password):
    resp = client.post('/api/v1/auth/login', json={
        'email': email, 'password': password, 'school_slug': 'test'
    })
    return resp.get_json()['data']['access_token']


def _h(token):
    return {'Authorization': f'Bearer {token}'}


def make_class(db):
    uid = _uid()
    c = Class(name=f'AN-Grade-{uid}', grade_level=(uid % 12) + 1)
    db.session.add(c)
    db.session.commit()
    return c


def make_section(db, class_id):
    uid = _uid()
    s = Section(name=f'AN{uid}', class_id=class_id)
    db.session.add(s)
    db.session.commit()
    return s


def make_student(db, section_id=None):
    uid = _uid()
    u = User(email=f'an_stu_{uid}@test.sms', role='student',
             first_name=f'Stu{uid}', last_name='T')
    u.set_password('Student@123')
    db.session.add(u)
    db.session.flush()
    s = Student(user_id=u.id, admission_no=f'AN-ADM-{uid:05d}',
                first_name=f'Stu{uid}', last_name='T',
                date_of_birth=date(2012, 1, 1), gender='Male',
                admission_date=date(2024, 6, 1))
    db.session.add(s)
    db.session.commit()
    if section_id:
        db.session.add(StudentSection(
            student_id=s.id, section_id=section_id,
            academic_year='2024-2025', start_date=date(2024, 6, 1),
            is_current=True))
        db.session.commit()
    return u, s


def make_parent_for(db, student_id):
    uid = _uid()
    u = User(email=f'an_par_{uid}@test.sms', role='parent',
             first_name=f'Par{uid}', last_name='T')
    u.set_password('Parent@123')
    db.session.add(u)
    db.session.flush()
    p = Parent(user_id=u.id, first_name=f'Par{uid}', last_name='T',
               relationship_type='Father', phone_primary='+91-9000000000')
    db.session.add(p)
    db.session.flush()
    db.session.execute(student_parent.insert().values(
        student_id=student_id, parent_id=p.id, is_primary_contact=True))
    db.session.commit()
    return u, p


def _create(client, admin_token, **kwargs):
    body = {'title': kwargs.get('title', 'Notice'), 'content': kwargs.get('content', 'Body')}
    for k in ('target_roles', 'target_class_ids', 'publish_at', 'expires_at'):
        if k in kwargs:
            body[k] = kwargs[k]
    return client.post('/api/v1/announcements', json=body, headers=_h(admin_token))


# ===========================================================================
# SMS-051 — create & publish
# ===========================================================================

def test_create_announcement_as_admin(client, admin_token):
    resp = _create(client, admin_token, title='PTM', content='Meeting Friday')
    assert resp.status_code == 201
    data = resp.get_json()['data']
    assert data['status'] == 'draft'
    assert data['title'] == 'PTM'


def test_create_requires_admin(client, teacher_token):
    resp = _create(client, teacher_token)
    assert resp.status_code == 403


def test_create_validation_error(client, admin_token):
    resp = client.post('/api/v1/announcements', json={'title': ''},
                       headers=_h(admin_token))
    assert resp.status_code == 422


def test_publish_schoolwide_dispatch(client, db, admin_token):
    cls = make_class(db)
    section = make_section(db, cls.id)
    stu_user, student = make_student(db, section.id)
    par_user, _ = make_parent_for(db, student.id)

    # school-wide: no target_roles / target_class_ids
    cid = _create(client, admin_token).get_json()['data']['id']
    resp = client.post(f'/api/v1/announcements/{cid}/publish', headers=_h(admin_token))
    assert resp.status_code == 200
    assert resp.get_json()['data']['status'] == 'published'
    assert resp.get_json()['data']['notified_count'] >= 2

    # both the student and the parent should have an announcement notification
    for uid in (stu_user.id, par_user.id):
        n = db.session.query(Notification).filter_by(
            user_id=uid, type='announcement', reference_id=cid).first()
        assert n is not None


def test_publish_class_targeted_dispatch(client, db, admin_token):
    cls_a = make_class(db)
    sec_a = make_section(db, cls_a.id)
    _, stu_a = make_student(db, sec_a.id)
    par_a_user, _ = make_parent_for(db, stu_a.id)

    cls_b = make_class(db)
    sec_b = make_section(db, cls_b.id)
    _, stu_b = make_student(db, sec_b.id)
    par_b_user, _ = make_parent_for(db, stu_b.id)

    cid = _create(client, admin_token,
                  target_roles=['parent'],
                  target_class_ids=[cls_a.id]).get_json()['data']['id']
    client.post(f'/api/v1/announcements/{cid}/publish', headers=_h(admin_token))

    na = db.session.query(Notification).filter_by(
        user_id=par_a_user.id, reference_id=cid).first()
    nb = db.session.query(Notification).filter_by(
        user_id=par_b_user.id, reference_id=cid).first()
    assert na is not None        # parent of class A child notified
    assert nb is None            # parent of class B child NOT notified


def test_publish_twice_conflicts(client, admin_token):
    cid = _create(client, admin_token).get_json()['data']['id']
    client.post(f'/api/v1/announcements/{cid}/publish', headers=_h(admin_token))
    resp = client.post(f'/api/v1/announcements/{cid}/publish', headers=_h(admin_token))
    assert resp.status_code == 409


def test_admin_list_returns_all(client, admin_token):
    _create(client, admin_token, title='Draft one')
    resp = client.get('/api/v1/announcements', headers=_h(admin_token))
    assert resp.status_code == 200
    assert len(resp.get_json()['data']['announcements']) >= 1


# ===========================================================================
# SMS-052 — targeted role_view
# ===========================================================================

def test_role_view_role_filter(client, db, admin_token, parent_token):
    # targeted to teachers only -> parent must not see it
    cid_t = _create(client, admin_token, target_roles=['teacher']).get_json()['data']['id']
    client.post(f'/api/v1/announcements/{cid_t}/publish', headers=_h(admin_token))
    # targeted to parents -> parent sees it
    cid_p = _create(client, admin_token, target_roles=['parent']).get_json()['data']['id']
    client.post(f'/api/v1/announcements/{cid_p}/publish', headers=_h(admin_token))

    resp = client.get('/api/v1/announcements?role_view=true', headers=_h(parent_token))
    assert resp.status_code == 200
    ids = [a['id'] for a in resp.get_json()['data']['announcements']]
    assert cid_p in ids
    assert cid_t not in ids


def test_role_view_excludes_draft_and_archived(client, db, admin_token, parent_token):
    cid_draft = _create(client, admin_token, target_roles=['parent']).get_json()['data']['id']
    # leave as draft (do not publish)
    cid_arch = _create(client, admin_token, target_roles=['parent']).get_json()['data']['id']
    client.post(f'/api/v1/announcements/{cid_arch}/publish', headers=_h(admin_token))
    client.put(f'/api/v1/announcements/{cid_arch}', json={'status': 'archived'},
               headers=_h(admin_token))

    resp = client.get('/api/v1/announcements?role_view=true', headers=_h(parent_token))
    ids = [a['id'] for a in resp.get_json()['data']['announcements']]
    assert cid_draft not in ids
    assert cid_arch not in ids


# ===========================================================================
# SMS-045 — parent notice board
# ===========================================================================

def test_parent_notices_schoolwide(client, db, admin_token, parent_token):
    cid = _create(client, admin_token, title='Holiday').get_json()['data']['id']
    client.post(f'/api/v1/announcements/{cid}/publish', headers=_h(admin_token))

    resp = client.get('/api/v1/parent-portal/notices', headers=_h(parent_token))
    assert resp.status_code == 200
    ids = [n['id'] for n in resp.get_json()['data']['notices']]
    assert cid in ids


def test_parent_notices_class_targeting(client, db, admin_token):
    # Build a parent whose child is in class A
    cls_a = make_class(db)
    sec_a = make_section(db, cls_a.id)
    _, stu_a = make_student(db, sec_a.id)
    par_user, _ = make_parent_for(db, stu_a.id)
    token = _login(client, par_user.email, 'Parent@123')

    cls_b = make_class(db)

    cid_a = _create(client, admin_token, target_roles=['parent'],
                    target_class_ids=[cls_a.id]).get_json()['data']['id']
    client.post(f'/api/v1/announcements/{cid_a}/publish', headers=_h(admin_token))
    cid_b = _create(client, admin_token, target_roles=['parent'],
                    target_class_ids=[cls_b.id]).get_json()['data']['id']
    client.post(f'/api/v1/announcements/{cid_b}/publish', headers=_h(admin_token))

    resp = client.get('/api/v1/parent-portal/notices', headers=_h(token))
    ids = [n['id'] for n in resp.get_json()['data']['notices']]
    assert cid_a in ids
    assert cid_b not in ids


def test_parent_notices_empty(client, parent_token):
    resp = client.get('/api/v1/parent-portal/notices', headers=_h(parent_token))
    assert resp.status_code == 200
    assert resp.get_json()['data']['notices'] == []


def test_parent_notices_requires_parent(client, admin_token):
    resp = client.get('/api/v1/parent-portal/notices', headers=_h(admin_token))
    assert resp.status_code == 403
