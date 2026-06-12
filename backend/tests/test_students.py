"""
Sprint 2 — Student Management API tests.

Covers:
  SMS-007  enrollment (201, 409 duplicate, 422 missing field)
  SMS-008  list with search, pagination, role guard
  SMS-009  profile GET, PUT (admin + student self-service)
  SMS-010  parent link / unlink / list
  SMS-011  transfer
  SMS-012  document upload / list / delete
  SMS-013  soft delete, status PATCH
"""

import io
from datetime import date, timedelta

import pytest
from app import db as _db
from app.models.student import Student
from app.models.student_section import StudentSection
from app.models.parent import Parent, student_parent
from app.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def auth(token):
    return {'Authorization': f'Bearer {token}'}


VALID_STUDENT = {
    'first_name': 'Ravi',
    'last_name': 'Kumar',
    'date_of_birth': '2010-05-20',
    'gender': 'Male',
    'admission_date': '2024-06-01',
    'admission_no': 'ADM-2024-001',
}


# ---------------------------------------------------------------------------
# Additional fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def student_token(client, student_user):
    resp = client.post('/api/v1/auth/login',
                       json={'email': 'alice@test.sms', 'password': 'Student@123',
                             'school_slug': 'test'})
    return resp.get_json()['data']['access_token']


@pytest.fixture
def enrolled_student(db, admin_user):
    """A student record in the DB, owned by admin_user's user id (simplest setup)."""
    s = Student(
        user_id=admin_user.id,
        admission_no='ADM-EXIST-001',
        first_name='Priya',
        last_name='Patel',
        date_of_birth=date(2011, 8, 10),
        gender='Female',
        admission_date=date(2023, 6, 1),
    )
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture
def linked_parent(db, enrolled_student):
    """A Parent record linked to enrolled_student."""
    u = User(email='linked_parent@test.sms', role='parent',
             first_name='Suresh', last_name='Patel')
    u.set_password('Parent@123')
    db.session.add(u)
    db.session.flush()

    p = Parent(
        user_id=u.id,
        first_name='Suresh',
        last_name='Patel',
        relationship_type='Father',
        phone_primary='+91-9000000001',
    )
    db.session.add(p)
    db.session.flush()

    db.session.execute(
        student_parent.insert().values(
            student_id=enrolled_student.id,
            parent_id=p.id,
            is_primary_contact=True,
        )
    )
    db.session.commit()
    return p


@pytest.fixture
def unlinked_parent(db):
    """A Parent record NOT linked to any student."""
    u = User(email='unlinked_parent@test.sms', role='parent',
             first_name='Meena', last_name='Shah')
    u.set_password('Parent@123')
    db.session.add(u)
    db.session.flush()

    p = Parent(
        user_id=u.id,
        first_name='Meena',
        last_name='Shah',
        relationship_type='Mother',
        phone_primary='+91-9000000002',
    )
    db.session.add(p)
    db.session.commit()
    return p


# ---------------------------------------------------------------------------
# SMS-007 — Enrollment
# ---------------------------------------------------------------------------

