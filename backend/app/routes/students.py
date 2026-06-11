from flask import Blueprint, request
from flask_jwt_extended import get_jwt, get_jwt_identity

from app.services.student_service import StudentService
from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required
from app.utils.tenant import get_db
from app.schemas.student_schema import (
    StudentCreateSchema,
    StudentUpdateSchema,
    StudentSelfUpdateSchema,
    StudentStatusSchema,
    StudentTransferSchema,
    ParentLinkSchema,
)

students_bp = Blueprint('students', __name__, url_prefix='/api/v1/students')

_create_schema = StudentCreateSchema()
_update_schema = StudentUpdateSchema()
_self_update_schema = StudentSelfUpdateSchema()
_status_schema = StudentStatusSchema()
_transfer_schema = StudentTransferSchema()
_parent_link_schema = ParentLinkSchema()


def _validate(schema, payload):
    """Returns (data, None) or (None, error_response)."""
    errors = schema.validate(payload or {})
    if errors:
        return None, error_response('Validation failed', errors=errors, status=422)
    return schema.load(payload), None


# ---------------------------------------------------------------------------
# SMS-008 — Student list
# ---------------------------------------------------------------------------

@students_bp.route('', methods=['GET'])
@roles_required('admin', 'teacher')
def get_students():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    search = request.args.get('search', '')
    section_id = request.args.get('section_id', type=int)
    # class_id deferred to Sprint 3
    result = StudentService.get_all(
        page=page, per_page=per_page, search=search, section_id=section_id
    )
    return success_response(data=result, message='Students retrieved')


# ---------------------------------------------------------------------------
# SMS-007 — Student enrollment (T-007-03)
# ---------------------------------------------------------------------------

@students_bp.route('', methods=['POST'])
@roles_required('admin')
def create_student():
    data, err = _validate(_create_schema, request.get_json())
    if err:
        return err
    student, svc_err = StudentService.create(data)
    if svc_err:
        return error_response(
            svc_err['message'],
            errors=svc_err.get('errors'),
            status=svc_err.get('status', 400),
        )
    return success_response(data=student, message='Student created successfully', status=201)


# ---------------------------------------------------------------------------
# SMS-009 — Student profile
# ---------------------------------------------------------------------------

@students_bp.route('/<int:student_id>', methods=['GET'])
@roles_required('admin', 'teacher', 'student', 'parent')
def get_student(student_id):
    claims = get_jwt()
    role = claims.get('role')
    # Students can only view their own record
    if role == 'student':
        current_user_id = int(get_jwt_identity())
        from app.models.student import Student
        own = get_db().query(Student).filter_by(user_id=current_user_id, is_active=True).first()
        if not own or own.id != student_id:
            return error_response('Access denied', status=403)

    student = StudentService.get_by_id(student_id)
    if not student:
        return error_response('Student not found', status=404)
    return success_response(data=student, message='Student retrieved')


@students_bp.route('/<int:student_id>', methods=['PUT'])
@roles_required('admin', 'student')
def update_student(student_id):
    claims = get_jwt()
    role = claims.get('role')

    if role == 'student':
        current_user_id = int(get_jwt_identity())
        from app.models.student import Student
        own = get_db().query(Student).filter_by(user_id=current_user_id, is_active=True).first()
        if not own or own.id != student_id:
            return error_response('Access denied', status=403)
        data, err = _validate(_self_update_schema, request.get_json())
    else:
        data, err = _validate(_update_schema, request.get_json())

    if err:
        return err

    student, svc_err = StudentService.update(student_id, data, role=role)
    if svc_err:
        return error_response(svc_err['message'], status=svc_err.get('status', 400))
    return success_response(data=student, message='Student updated successfully')


# ---------------------------------------------------------------------------
# SMS-013 — Soft delete & status patch
# ---------------------------------------------------------------------------

