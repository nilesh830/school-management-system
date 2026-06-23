from flask import Blueprint, request
from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required
from app.services.subject_service import SubjectService

subjects_bp = Blueprint("subjects", __name__, url_prefix="/api/v1/subjects")


@subjects_bp.route("/", methods=["GET"], strict_slashes=False)
@roles_required("admin", "teacher")
def list_subjects():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "", type=str)
    result = SubjectService.get_all(page=page, per_page=per_page, search=search)
    return success_response(data=result, message="Subjects retrieved")


@subjects_bp.route("/<int:subject_id>", methods=["GET"])
@roles_required("admin", "teacher")
def get_subject(subject_id):
    subject = SubjectService.get_by_id(subject_id)
    if not subject:
        return error_response("Subject not found", status=404)
    return success_response(data=subject, message="Subject retrieved")


@subjects_bp.route("/", methods=["POST"], strict_slashes=False)
@roles_required("admin")
def create_subject():
    data = request.get_json(silent=True) or {}
    result, err = SubjectService.create(data)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(data=result, message="Subject created", status=201)


@subjects_bp.route("/<int:subject_id>", methods=["PUT"])
@roles_required("admin")
def update_subject(subject_id):
    data = request.get_json(silent=True) or {}
    result, err = SubjectService.update(subject_id, data)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(data=result, message="Subject updated")


@subjects_bp.route("/<int:subject_id>", methods=["DELETE"])
@roles_required("admin")
def delete_subject(subject_id):
    ok, err = SubjectService.delete(subject_id)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(message="Subject deleted")
