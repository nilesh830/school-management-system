"""
SMS-035 — Fee Structure per Class
Tests: CRUD operations, validation, authorization, filters
"""
import pytest
from datetime import date
from app.models.class_ import Class
from app.models.academic_year import AcademicYear
from app.models.fee_structure import FeeStructure


# ---------------------------------------------------------------------------
# Helpers
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


# ---------------------------------------------------------------------------
# 1. test_create_fee_structure_success
# ---------------------------------------------------------------------------

class TestCreateFeeStructureSuccess:

    def test_create_fee_structure_success(self, client, admin_token, db):
        cls = make_class(db, name='Grade 1', grade_level=1)
        ay = make_academic_year(db, name='2024-2025')

        resp = client.post('/api/v1/fee-structures', json={
            'class_id': cls.id,
            'academic_year_id': ay.id,
            'fee_type': 'Tuition Fee',
            'amount': 5000.00,
            'is_recurring': True,
            'frequency': 'monthly',
        }, headers={'Authorization': f'Bearer {admin_token}'})

        assert resp.status_code == 201
        body = resp.get_json()
        assert body['success'] is True
        assert body['data']['class_id'] == cls.id
        assert body['data']['academic_year_id'] == ay.id
        assert body['data']['fee_type'] == 'Tuition Fee'
        assert body['data']['amount'] == 5000.0
        assert body['data']['is_recurring'] is True
        assert body['data']['frequency'] == 'monthly'
        assert body['data']['is_active'] is True


# ---------------------------------------------------------------------------
# 2. test_create_fee_structure_invalid_class
# ---------------------------------------------------------------------------

class TestCreateFeeStructureInvalidClass:

    def test_create_fee_structure_invalid_class(self, client, admin_token, db):
        ay = make_academic_year(db, name='2024-2025-B')

        resp = client.post('/api/v1/fee-structures', json={
            'class_id': 99999,
            'academic_year_id': ay.id,
            'fee_type': 'Exam Fee',
            'amount': 1000.00,
            'due_date': '2026-07-31',
        }, headers={'Authorization': f'Bearer {admin_token}'})

        assert resp.status_code == 404
        body = resp.get_json()
        assert body['success'] is False


# ---------------------------------------------------------------------------
# 3. test_create_fee_structure_invalid_frequency
# ---------------------------------------------------------------------------

class TestCreateFeeStructureInvalidFrequency:

    def test_create_fee_structure_invalid_frequency(self, client, admin_token, db):
        cls = make_class(db, name='Grade 2', grade_level=2)
        ay = make_academic_year(db, name='2024-2025-C')

        resp = client.post('/api/v1/fee-structures', json={
            'class_id': cls.id,
            'academic_year_id': ay.id,
            'fee_type': 'Library Fee',
            'amount': 200.00,
            'frequency': 'weekly',  # not a valid frequency
        }, headers={'Authorization': f'Bearer {admin_token}'})

        assert resp.status_code == 422
        body = resp.get_json()
        assert body['success'] is False


# ---------------------------------------------------------------------------
# 4. test_create_fee_structure_negative_amount
# ---------------------------------------------------------------------------

class TestCreateFeeStructureNegativeAmount:

    def test_create_fee_structure_negative_amount(self, client, admin_token, db):
        cls = make_class(db, name='Grade 3', grade_level=3)
        ay = make_academic_year(db, name='2024-2025-D')

        resp = client.post('/api/v1/fee-structures', json={
            'class_id': cls.id,
            'academic_year_id': ay.id,
            'fee_type': 'Sports Fee',
            'amount': -1,
        }, headers={'Authorization': f'Bearer {admin_token}'})

        assert resp.status_code == 422
        body = resp.get_json()
        assert body['success'] is False


# ---------------------------------------------------------------------------
# 5. test_list_fee_structures
# ---------------------------------------------------------------------------

class TestListFeeStructures:

    def test_list_fee_structures(self, client, admin_token, db):
        cls = make_class(db, name='Grade 4', grade_level=4)
        ay = make_academic_year(db, name='2025-2026')
        make_fee_structure(db, cls.id, ay.id, fee_type='Tuition Fee', amount=6000)
        make_fee_structure(db, cls.id, ay.id, fee_type='Lab Fee', amount=500)

        resp = client.get('/api/v1/fee-structures',
                          headers={'Authorization': f'Bearer {admin_token}'})

        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        assert len(body['data']['fee_structures']) == 2


# ---------------------------------------------------------------------------
# 6. test_list_fee_structures_filter_by_class
# ---------------------------------------------------------------------------