@students_bp.route('/<int:student_id>', methods=['DELETE'])
@roles_required('admin')
def delete_student(student_id):
    ok, err = StudentService.delete(student_id)
    if err:
        return error_response(err['message'], status=err.get('status', 400))
    return success_response(message='Student deactivated successfully')


@students_bp.route('/<int:student_id>/status', methods=['PATCH'])
@roles_required('admin')
def update_student_status(student_id):
    data, err = _validate(_status_schema, request.get_json())
    if err:
        return err
    student, svc_err = StudentService.update_status(student_id, data)
    if svc_err:
        return error_response(svc_err['message'], status=svc_err.get('status', 400))
    return success_response(data=student, message='Student status updated')


# ---------------------------------------------------------------------------
# SMS-010 — Parent linking
# ---------------------------------------------------------------------------

@students_bp.route('/<int:student_id>/parents', methods=['POST'])
@roles_required('admin')
def link_parent(student_id):
    data, err = _validate(_parent_link_schema, request.get_json())
    if err:
        return err
    parent, svc_err = StudentService.link_parent(
        student_id, data['parent_id'], data.get('is_primary_contact', False)
    )
    if svc_err:
        return error_response(svc_err['message'], status=svc_err.get('status', 400))
    return success_response(data=parent, message='Parent linked successfully', status=201)


@students_bp.route('/<int:student_id>/parents/<int:parent_id>', methods=['DELETE'])
@roles_required('admin')
def unlink_parent(student_id, parent_id):
    ok, err = StudentService.unlink_parent(student_id, parent_id)
    if err:
        return error_response(err['message'], status=err.get('status', 400))
    return success_response(message='Parent unlinked successfully')


@students_bp.route('/<int:student_id>/parents', methods=['GET'])
@roles_required('admin')
def get_student_parents(student_id):
    parents, err = StudentService.get_parents(student_id)
    if err:
        return error_response(err['message'], status=err.get('status', 400))
    return success_response(data=parents, message='Parents retrieved')


# ---------------------------------------------------------------------------
# SMS-011 — Student transfer
# ---------------------------------------------------------------------------

@students_bp.route('/<int:student_id>/transfer', methods=['POST'])
@roles_required('admin')
def transfer_student(student_id):
    data, err = _validate(_transfer_schema, request.get_json())
    if err:
        return err
    enrollment, svc_err = StudentService.transfer(student_id, data)
    if svc_err:
        return error_response(svc_err['message'], status=svc_err.get('status', 400))
    return success_response(data=enrollment, message='Student transferred successfully', status=201)


# ---------------------------------------------------------------------------
# SMS-012 — Document upload / list / delete
# ---------------------------------------------------------------------------

@students_bp.route('/<int:student_id>/documents', methods=['POST'])
@roles_required('admin', 'teacher')
def upload_document(student_id):
    document_type = request.form.get('document_type', '').strip()
    if not document_type:
        return error_response('document_type is required', status=400)

    file = request.files.get('file')
    if not file:
        return error_response('file is required', status=400)

    uploader_id = int(get_jwt_identity())
    doc, err = StudentService.upload_document(student_id, document_type, file, uploader_id)
    if err:
        return error_response(err['message'], status=err.get('status', 400))
    return success_response(data=doc, message='Document uploaded successfully', status=201)


@students_bp.route('/<int:student_id>/documents', methods=['GET'])
@roles_required('admin', 'teacher')
def list_documents(student_id):
    docs, err = StudentService.list_documents(student_id)
    if err:
        return error_response(err['message'], status=err.get('status', 400))
    return success_response(data=docs, message='Documents retrieved')


@students_bp.route('/<int:student_id>/documents/<int:doc_id>', methods=['DELETE'])
@roles_required('admin')
def delete_document(student_id, doc_id):
    ok, err = StudentService.delete_document(student_id, doc_id)
    if err:
        return error_response(err['message'], status=err.get('status', 400))
    return success_response(message='Document deleted successfully')
