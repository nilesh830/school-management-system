from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.services.fee_structure_service import FeeStructureService
from app.services.fee_service import FeeService
from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required
from app.schemas.fee_structure_schema import FeeStructureCreateSchema, FeeStructureUpdateSchema
from app.schemas.fee_optin_schema import FeeOptinBulkAddSchema, FeeOptinBulkRemoveSchema

fee_structures_bp = Blueprint("fee_structures", __name__, url_prefix="/api/v1/fee-structures")

_create_schema = FeeStructureCreateSchema()
_update_schema = FeeStructureUpdateSchema()


def _validate(schema, payload):
    errors = schema.validate(payload or {})
    if errors:
        return None, error_response("Validation failed", errors=errors, status=422)
    return schema.load(payload), None


# ---------------------------------------------------------------------------
# POST /api/v1/fee-structures — create fee structure (admin only)
# ---------------------------------------------------------------------------


@fee_structures_bp.route("", methods=["POST"], strict_slashes=False)
@roles_required("admin")
def create_fee_structure():
    data, err = _validate(_create_schema, request.get_json())
    if err:
        return err

    result, svc_err = FeeStructureService.create_fee_structure(data)
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 400))
    return success_response(data=result, message="Fee structure created successfully", status=201)


# ---------------------------------------------------------------------------
# GET /api/v1/fee-structures — list fee structures (admin + teacher)
# ---------------------------------------------------------------------------


@fee_structures_bp.route("", methods=["GET"], strict_slashes=False)
@roles_required("admin", "teacher")
def list_fee_structures():
    class_id = request.args.get("class_id", type=int)
    academic_year_id = request.args.get("academic_year_id", type=int)

    results = FeeStructureService.get_fee_structures(
        class_id=class_id,
        academic_year_id=academic_year_id,
    )
    return success_response(data={"fee_structures": results}, message="Fee structures retrieved")


# ---------------------------------------------------------------------------
# GET /api/v1/fee-structures/<id> — single fee structure (admin + teacher)
# ---------------------------------------------------------------------------


@fee_structures_bp.route("/<int:fee_structure_id>", methods=["GET"], strict_slashes=False)
@roles_required("admin", "teacher")
def get_fee_structure(fee_structure_id):
    result, svc_err = FeeStructureService.get_fee_structure(fee_structure_id)
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 404))
    return success_response(data=result, message="Fee structure retrieved")


# ---------------------------------------------------------------------------
# PUT /api/v1/fee-structures/<id> — update fee structure (admin only)
# ---------------------------------------------------------------------------


@fee_structures_bp.route("/<int:fee_structure_id>", methods=["PUT"], strict_slashes=False)
@roles_required("admin")
def update_fee_structure(fee_structure_id):
    data, err = _validate(_update_schema, request.get_json())
    if err:
        return err

    result, svc_err = FeeStructureService.update_fee_structure(fee_structure_id, data)
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 400))
    return success_response(data=result, message="Fee structure updated successfully")


# ---------------------------------------------------------------------------
# DELETE /api/v1/fee-structures/<id> — soft delete (admin only)
# ---------------------------------------------------------------------------


@fee_structures_bp.route("/<int:fee_structure_id>", methods=["DELETE"], strict_slashes=False)
@roles_required("admin")
def delete_fee_structure(fee_structure_id):
    result, svc_err = FeeStructureService.delete_fee_structure(fee_structure_id)
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 400))
    return success_response(data=result, message="Fee structure deleted successfully")


# ---------------------------------------------------------------------------
# POST /api/v1/fee-structures/<id>/generate — generate fee records (admin only)
# ---------------------------------------------------------------------------


@fee_structures_bp.route("/<int:fee_structure_id>/generate", methods=["POST"], strict_slashes=False)
@roles_required("admin")
def generate_fee_records(fee_structure_id):
    result, svc_err = FeeService.generate_records_for_class(fee_structure_id)
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 400))
    return success_response(data=result, message="Fee records generated successfully")


# ---------------------------------------------------------------------------
# GET /api/v1/fee-structures/<id>/opt-in — list opted-in students (admin)
# ---------------------------------------------------------------------------


@fee_structures_bp.route("/<int:fee_structure_id>/opt-in", methods=["GET"], strict_slashes=False)
@roles_required("admin")
def list_fee_optins(fee_structure_id):
    result, svc_err = FeeStructureService.list_optins(fee_structure_id)
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 404))
    return success_response(data={"optins": result}, message="Opt-in list retrieved")


# ---------------------------------------------------------------------------
# POST /api/v1/fee-structures/<id>/opt-in — bulk add students (admin)
# ---------------------------------------------------------------------------

_optin_add_schema = FeeOptinBulkAddSchema()
_optin_remove_schema = FeeOptinBulkRemoveSchema()


@fee_structures_bp.route("/<int:fee_structure_id>/opt-in", methods=["POST"], strict_slashes=False)
@roles_required("admin")
def add_fee_optins(fee_structure_id):
    payload = request.get_json()
    errors = _optin_add_schema.validate(payload or {})
    if errors:
        return error_response("Validation failed", errors=errors, status=422)
    data = _optin_add_schema.load(payload)

    current_user_id = get_jwt_identity()
    result, svc_err = FeeStructureService.add_optins(
        fee_structure_id=fee_structure_id,
        student_ids=data["student_ids"],
        amount_override=data.get("amount_override"),
        opted_in_by=current_user_id,
    )
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 400))
    return success_response(data=result, message="Students opted in successfully", status=201)


# ---------------------------------------------------------------------------
# DELETE /api/v1/fee-structures/<id>/opt-in — bulk remove students (admin)
# ---------------------------------------------------------------------------


@fee_structures_bp.route("/<int:fee_structure_id>/opt-in", methods=["DELETE"], strict_slashes=False)
@roles_required("admin")
def remove_fee_optins(fee_structure_id):
    payload = request.get_json()
    errors = _optin_remove_schema.validate(payload or {})
    if errors:
        return error_response("Validation failed", errors=errors, status=422)
    data = _optin_remove_schema.load(payload)

    result, svc_err = FeeStructureService.remove_optins(
        fee_structure_id=fee_structure_id,
        student_ids=data["student_ids"],
    )
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 400))
    return success_response(data=result, message="Students removed from opt-in")
