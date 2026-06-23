import os
import secrets
import hashlib
import logging
from datetime import datetime, timedelta

from flask import Blueprint, request, current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
)
from werkzeug.utils import secure_filename

from app import limiter
from app.models.user import User
from app.models.revoked_token import RevokedToken
from app.models.password_reset_token import PasswordResetToken
from app.utils.response import success_response, error_response
from app.utils.validators import validate_password
from app.utils.tenant import get_db

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def _allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def _build_additional_claims(user, school_slug: str):
    claims = {"role": user.role, "user_id": user.id, "school_slug": school_slug}
    if user.role == "parent" and user.parent:
        claims["parent_id"] = user.parent.id
    return claims


# ---------------------------------------------------------------------------
# SMS-001 — Login
# ---------------------------------------------------------------------------


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5/minute")
def login():
    data = request.get_json()
    if not data or not data.get("email") or not data.get("password") or not data.get("school_slug"):
        return error_response("Email, password, and school_slug are required", status=400)

    # Validate school exists and is active in master.db
    from app.models.master.school import School

    school_slug = data["school_slug"].lower().strip()
    school = School.query.filter_by(slug=school_slug, is_active=True).first()
    if not school:
        return error_response("School not found or inactive", status=404)

    user = get_db().query(User).filter_by(email=data["email"].lower().strip(), is_active=True).first()
    if not user or not user.check_password(data["password"]):
        return error_response("Invalid email or password", status=401)

    user.last_login = datetime.utcnow()
    get_db().commit()

    claims = _build_additional_claims(user, school_slug)
    access_token = create_access_token(identity=str(user.id), additional_claims=claims)
    refresh_token = create_refresh_token(identity=str(user.id), additional_claims=claims)

    return success_response(
        data={"access_token": access_token, "refresh_token": refresh_token, "user": user.to_dict()},
        message="Login successful",
    )


# ---------------------------------------------------------------------------
# SMS-002 — Token Refresh & Logout
# ---------------------------------------------------------------------------


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
@limiter.limit("10/minute")
def refresh():
    user_id = int(get_jwt_identity())
    current_claims = get_jwt()
    user = get_db().get(User, user_id)
    if not user or not user.is_active:
        return error_response("User not found or inactive", status=401)

    school_slug = current_claims.get("school_slug", "")
    claims = _build_additional_claims(user, school_slug)
    access_token = create_access_token(identity=str(user_id), additional_claims=claims)
    return success_response(data={"access_token": access_token}, message="Token refreshed")


@auth_bp.route("/logout", methods=["DELETE"])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    revoked = RevokedToken(jti=jti)
    get_db().add(revoked)
    get_db().commit()
    return success_response(message="Logged out successfully")


# ---------------------------------------------------------------------------
# SMS-001 — Me endpoint
# ---------------------------------------------------------------------------


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id_raw = get_jwt_identity()
    user = get_db().get(User, int(user_id_raw))
    if not user or not user.is_active:
        return error_response("User not found", status=404)
    return success_response(data=user.to_dict(), message="User profile retrieved")


# ---------------------------------------------------------------------------
# SMS-005 — Forgot Password & Reset Password
# ---------------------------------------------------------------------------


@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("3/minute")
def forgot_password():
    data = request.get_json()
    email = (data or {}).get("email", "").lower().strip()
    if not email:
        return error_response("Email is required", status=400)

    # Always return 200 — do not reveal whether the email exists
    user = get_db().query(User).filter_by(email=email, is_active=True).first()
    if user:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires = datetime.utcnow() + timedelta(hours=current_app.config.get("PASSWORD_RESET_EXPIRES_HOURS", 1))

        # Invalidate any existing tokens for this user
        get_db().query(PasswordResetToken).filter_by(user_id=user.id, is_used=False).update({"is_used": True})

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires,
        )
        get_db().add(reset_token)
        get_db().commit()

        frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:4200")
        reset_link = f"{frontend_url}/auth/reset-password?token={raw_token}"

        if current_app.config.get("MAIL_SUPPRESS_SEND", True):
            logger.info("PASSWORD RESET LINK (dev only): %s", reset_link)
        else:
            _send_reset_email(user.email, reset_link)

    return success_response(message="If that email exists, a reset link has been sent")


@auth_bp.route("/reset-password", methods=["POST"])
@limiter.limit("5/minute")
def reset_password():
    data = request.get_json()
    raw_token = (data or {}).get("token", "").strip()
    new_password = (data or {}).get("password", "")

    if not raw_token or not new_password:
        return error_response("Token and new password are required", status=400)

    pw_errors = validate_password(new_password)
    if pw_errors:
        return error_response("Password does not meet requirements", errors=pw_errors, status=422)

    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    reset_token = get_db().query(PasswordResetToken).filter_by(token_hash=token_hash, is_used=False).first()

    if not reset_token or not reset_token.is_valid:
        return error_response("Invalid or expired reset token", status=400)

    user = get_db().get(User, reset_token.user_id)
    if not user or not user.is_active:
        return error_response("User not found", status=404)

    user.set_password(new_password)
    reset_token.is_used = True
    get_db().commit()

    return success_response(message="Password reset successfully. Please log in with your new password.")


# ---------------------------------------------------------------------------
# SMS-006 — Profile Edit & Photo Upload
# ---------------------------------------------------------------------------


@auth_bp.route("/profile", methods=["PATCH"])
@jwt_required()
def update_profile():
    user_id = int(get_jwt_identity())
    user = get_db().get(User, user_id)
    if not user or not user.is_active:
        return error_response("User not found", status=404)

    data = request.get_json()
    if not data:
        return error_response("No data provided", status=400)

    allowed_fields = {"first_name", "last_name"}
    updated = {}
    for field in allowed_fields:
        if field in data and data[field] and data[field].strip():
            setattr(user, field, data[field].strip())
            updated[field] = data[field].strip()

    if not updated:
        return error_response("No valid fields to update", status=400)

    get_db().commit()
    return success_response(data=user.to_dict(), message="Profile updated successfully")


@auth_bp.route("/profile/photo", methods=["POST"])
@jwt_required()
def upload_profile_photo():
    user_id = int(get_jwt_identity())
    user = get_db().get(User, user_id)
    if not user or not user.is_active:
        return error_response("User not found", status=404)

    if "photo" not in request.files:
        return error_response("No photo file provided", status=400)

    file = request.files["photo"]
    if not file.filename:
        return error_response("No file selected", status=400)

    if not _allowed_image(file.filename):
        return error_response(f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}", status=400)

    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "profile_photos")
    os.makedirs(upload_dir, exist_ok=True)

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = secure_filename(f"user_{user_id}_{secrets.token_hex(8)}.{ext}")
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    user.photo_url = f"/uploads/profile_photos/{filename}"
    get_db().commit()

    return success_response(data={"photo_url": user.photo_url}, message="Profile photo uploaded successfully")


def _send_reset_email(email, reset_link):
    """Send password reset email. Requires Flask-Mail to be configured."""
    try:
        from flask_mail import Mail, Message

        mail = Mail(current_app)
        msg = Message(
            subject="SMS — Password Reset Request",
            recipients=[email],
            body=(
                f"You requested a password reset.\n\n"
                f"Click the link below to reset your password (valid for 1 hour):\n{reset_link}\n\n"
                f"If you did not request this, please ignore this email."
            ),
        )
        mail.send(msg)
    except Exception as exc:
        logger.error("Failed to send reset email to %s: %s", email, exc)
