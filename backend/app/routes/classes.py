from flask import Blueprint, request
from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required
from app.services.class_service import ClassService

classes_bp = Blueprint("classes", __name__, url_prefix="/api/v1/classes")


@classes_bp.route("/", methods=["GET"], strict_slashes=False)
@roles_required("admin", "teacher")
def list_classes():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "", type=str)
    academic_year_id = request.args.get("academic_year_id", type=int)
    result = ClassService.get_all(page=page, per_page=per_page, search=search, academic_year_id=academic_year_id)
    return success_response(data=result, message="Classes retrieved")


@classes_bp.route("/<int:class_id>", methods=["GET"])
@roles_required("admin", "teacher")
def get_class(class_id):
    cls = ClassService.get_by_id(class_id)
    if not cls:
        return error_response("Class not found", status=404)
    return success_response(data=cls, message="Class retrieved")


@classes_bp.route("/", methods=["POST"], strict_slashes=False)
@roles_required("admin")
def create_class():
    data = request.get_json(silent=True) or {}
    result, err = ClassService.create(data)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(data=result, message="Class created", status=201)


@classes_bp.route("/<int:class_id>", methods=["PUT"])
@roles_required("admin")
def update_class(class_id):
    data = request.get_json(silent=True) or {}
    result, err = ClassService.update(class_id, data)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(data=result, message="Class updated")


@classes_bp.route("/<int:class_id>", methods=["DELETE"])
@roles_required("admin")
def delete_class(class_id):
    ok, err = ClassService.delete(class_id)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(message="Class deleted")
