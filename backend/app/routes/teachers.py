from flask import Blueprint, request
from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required

teachers_bp = Blueprint('teachers', __name__, url_prefix='/api/v1/teachers')


@teachers_bp.route('/', methods=['GET'])
@roles_required('admin')
def get_teachers():
    return success_response(data={'teachers': [], 'meta': {'total': 0}}, message="Teachers retrieved")


@teachers_bp.route('/<int:teacher_id>', methods=['GET'])
@roles_required('admin', 'teacher')
def get_teacher(teacher_id):
    return error_response("Teacher not found", status=404)
