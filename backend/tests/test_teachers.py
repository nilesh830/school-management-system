"""
Sprint 3 — SMS-014 Teacher Registration & Profile
              SMS-015 Subject Assignment
              SMS-018 Teacher Document Upload
"""
import io
import pytest
from datetime import date
from app.models.user import User
from app.models.teacher import Teacher
from app.models.subject import Subject


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_teacher(db, user_id, employee_id='EMP001', first_name='Priya',
                 last_name='Sharma', joining_date=None):
    t = Teacher(
        user_id=user_id,
        employee_id=employee_id,
        first_name=first_name,
        last_name=last_name,
        joining_date=joining_date or date(2022, 6, 1),
    )
    db.session.add(t)
    db.session.commit()
    return t


def make_subject(db, code='MATH101', name='Mathematics', max_marks=100, pass_marks=35):
    s = Subject(code=code, name=name, max_marks=max_marks, pass_marks=pass_marks)
    db.session.add(s)
    db.session.commit()
    return s


# ---------------------------------------------------------------------------
# SMS-014 — Teacher CRUD
# ---------------------------------------------------------------------------

class TestTeacherCreate:

    def test_admin_creates_teacher(self, client, admin_token, teacher_user):
        resp = client.post('/api/v1/teachers', json={
            'employee_id': 'EMP001',
            'user_id': teacher_user.id,
            'first_name': 'Priya',
            'last_name': 'Sharma',
            'joining_date': '2022-06-01',
            'gender': 'Female',
            'qualification': 'M.Sc Physics',
            'specialization': 'Physics',
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['success'] is True
        assert data['data']['employee_id'] == 'EMP001'
        assert data['data']['full_name'] == 'Priya Sharma'

    def test_duplicate_employee_id_returns_409(self, client, admin_token, teacher_user):
        client.post('/api/v1/teachers', json={
            'employee_id': 'EMP001',
            'user_id': teacher_user.id,
            'first_name': 'Priya',
            'last_name': 'Sharma',
            'joining_date': '2022-06-01',
        }, headers={'Authorization': f'Bearer {admin_token}'})

        resp = client.post('/api/v1/teachers', json={
            'employee_id': 'EMP001',
            'user_id': teacher_user.id,
            'first_name': 'Other',
            'last_name': 'Teacher',
            'joining_date': '2023-01-01',
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 409

    def test_missing_employee_id_returns_400(self, client, admin_token, teacher_user):
        resp = client.post('/api/v1/teachers', json={
            'user_id': teacher_user.id,
            'first_name': 'X',
            'last_name': 'Y',
            'joining_date': '2022-01-01',
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 400

    def test_missing_joining_date_returns_400(self, client, admin_token, teacher_user):
        resp = client.post('/api/v1/teachers', json={
            'employee_id': 'EMP002',
            'user_id': teacher_user.id,
            'first_name': 'X',
            'last_name': 'Y',
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 400

    def test_teacher_cannot_create_teacher(self, client, teacher_token, teacher_user):
        resp = client.post('/api/v1/teachers', json={
            'employee_id': 'EMP003',
            'user_id': teacher_user.id,
            'first_name': 'X',
            'last_name': 'Y',
            'joining_date': '2022-01-01',
        }, headers={'Authorization': f'Bearer {teacher_token}'})
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, client, teacher_user):
        resp = client.post('/api/v1/teachers', json={
            'employee_id': 'EMP001',
            'user_id': teacher_user.id,
            'first_name': 'X',
            'last_name': 'Y',
            'joining_date': '2022-01-01',
        })
        assert resp.status_code == 401


class TestTeacherRead:

    def test_list_teachers(self, client, db, admin_token, teacher_user):
        make_teacher(db, teacher_user.id)
        resp = client.get('/api/v1/teachers', headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['meta']['total'] == 1
        assert len(data['teachers']) == 1

    def test_list_teachers_search(self, client, db, admin_token, teacher_user):
        u2 = User(email='another@test.sms', role='teacher', first_name='Rahul', last_name='Gupta')
        u2.set_password('x')
        db.session.add(u2)
        db.session.commit()
        make_teacher(db, teacher_user.id, 'EMP001', 'Priya', 'Sharma')
        make_teacher(db, u2.id, 'EMP002', 'Rahul', 'Gupta')

        resp = client.get('/api/v1/teachers?search=priya',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        assert resp.get_json()['data']['meta']['total'] == 1

    def test_get_teacher_by_id(self, client, db, admin_token, teacher_user):
        t = make_teacher(db, teacher_user.id)
        resp = client.get(f'/api/v1/teachers/{t.id}',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        assert resp.get_json()['data']['employee_id'] == 'EMP001'

    def test_get_nonexistent_teacher_404(self, client, admin_token):
        resp = client.get('/api/v1/teachers/9999',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 404

    def test_teacher_can_read_own_profile(self, client, db, teacher_token, teacher_user):
        t = make_teacher(db, teacher_user.id)
        resp = client.get(f'/api/v1/teachers/{t.id}',
                          headers={'Authorization': f'Bearer {teacher_token}'})
        assert resp.status_code == 200


class TestTeacherUpdate:

    def test_admin_updates_teacher(self, client, db, admin_token, teacher_user):
        t = make_teacher(db, teacher_user.id)
        resp = client.put(f'/api/v1/teachers/{t.id}', json={
            'specialization': 'Quantum Physics',
            'phone': '9876543210',
        }, headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        assert resp.get_json()['data']['specialization'] == 'Quantum Physics'

    def test_duplicate_employee_id_on_update_409(self, client, db, admin_token, teacher_user):
        u2 = User(email='t2@test.sms', role='teacher', first_name='A', last_name='B')
        u2.set_password('x')
        db.session.add(u2)
        db.session.commit()
        t1 = make_teacher(db, teacher_user.id, 'EMP001')
        t2 = make_teacher(db, u2.id, 'EMP002')

        resp = client.put(f'/api/v1/teachers/{t2.id}', json={'employee_id': 'EMP001'},
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 409


class TestTeacherDelete:

    def test_soft_delete_teacher(self, client, db, admin_token, teacher_user):
        t = make_teacher(db, teacher_user.id)
        resp = client.delete(f'/api/v1/teachers/{t.id}',
                             headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200

        # Verify no longer in list
        list_resp = client.get('/api/v1/teachers',
                               headers={'Authorization': f'Bearer {admin_token}'})
        assert list_resp.get_json()['data']['meta']['total'] == 0

    def test_delete_nonexistent_teacher_404(self, client, admin_token):
        resp = client.delete('/api/v1/teachers/9999',
                             headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# SMS-015 — Subject assignment
# ---------------------------------------------------------------------------

class TestSubjectAssignment:

    def test_assign_subject_to_teacher(self, client, db, admin_token, teacher_user):
        t = make_teacher(db, teacher_user.id)
        s = make_subject(db)
        resp = client.post(f'/api/v1/teachers/{t.id}/subjects', json={'subject_id': s.id},
                           headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 201

    def test_duplicate_assignment_409(self, client, db, admin_token, teacher_user):
        t = make_teacher(db, teacher_user.id)
        s = make_subject(db)
        client.post(f'/api/v1/teachers/{t.id}/subjects', json={'subject_id': s.id},
                    headers={'Authorization': f'Bearer {admin_token}'})
        resp = client.post(f'/api/v1/teachers/{t.id}/subjects', json={'subject_id': s.id},
                           headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 409

    def test_list_teacher_subjects(self, client, db, admin_token, teacher_user):
        t = make_teacher(db, teacher_user.id)
        s = make_subject(db)
        client.post(f'/api/v1/teachers/{t.id}/subjects', json={'subject_id': s.id},
                    headers={'Authorization': f'Bearer {admin_token}'})
        resp = client.get(f'/api/v1/teachers/{t.id}/subjects',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        assert len(resp.get_json()['data']['subjects']) == 1

    def test_unassign_subject(self, client, db, admin_token, teacher_user):
        t = make_teacher(db, teacher_user.id)
        s = make_subject(db)
        client.post(f'/api/v1/teachers/{t.id}/subjects', json={'subject_id': s.id},
                    headers={'Authorization': f'Bearer {admin_token}'})
        resp = client.delete(f'/api/v1/teachers/{t.id}/subjects/{s.id}',
                             headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200

        # Verify empty
        list_resp = client.get(f'/api/v1/teachers/{t.id}/subjects',
                               headers={'Authorization': f'Bearer {admin_token}'})
        assert len(list_resp.get_json()['data']['subjects']) == 0

    def test_missing_subject_id_returns_400(self, client, db, admin_token, teacher_user):
        t = make_teacher(db, teacher_user.id)
        resp = client.post(f'/api/v1/teachers/{t.id}/subjects', json={},
                           headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# SMS-018 — Document upload
# ---------------------------------------------------------------------------

class TestTeacherDocumentUpload:

    def test_upload_valid_document(self, client, db, admin_token, teacher_user):
        t = make_teacher(db, teacher_user.id)
        data = {
            'document_type': 'degree_certificate',
            'file': (io.BytesIO(b'fake pdf content'), 'degree.pdf'),
        }
        resp = client.post(
            f'/api/v1/teachers/{t.id}/documents',
            data=data,
            content_type='multipart/form-data',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 201
        doc = resp.get_json()['data']
        assert doc['document_type'] == 'degree_certificate'

    def test_list_documents(self, client, db, admin_token, teacher_user):
        t = make_teacher(db, teacher_user.id)
        client.post(
            f'/api/v1/teachers/{t.id}/documents',
            data={
                'document_type': 'id_proof',
                'file': (io.BytesIO(b'img'), 'id.jpg'),
            },
            content_type='multipart/form-data',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        resp = client.get(f'/api/v1/teachers/{t.id}/documents',
                          headers={'Authorization': f'Bearer {admin_token}'})
        assert resp.status_code == 200
        assert len(resp.get_json()['data']['documents']) == 1

    def test_upload_invalid_extension_400(self, client, db, admin_token, teacher_user):
        t = make_teacher(db, teacher_user.id)
        resp = client.post(
            f'/api/v1/teachers/{t.id}/documents',
            data={
                'document_type': 'degree',
                'file': (io.BytesIO(b'exe'), 'malware.exe'),
            },
            content_type='multipart/form-data',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 400

    def test_missing_document_type_400(self, client, db, admin_token, teacher_user):
        t = make_teacher(db, teacher_user.id)
        resp = client.post(
            f'/api/v1/teachers/{t.id}/documents',
            data={'file': (io.BytesIO(b'pdf'), 'file.pdf')},
            content_type='multipart/form-data',
            headers={'Authorization': f'Bearer {admin_token}'},
        )
        assert resp.status_code == 400