class TestListFeeStructuresFilterByClass:

    def test_list_fee_structures_filter_by_class(self, client, admin_token, db):
        cls_a = make_class(db, name='Grade 5A', grade_level=5)
        cls_b = make_class(db, name='Grade 5B', grade_level=5)
        ay = make_academic_year(db, name='2025-2026-B')

        make_fee_structure(db, cls_a.id, ay.id, fee_type='Tuition', amount=5000)
        make_fee_structure(db, cls_b.id, ay.id, fee_type='Tuition', amount=5500)

        resp = client.get(
            f'/api/v1/fee-structures?class_id={cls_a.id}',
            headers={'Authorization': f'Bearer {admin_token}'},
        )

        assert resp.status_code == 200
        results = resp.get_json()['data']['fee_structures']
        assert len(results) == 1
        assert results[0]['class_id'] == cls_a.id


# ---------------------------------------------------------------------------
# 7. test_get_fee_structure
# ---------------------------------------------------------------------------

class TestGetFeeStructure:

    def test_get_fee_structure(self, client, admin_token, db):
        cls = make_class(db, name='Grade 6', grade_level=6)
        ay = make_academic_year(db, name='2026-2027')
        fs = make_fee_structure(db, cls.id, ay.id, fee_type='Annual Fee', amount=10000)

        resp = client.get(f'/api/v1/fee-structures/{fs.id}',
                          headers={'Authorization': f'Bearer {admin_token}'})

        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        assert body['data']['id'] == fs.id
        assert body['data']['fee_type'] == 'Annual Fee'


# ---------------------------------------------------------------------------
# 8. test_get_fee_structure_not_found
# ---------------------------------------------------------------------------

class TestGetFeeStructureNotFound:

    def test_get_fee_structure_not_found(self, client, admin_token):
        resp = client.get('/api/v1/fee-structures/99999',
                          headers={'Authorization': f'Bearer {admin_token}'})

        assert resp.status_code == 404
        body = resp.get_json()
        assert body['success'] is False


# ---------------------------------------------------------------------------
# 9. test_update_fee_structure
# ---------------------------------------------------------------------------

class TestUpdateFeeStructure:

    def test_update_fee_structure(self, client, admin_token, db):
        cls = make_class(db, name='Grade 7', grade_level=7)
        ay = make_academic_year(db, name='2027-2028')
        fs = make_fee_structure(db, cls.id, ay.id, fee_type='Old Fee', amount=3000)

        resp = client.put(f'/api/v1/fee-structures/{fs.id}', json={
            'fee_type': 'Updated Fee',
        }, headers={'Authorization': f'Bearer {admin_token}'})

        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        assert body['data']['fee_type'] == 'Updated Fee'
        # amount should remain unchanged
        assert body['data']['amount'] == 3000.0


# ---------------------------------------------------------------------------
# 10. test_delete_fee_structure
# ---------------------------------------------------------------------------

class TestDeleteFeeStructure:

    def test_delete_fee_structure(self, client, admin_token, db):
        cls = make_class(db, name='Grade 8', grade_level=8)
        ay = make_academic_year(db, name='2028-2029')
        fs = make_fee_structure(db, cls.id, ay.id, fee_type='Transport Fee', amount=1500)

        resp = client.delete(f'/api/v1/fee-structures/{fs.id}',
                             headers={'Authorization': f'Bearer {admin_token}'})

        assert resp.status_code == 200
        body = resp.get_json()
        assert body['success'] is True
        assert body['data']['deleted'] is True

        # Verify soft delete: record still exists with is_active=False
        db.session.refresh(fs)
        assert fs.is_active is False


# ---------------------------------------------------------------------------
# 11. test_teacher_cannot_create
# ---------------------------------------------------------------------------

class TestTeacherCannotCreate:

    def test_teacher_cannot_create(self, client, teacher_token, db):
        cls = make_class(db, name='Grade 9', grade_level=9)
        ay = make_academic_year(db, name='2029-2030')

        resp = client.post('/api/v1/fee-structures', json={
            'class_id': cls.id,
            'academic_year_id': ay.id,
            'fee_type': 'Unauthorized Fee',
            'amount': 100.00,
        }, headers={'Authorization': f'Bearer {teacher_token}'})

        assert resp.status_code == 403
        body = resp.get_json()
        assert body['success'] is False


# ---------------------------------------------------------------------------
# 12. test_teacher_cannot_delete
# ---------------------------------------------------------------------------

class TestTeacherCannotDelete:

    def test_teacher_cannot_delete(self, client, admin_token, teacher_token, db):
        cls = make_class(db, name='Grade 10', grade_level=10)
        ay = make_academic_year(db, name='2030-2031')
        fs = make_fee_structure(db, cls.id, ay.id, fee_type='Lab Fee', amount=800)

        resp = client.delete(f'/api/v1/fee-structures/{fs.id}',
                             headers={'Authorization': f'Bearer {teacher_token}'})

        assert resp.status_code == 403
        body = resp.get_json()
        assert body['success'] is False
