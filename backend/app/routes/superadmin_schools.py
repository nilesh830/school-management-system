import logging

from flask import Blueprint, request

from app.schemas.superadmin_schema import SchoolCreateSchema, SchoolUpdateSchema
from app.services.superadmin_service import SuperAdminService
from app.utils.decorators import roles_required
from app.utils.response import error_response, success_response

logger = logging.getLogger(__name__)

superadmin_schools_bp = Blueprint("superadmin_schools", __name__, url_prefix="/api/v1/superadmin/schools")

_create_schema = SchoolCreateSchema()
_update_schema = SchoolUpdateSchema()


# ---------------------------------------------------------------------------
# ERP-003 — GET /api/v1/superadmin/schools/
# ---------------------------------------------------------------------------


@superadmin_schools_bp.route("/", methods=["GET"], strict_slashes=False)
@roles_required("super_admin")
def list_schools():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "", type=str)

    result = SuperAdminService.get_all_schools(page=page, per_page=per_page, search=search)
    return success_response(data=result, message="Schools retrieved")


# ---------------------------------------------------------------------------
# ERP-003 — POST /api/v1/superadmin/schools/  (provision)
# ---------------------------------------------------------------------------


@superadmin_schools_bp.route("/", methods=["POST"], strict_slashes=False)
@roles_required("super_admin")
def provision_school():
    body = request.get_json() or {}
    errors = _create_schema.validate(body)
    if errors:
        return error_response("Validation failed", errors=errors, status=422)

    validated = _create_schema.load(body)
    school_dict, err = SuperAdminService.provision_school(validated)

    if err:
        return error_response(err["message"], status=err["status"])

    return success_response(data=school_dict, message="School provisioned successfully", status=201)


# ---------------------------------------------------------------------------
# ERP-003 — GET /api/v1/superadmin/schools/<id>
# ---------------------------------------------------------------------------


@superadmin_schools_bp.route("/<int:school_id>", methods=["GET"])
@roles_required("super_admin")
def get_school(school_id):
    school_dict = SuperAdminService.get_school_by_id(school_id)
    if not school_dict:
        return error_response("School not found", status=404)
    return success_response(data=school_dict, message="School retrieved")


# ---------------------------------------------------------------------------
# ERP-003 — PATCH /api/v1/superadmin/schools/<id>
# ---------------------------------------------------------------------------


@superadmin_schools_bp.route("/<int:school_id>", methods=["PATCH"])
@roles_required("super_admin")
def update_school(school_id):
    body = request.get_json() or {}
    errors = _update_schema.validate(body)
    if errors:
        return error_response("Validation failed", errors=errors, status=422)

    validated = _update_schema.load(body)
    school_dict, err = SuperAdminService.update_school(school_id, validated)

    if err:
        return error_response(err["message"], status=err["status"])

    return success_response(data=school_dict, message="School updated successfully")
