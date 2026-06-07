from flask import Blueprint, request
from app.services.student_service import StudentService
from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required

students_bp = Blueprint('students', __name__, url_prefix='/api/v1/students')


@students_bp.route('', methods=['GET'])
@roles_required('admin', 'teacher')
def get_students():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    result = StudentService.get_all(page=page, per_page=per_page, search=search)
    return success_response(data=result, message="Students retrieved")


@students_bp.route('/<int:student_id>', methods=['GET'])
@roles_required('admin', 'teacher', 'student', 'parent')
def get_student(student_id):
    student = StudentService.get_by_id(student_id)
    if not student:
        return error_response("Student not found", status=404)
    return success_response(data=student, message="Student retrieved")


@students_bp.route('', methods=['POST'])
@roles_required('admin')
def create_student():
    data = request.get_json()
    if not data:
        return error_response("Request body required", status=400)
    student, err = StudentService.create(data)
    if err:
        return error_response(err['message'], errors=err.get('errors'), status=err.get('status', 400))
    return success_response(data=student, message="Student created successfully", status=201)


@students_bp.route('/<int:student_id>', methods=['PUT'])
@roles_required('admin')
def update_student(student_id):
    data = request.get_json()
    student, err = StudentService.update(student_id, data)
    if err:
        return error_response(err['message'], status=err.get('status', 400))
    return success_response(data=student, message="Student updated successfully")


@students_bp.route('/<int:student_id>', methods=['DELETE'])
@roles_required('admin')
def delete_student(student_id):
    ok, err = StudentService.delete(student_id)
    if err:
        return error_response(err['message'], status=err.get('status', 400))
    return success_response(message="Student deactivated successfully")