class TestStudentEnrollment:

    def test_create_student_success(self, client, admin_token):
        resp = client.post('/api/v1/students', json=VALID_STUDENT,
                           headers=auth(admin_token))
        assert resp.status_code == 201
        body = resp.get_json()
        assert body['success'] is True
        assert body['data']['admission_no'] == 'ADM-2024-001'
        assert body['data']['first_name'] == 'Ravi'

    def test_create_student_with_optional_fields(self, client, admin_token):
        payload = {**VALID_STUDENT, 'blood_group': 'B+', 'phone': '9876543210',
                   'address': '123 Main St'}
        resp = client.post('/api/v1/students', json=payload,
                           headers=auth(admin_token))
        assert resp.status_code == 201
        data = resp.get_json()['data']
        assert data['blood_group'] == 'B+'
        assert data['phone'] == '9876543210'

    def test_create_student_duplicate_admission_no(self, client, admin_token, enrolled_student):
        payload = {**VALID_STUDENT, 'admission_no': enrolled_student.admission_no}
        resp = client.post('/api/v1/students', json=payload,
                           headers=auth(admin_token))
        assert resp.status_code == 409
        assert resp.get_json()['success'] is False

    def test_create_student_missing_required_field(self, client, admin_token):
        payload = {k: v for k, v in VALID_STUDENT.items() if k != 'first_name'}
        resp = client.post('/api/v1/students', json=payload,
                           headers=auth(admin_token))
        assert resp.status_code == 422
        errors = resp.get_json()['errors']
        assert 'first_name' in errors

    def test_create_student_invalid_gender(self, client, admin_token):
        payload = {**VALID_STUDENT, 'gender': 'Robot', 'admission_no': 'ADM-BAD-001'}
        resp = client.post('/api/v1/students', json=payload,
                           headers=auth(admin_token))
        assert resp.status_code == 422

    def test_create_student_future_dob(self, client, admin_token):
        future = (date.today() + timedelta(days=10)).isoformat()
        payload = {**VALID_STUDENT, 'date_of_birth': future, 'admission_no': 'ADM-BAD-002'}
        resp = client.post('/api/v1/students', json=payload,
                           headers=auth(admin_token))
        assert resp.status_code == 422

    def test_create_student_forbidden_for_teacher(self, client, teacher_token):
        resp = client.post('/api/v1/students', json=VALID_STUDENT,
                           headers=auth(teacher_token))
        assert resp.status_code == 403

    def test_create_student_unauthorized(self, client):
        resp = client.post('/api/v1/students', json=VALID_STUDENT)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# SMS-008 — Student list
# ---------------------------------------------------------------------------

class TestStudentList:

    def test_list_students_admin(self, client, admin_token, enrolled_student):
        resp = client.get('/api/v1/students', headers=auth(admin_token))
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        assert 'students' in body['data']
        assert 'meta' in body['data']

    def test_list_students_teacher(self, client, teacher_token, enrolled_student):
        resp = client.get('/api/v1/students', headers=auth(teacher_token))
        assert resp.status_code == 200

    def test_list_students_forbidden_for_student_role(self, client, student_token):
        resp = client.get('/api/v1/students', headers=auth(student_token))
        assert resp.status_code == 403

    def test_list_students_unauthorized(self, client):
        resp = client.get('/api/v1/students')
        assert resp.status_code == 401

    def test_list_students_search_by_first_name(self, client, admin_token, enrolled_student):
        resp = client.get('/api/v1/students?search=Priya', headers=auth(admin_token))
        assert resp.status_code == 200
        students = resp.get_json()['data']['students']
        assert any(s['first_name'] == 'Priya' for s in students)

    def test_list_students_search_no_match(self, client, admin_token, enrolled_student):
        resp = client.get('/api/v1/students?search=ZZZNOMATCH', headers=auth(admin_token))
        assert resp.status_code == 200
        assert resp.get_json()['data']['meta']['total'] == 0

    def test_list_students_search_by_admission_no(self, client, admin_token, enrolled_student):
        resp = client.get(f'/api/v1/students?search={enrolled_student.admission_no}',
                          headers=auth(admin_token))
        students = resp.get_json()['data']['students']
        assert len(students) == 1
        assert students[0]['admission_no'] == enrolled_student.admission_no

    def test_list_pagination_meta(self, client, admin_token, db, admin_user):
        # Create 5 students
        for i in range(5):
            db.session.add(Student(
                user_id=admin_user.id,
                admission_no=f'PGTEST-{i:03d}',
                first_name='Page',
                last_name=f'Test{i}',
                date_of_birth=date(2010, 1, 1),
                gender='Male',
                admission_date=date(2024, 1, 1),
            ))
        db.session.commit()

        resp = client.get('/api/v1/students?per_page=2&page=1', headers=auth(admin_token))
        meta = resp.get_json()['data']['meta']
        assert meta['per_page'] == 2
        assert meta['total'] >= 5
        assert meta['pages'] >= 3


# ---------------------------------------------------------------------------
# SMS-009 — Profile GET / PUT
# ---------------------------------------------------------------------------

