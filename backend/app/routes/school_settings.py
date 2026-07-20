"""Admin-facing per-school settings — currently the outbound SMTP config used
to email bulk-registration credentials FROM the school's own address.

Config lives in the master ``school_email_configs`` table and is keyed by the
``school_slug`` claim in the admin's JWT, so an admin can only ever read/write
their own school's config.
"""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt

from app import db
from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required
from app.utils.validators import validate_email
from app.models.master.school_email_config import SchoolEmailConfig

school_settings_bp = Blueprint("school_settings", __name__, url_prefix="/api/v1/school")


@school_settings_bp.route("/email-config", methods=["GET"])
@roles_required("admin")
def get_email_config():
    slug = get_jwt().get("school_slug")
    row = SchoolEmailConfig.query.filter_by(school_slug=slug).first()
    return success_response(data=row.to_dict() if row else None, message="Email config retrieved")


@school_settings_bp.route("/email-config", methods=["PUT"])
@roles_required("admin")
def upsert_email_config():
    slug = get_jwt().get("school_slug")
    if not slug:
        return error_response("No school context in token", status=400)

    data = request.get_json(silent=True) or {}
    row = SchoolEmailConfig.query.filter_by(school_slug=slug).first()

    host = (data.get("smtp_host") or "").strip()
    username = (data.get("smtp_username") or "").strip()
    from_email = (data.get("from_email") or "").strip()
    password = data.get("smtp_password")  # may be omitted on update to keep existing

    # Required fields (password required only when creating a new config).
    missing = [f for f, v in [("smtp_host", host), ("smtp_username", username), ("from_email", from_email)] if not v]
    if row is None and not password:
        missing.append("smtp_password")
    if missing:
        return error_response(f"Missing required fields: {', '.join(missing)}", status=422)

    if not validate_email(from_email):
        return error_response("from_email is not a valid email address", status=422)

    port = data.get("smtp_port", 587)
    try:
        port = int(port)
    except (TypeError, ValueError):
        return error_response("smtp_port must be a number", status=422)

    use_tls = bool(data.get("smtp_use_tls", True))
    from_name = (data.get("from_name") or "").strip() or None

    if row is None:
        row = SchoolEmailConfig(school_slug=slug)
        db.session.add(row)

    row.smtp_host = host
    row.smtp_port = port
    row.smtp_use_tls = use_tls
    row.smtp_username = username
    if password:
        row.smtp_password = password
    row.from_email = from_email
    row.from_name = from_name
    row.is_active = bool(data.get("is_active", True))

    db.session.commit()
    return success_response(data=row.to_dict(), message="Email config saved")
