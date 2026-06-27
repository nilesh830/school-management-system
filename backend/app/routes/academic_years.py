from flask import Blueprint, request
from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required
from app.services.academic_year_service import AcademicYearService

academic_years_bp = Blueprint("academic_years", __name__, url_prefix="/api/v1/academic-years")


@academic_years_bp.route("/", methods=["GET"], strict_slashes=False)
@roles_required("admin", "teacher")
def list_academic_years():
    years = AcademicYearService.get_all()
    return success_response(data={"academic_years": years}, message="Academic years retrieved")


@academic_years_bp.route("/current", methods=["GET"])
@roles_required("admin", "teacher")
def get_current_academic_year():
    year = AcademicYearService.get_current()
    if not year:
        return error_response("No current academic year set", status=404)
    return success_response(data=year, message="Current academic year retrieved")


@academic_years_bp.route("/", methods=["POST"], strict_slashes=False)
@roles_required("admin")
def create_academic_year():
    data = request.get_json(silent=True) or {}
    result, err = AcademicYearService.create(data)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(data=result, message="Academic year created", status=201)


@academic_years_bp.route("/<int:year_id>", methods=["PUT"])
@roles_required("admin")
def update_academic_year(year_id):
    data = request.get_json(silent=True) or {}
    result, err = AcademicYearService.update(year_id, data)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(data=result, message="Academic year updated")


@academic_years_bp.route("/<int:year_id>", methods=["DELETE"])
@roles_required("admin")
def delete_academic_year(year_id):
    ok, err = AcademicYearService.delete(year_id)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(message="Academic year deleted")