class TestStudentProfile:

    def test_get_student_admin(self, client, admin_token, enrolled_student):
        resp = client.get(f'/api/v1/students/{enrolled_student.id}',
                          headers=auth(admin_token))
        assert resp.status_code == 200
        assert resp.get_json()['data']['id'] == enrolled_student.id

    def test_get_student_not_found(self, client, admin_token):
        resp = client.get('/api/v1/students/99999', headers=auth(admin_token))
        assert resp.status_code == 404

    def test_student_cannot_view_other_student(self, client, student_token, enrolled_student):
        # enrolled_student.user_id != student_user.id
        resp = client.get(f'/api/v1/students/{enrolled_student.id}',
                          headers=auth(student_token))
        assert resp.status_code == 403

    def test_admin_update_student(self, client, admin_token, enrolled_student):
        resp = client.put(f'/api/v1/students/{enrolled_student.id}',
                          json={'phone': '9988776655', 'blood_group': 'O+'},
                          headers=auth(admin_token))
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['phone'] == '9988776655'
        assert data['blood_group'] == 'O+'

    def test_admin_update_invalid_gender(self, client, admin_token, enrolled_student):
        resp = client.put(f'/api/v1/students/{enrolled_student.id}',
                          json={'gender': 'Alien'},
                          headers=auth(admin_token))
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# SMS-013 — Soft delete & status patch
# ---------------------------------------------------------------------------

class TestStudentDeactivation:

    def test_delete_student(self, client, admin_token, enrolled_student):
        resp = client.delete(f'/api/v1/students/{enrolled_student.id}',
                             headers=auth(admin_token))
        assert resp.status_code == 200
        # Should now be gone from list
        resp2 = client.get(f'/api/v1/students/{enrolled_student.id}',
                           headers=auth(admin_token))
        assert resp2.status_code == 404

    def test_delete_student_not_found(self, client, admin_token):
        resp = client.delete('/api/v1/students/99999', headers=auth(admin_token))
        assert resp.status_code == 404

    def test_patch_status(self, client, admin_token, enrolled_student):
        resp = client.patch(f'/api/v1/students/{enrolled_student.id}/status',
                            json={'status': 'alumni', 'leaving_date': '2024-05-31'},
                            headers=auth(admin_token))
        assert resp.status_code == 200
        assert resp.get_json()['data']['status'] == 'alumni'

    def test_patch_status_invalid(self, client, admin_token, enrolled_student):
        resp = client.patch(f'/api/v1/students/{enrolled_student.id}/status',
                            json={'status': 'graduated'},
                            headers=auth(admin_token))
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# SMS-010 — Parent linking
# ---------------------------------------------------------------------------

