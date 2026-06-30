from flask import Blueprint, request, make_response
from flask_jwt_extended import get_jwt_identity

from app.services.fee_service import FeeService
from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required
from app.schemas.fee_payment_schema import (
    FeePaymentCreateSchema,
    DiscountSchema,
    AmountOverrideSchema,
)

fees_bp = Blueprint("fees", __name__, url_prefix="/api/v1/fees")

_payment_create_schema = FeePaymentCreateSchema()
_discount_schema = DiscountSchema()
_amount_override_schema = AmountOverrideSchema()


def _validate(schema, payload):
    errors = schema.validate(payload or {})
    if errors:
        return None, error_response("Validation failed", errors=errors, status=422)
    return schema.load(payload), None


def _auto_catchup_recurring():
    """Best-effort recurring-fee catch-up before a read. Never raises — a
    generation hiccup must not break viewing the data."""
    try:
        FeeService.run_recurring_catchup()
    except Exception:  # pragma: no cover - defensive
        from app.utils.tenant import get_db

        get_db().rollback()


# ---------------------------------------------------------------------------
# POST /api/v1/fees/payments — record a fee payment (admin only)
# ---------------------------------------------------------------------------


@fees_bp.route("/payments", methods=["POST"], strict_slashes=False)
@roles_required("admin")
def record_payment():
    data, err = _validate(_payment_create_schema, request.get_json())
    if err:
        return err

    result, svc_err = FeeService.record_payment(data)
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 400))
    return success_response(data=result, message="Payment recorded successfully", status=201)


# ---------------------------------------------------------------------------
# GET /api/v1/fees/records?student_id=N — list fee records for a student (admin only)
# ---------------------------------------------------------------------------


@fees_bp.route("/records", methods=["GET"], strict_slashes=False)
@roles_required("admin")
def get_fee_records():
    student_id = request.args.get("student_id", type=int)
    if not student_id:
        return error_response("student_id query parameter is required", status=400)

    # Auto: make sure recurring monthly dues are up to date before showing them.
    _auto_catchup_recurring()
    records = FeeService.get_fee_records(student_id)
    return success_response(data={"fee_records": records}, message="Fee records retrieved")


# ---------------------------------------------------------------------------
# GET /api/v1/fees/defaulters — defaulter report (admin only)
# ---------------------------------------------------------------------------


@fees_bp.route("/defaulters", methods=["GET"], strict_slashes=False)
@roles_required("admin")
def get_defaulters():
    class_id = request.args.get("class_id", type=int)
    # Auto: catch up recurring dues so newly-overdue months show as defaulters.
    _auto_catchup_recurring()
    result = FeeService.get_defaulters(class_id=class_id)
    return success_response(
        data={"defaulters": result, "count": len(result)},
        message="Defaulter report retrieved",
    )


# ---------------------------------------------------------------------------
# POST /api/v1/fees/run-recurring — manually/cron-trigger recurring generation
# ---------------------------------------------------------------------------


@fees_bp.route("/run-recurring", methods=["POST"], strict_slashes=False)
@roles_required("admin")
def run_recurring():
    generated = FeeService.run_recurring_catchup()
    return success_response(
        data={"generated": generated},
        message=f"Recurring fee catch-up complete — {generated} new record(s)",
    )


# ---------------------------------------------------------------------------
# GET /api/v1/fees/payments/<payment_id>/receipt — download fee receipt PDF
# ---------------------------------------------------------------------------


@fees_bp.route("/payments/<int:payment_id>/receipt", methods=["GET"], strict_slashes=False)
@roles_required("admin", "teacher")
def download_receipt(payment_id):
    pdf_bytes, svc_err = FeeService.generate_receipt_pdf(payment_id)
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 404))

    # Fetch the receipt_no for the filename — payment was already validated in the service
    from app.utils.tenant import get_db
    from app.models.fee_payment import FeePayment

    payment = get_db().query(FeePayment).filter_by(id=payment_id).first()
    receipt_no = payment.receipt_no if payment else str(payment_id)

    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="receipt_{receipt_no}.pdf"'
    return response


# ---------------------------------------------------------------------------
# GET /api/v1/fees/records/<record_id> — single fee record with discounts list
# ---------------------------------------------------------------------------


@fees_bp.route("/records/<int:record_id>", methods=["GET"], strict_slashes=False)
@roles_required("admin")
def get_fee_record(record_id):
    result, svc_err = FeeService.get_fee_record(record_id)
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 404))
    return success_response(data=result, message="Fee record retrieved")


# ---------------------------------------------------------------------------
# POST /api/v1/fees/records/<record_id>/discount — apply discount (admin only)
# ---------------------------------------------------------------------------


@fees_bp.route("/records/<int:record_id>/discount", methods=["POST"], strict_slashes=False)
@roles_required("admin")
def apply_discount(record_id):
    data, err = _validate(_discount_schema, request.get_json())
    if err:
        return err

    approved_by_user_id = int(get_jwt_identity())
    discount, svc_err = FeeService.apply_discount(record_id, data, approved_by_user_id)
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 400))
    return success_response(data=discount, message="Discount applied successfully", status=201)


# ---------------------------------------------------------------------------
# PATCH /api/v1/fees/records/<record_id>/amount — set/clear per-student
# base amount override (admin only). (ADR-005 SMS-066)
# ---------------------------------------------------------------------------


@fees_bp.route("/records/<int:record_id>/amount", methods=["PATCH"], strict_slashes=False)
@roles_required("admin")
def set_amount_override(record_id):
    data, err = _validate(_amount_override_schema, request.get_json())
    if err:
        return err

    result, svc_err = FeeService.set_amount_override(record_id, data["amount_override"])
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 400))
    return success_response(data=result, message="Fee record amount updated successfully")
