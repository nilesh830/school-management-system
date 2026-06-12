from flask import Blueprint, request
from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required
from app.services.section_service import SectionService

sections_bp = Blueprint('sections', __name__, url_prefix='/api/v1/sections')


@sections_bp.route('/', methods=['GET'], strict_slashes=False)
@roles_required('admin', 'teacher')
def list_sections():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    class_id = request.args.get('class_id', type=int)
    result = SectionService.get_all(class_id=class_id, page=page, per_page=per_page)
    return success_response(data=result, message='Sections retrieved')


@sections_bp.route('/<int:section_id>', methods=['GET'])
@roles_required('admin', 'teacher')
def get_section(section_id):
    section = SectionService.get_by_id(section_id)
    if not section:
        return error_response('Section not found', status=404)
    return success_response(data=section, message='Section retrieved')


@sections_bp.route('/', methods=['POST'], strict_slashes=False)
@roles_required('admin')
def create_section():
    data = request.get_json(silent=True) or {}
    result, err = SectionService.create(data)
    if err:
        return error_response(err['message'], status=err['status'])
    return success_response(data=result, message='Section created', status=201)


@sections_bp.route('/<int:section_id>', methods=['PUT'])
@roles_required('admin')
def update_section(section_id):
    data = request.get_json(silent=True) or {}
    result, err = SectionService.update(section_id, data)
    if err:
        return error_response(err['message'], status=err['status'])
    return success_response(data=result, message='Section updated')


@sections_bp.route('/<int:section_id>', methods=['DELETE'])
@roles_required('admin')
def delete_section(section_id):
    ok, err = SectionService.delete(section_id)
    if err:
        return error_response(err['message'], status=err['status'])
    return success_response(message='Section deleted')


@sections_bp.route('/<int:section_id>/enroll', methods=['POST'])
@roles_required('admin')
def enroll_student(section_id):
    """Enroll a student in this section. Body: {student_id, academic_year_id}"""
    data = request.get_json(silent=True) or {}
    student_id = data.get('student_id')
    academic_year_id = data.get('academic_year_id')

    if not student_id:
        return error_response('student_id is required', status=400)

    result, err = SectionService.enroll_student(
        section_id=section_id,
        student_id=student_id,
        academic_year_id=academic_year_id,
    )
    if err:
        return error_response(err['message'], status=err['status'])
    return success_response(data=result, message='Student enrolled in section', status=201)


@sections_bp.route('/<int:section_id>/students/<int:student_id>', methods=['DELETE'])
@roles_required('admin')
def unenroll_student(section_id, student_id):
    """Remove a student from this section."""
    ok, err = SectionService.unenroll_student(section_id=section_id, student_id=student_id)
    if err:
        return error_response(err['message'], status=err['status'])
    return success_response(message='Student unenrolled from section')