class TestParentLinking:

    def test_link_parent(self, client, admin_token, enrolled_student, unlinked_parent):
        resp = client.post(f'/api/v1/students/{enrolled_student.id}/parents',
                           json={'parent_id': unlinked_parent.id, 'is_primary_contact': True},
                           headers=auth(admin_token))
        assert resp.status_code == 201
        assert resp.get_json()['success'] is True

    def test_link_parent_duplicate(self, client, admin_token, enrolled_student, linked_parent):
        resp = client.post(f'/api/v1/students/{enrolled_student.id}/parents',
                           json={'parent_id': linked_parent.id},
                           headers=auth(admin_token))
        assert resp.status_code == 409

    def test_link_parent_not_found(self, client, admin_token, enrolled_student):
        resp = client.post(f'/api/v1/students/{enrolled_student.id}/parents',
                           json={'parent_id': 99999},
                           headers=auth(admin_token))
        assert resp.status_code == 404

    def test_get_parents(self, client, admin_token, enrolled_student, linked_parent):
        resp = client.get(f'/api/v1/students/{enrolled_student.id}/parents',
                          headers=auth(admin_token))
        assert resp.status_code == 200
        parents = resp.get_json()['data']
        assert len(parents) >= 1
        assert any(p['id'] == linked_parent.id for p in parents)

    def test_unlink_parent(self, client, admin_token, enrolled_student, linked_parent):
        resp = client.delete(
            f'/api/v1/students/{enrolled_student.id}/parents/{linked_parent.id}',
            headers=auth(admin_token),
        )
        assert resp.status_code == 200

    def test_unlink_parent_not_linked(self, client, admin_token, enrolled_student):
        resp = client.delete(
            f'/api/v1/students/{enrolled_student.id}/parents/99999',
            headers=auth(admin_token),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# SMS-011 — Transfer
# ---------------------------------------------------------------------------

class TestStudentTransfer:

    def test_transfer_creates_new_section(self, client, admin_token, enrolled_student, db):
        # Seed a current section
        current = StudentSection(
            student_id=enrolled_student.id,
            section_id=1,
            academic_year='2023-2024',
            start_date=date(2023, 6, 1),
            is_current=True,
        )
        db.session.add(current)
        db.session.commit()

        resp = client.post(f'/api/v1/students/{enrolled_student.id}/transfer',
                           json={
                               'new_section_id': 2,
                               'effective_date': '2024-06-01',
                               'reason': 'Grade promotion',
                           },
                           headers=auth(admin_token))
        assert resp.status_code == 201
        data = resp.get_json()['data']
        assert data['section_id'] == 2
        assert data['is_current'] is True

        # Old row should be closed
        db.session.refresh(current)
        assert current.is_current is False
        assert current.end_date is not None

    def test_transfer_missing_field(self, client, admin_token, enrolled_student):
        resp = client.post(f'/api/v1/students/{enrolled_student.id}/transfer',
                           json={'new_section_id': 2},
                           headers=auth(admin_token))
        assert resp.status_code == 422

    def test_transfer_student_not_found(self, client, admin_token):
        resp = client.post('/api/v1/students/99999/transfer',
                           json={'new_section_id': 1, 'effective_date': '2024-06-01'},
                           headers=auth(admin_token))
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# SMS-012 — Document upload
# ---------------------------------------------------------------------------

class TestDocumentUpload:

    def _pdf_file(self, name='test.pdf'):
        """Minimal valid PDF bytes wrapped in a FileStorage."""
        pdf_bytes = b'%PDF-1.4 1 0 obj<</Type/Catalog>>endobj'
        return (io.BytesIO(pdf_bytes), name)

    def test_upload_document_success(self, client, admin_token, enrolled_student):
        data = {
            'document_type': 'birth_certificate',
            'file': self._pdf_file(),
        }
        resp = client.post(
            f'/api/v1/students/{enrolled_student.id}/documents',
            data=data,
            content_type='multipart/form-data',
            headers=auth(admin_token),
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body['success'] is True
        assert body['data']['document_type'] == 'birth_certificate'

    def test_upload_invalid_extension(self, client, admin_token, enrolled_student):
        data = {
            'document_type': 'transfer_cert',
            'file': (io.BytesIO(b'data'), 'file.exe'),
        }
        resp = client.post(
            f'/api/v1/students/{enrolled_student.id}/documents',
            data=data,
            content_type='multipart/form-data',
            headers=auth(admin_token),
        )
        assert resp.status_code == 400

    def test_upload_missing_document_type(self, client, admin_token, enrolled_student):
        data = {'file': self._pdf_file()}
        resp = client.post(
            f'/api/v1/students/{enrolled_student.id}/documents',
            data=data,
            content_type='multipart/form-data',
            headers=auth(admin_token),
        )
        assert resp.status_code == 400

    def test_list_documents(self, client, admin_token, enrolled_student):
        # Upload one first
        client.post(
            f'/api/v1/students/{enrolled_student.id}/documents',
            data={'document_type': 'id_proof', 'file': self._pdf_file()},
            content_type='multipart/form-data',
            headers=auth(admin_token),
        )
        resp = client.get(f'/api/v1/students/{enrolled_student.id}/documents',
                          headers=auth(admin_token))
        assert resp.status_code == 200
        docs = resp.get_json()['data']
        assert len(docs) >= 1

    def test_delete_document(self, client, admin_token, enrolled_student):
        upload = client.post(
            f'/api/v1/students/{enrolled_student.id}/documents',
            data={'document_type': 'marksheet', 'file': self._pdf_file()},
            content_type='multipart/form-data',
            headers=auth(admin_token),
        )
        doc_id = upload.get_json()['data']['id']

        resp = client.delete(
            f'/api/v1/students/{enrolled_student.id}/documents/{doc_id}',
            headers=auth(admin_token),
        )
        assert resp.status_code == 200

        # Should not appear in list any more
        list_resp = client.get(f'/api/v1/students/{enrolled_student.id}/documents',
                               headers=auth(admin_token))
        ids = [d['id'] for d in list_resp.get_json()['data']]
        assert doc_id not in ids
