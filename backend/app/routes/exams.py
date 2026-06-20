from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, get_jwt

from app.services.exam_service import ExamService
from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required
from app.schemas.exam_schema import ExamCreateSchema, ExamUpdateSchema, ExamMarksSchema

exams_bp = Blueprint('exams', __name__, url_prefix='/api/v1/exams')

_create_schema = ExamCreateSchema()
_update_schema = ExamUpdateSchema()
_marks_schema = ExamMarksSchema()


def _validate(schema, payload):
    errors = schema.validate(payload or {})
    if errors:
        return None, error_response('Validation failed', errors=errors, status=422)
    return schema.load(payload), None


# ---------------------------------------------------------------------------
# POST /api/v1/exams — create exam (admin only)
# ---------------------------------------------------------------------------

@exams_bp.route('', methods=['POST'], strict_slashes=False)
@roles_required('admin')
def create_exam():
    user_id = int(get_jwt_identity())
    data, err = _validate(_create_schema, request.get_json())
    if err:
        return err

    result, svc_err = ExamService.create_exam(data, created_by=user_id)
    if svc_err:
        return error_response(svc_err['message'], status=svc_err.get('status', 400))
    return success_response(data=result, message='Exam created successfully', status=201)


# ---------------------------------------------------------------------------
# GET /api/v1/exams — list exams (admin + teacher)
# ---------------------------------------------------------------------------

@exams_bp.route('', methods=['GET'], strict_slashes=False)
@roles_required('admin', 'teacher')
def list_exams():
    section_id = request.args.get('section_id', type=int)
    academic_year_id = request.args.get('academic_year_id', type=int)
    is_active_str = request.args.get('is_active')

    is_active = None
    if is_active_str is not None:
        is_active = is_active_str.lower() in ('true', '1')

    exams = ExamService.get_exams(
        section_id=section_id,
        academic_year_id=academic_year_id,
        is_active=is_active,
    )
    return success_response(data={'exams': exams}, message='Exams retrieved')


# ---------------------------------------------------------------------------
# GET /api/v1/exams/<id> — single exam (admin + teacher)
# ---------------------------------------------------------------------------

@exams_bp.route('/<int:exam_id>', methods=['GET'], strict_slashes=False)
@roles_required('admin', 'teacher')
def get_exam(exam_id):
    result, svc_err = ExamService.get_exam(exam_id)
    if svc_err:
        return error_response(svc_err['message'], status=svc_err.get('status', 404))
    return success_response(data=result, message='Exam retrieved')


# ---------------------------------------------------------------------------
# PUT /api/v1/exams/<id> — update exam (admin only)
# ---------------------------------------------------------------------------

@exams_bp.route('/<int:exam_id>', methods=['PUT'], strict_slashes=False)
@roles_required('admin')
def update_exam(exam_id):
    data, err = _validate(_update_schema, request.get_json())
    if err:
        return err

    # Strip None values from update schema defaults so we only update supplied fields
    data = {k: v for k, v in data.items() if v is not None}

    result, svc_err = ExamService.update_exam(exam_id, data)
    if svc_err:
        return error_response(svc_err['message'], status=svc_err.get('status', 400))
    return success_response(data=result, message='Exam updated successfully')


# ---------------------------------------------------------------------------
# T-030-04: POST /api/v1/exams/<exam_id>/marks — enter subject-wise marks
# ---------------------------------------------------------------------------

@exams_bp.route('/<int:exam_id>/marks', methods=['POST'], strict_slashes=False)
@roles_required('admin', 'teacher')
def enter_marks(exam_id):
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())

    data, err = _validate(_marks_schema, request.get_json())
    if err:
        return err

    result, svc_err = ExamService.enter_marks(
        exam_id=exam_id,
        subject_id=data['subject_id'],
        section_id=data['section_id'],
        marks_list=data['marks'],
        created_by_user_id=user_id,
        role=role,
    )
    if svc_err:
        return error_response(svc_err['message'], status=svc_err.get('status', 400))
    return success_response(data=result, message='Marks saved', status=201)
