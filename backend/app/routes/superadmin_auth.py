import logging

from flask import Blueprint, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt,
    get_jwt_identity,
)

from app import db, bcrypt, limiter
from app.models.master.super_admin import SuperAdmin
from app.models.master.super_admin_revoked_token import SuperAdminRevokedToken
from app.utils.response import success_response, error_response

logger = logging.getLogger(__name__)

superadmin_auth_bp = Blueprint(
    'superadmin_auth', __name__, url_prefix='/api/v1/superadmin/auth'
)


def _build_sa_claims(super_admin):
    """Return additional JWT claims for a super admin."""
    return {
        'role': 'super_admin',
        'super_admin_id': super_admin.id,
    }


def _identity_for(super_admin):
    """JWT identity string — prefixed to avoid collision with school user IDs."""
    return f'sa:{super_admin.id}'


# ---------------------------------------------------------------------------
# ERP-002 — Super Admin Login
# ---------------------------------------------------------------------------

@superadmin_auth_bp.route('/login', methods=['POST'])
@limiter.limit("5/minute")
def sa_login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return error_response("Email and password are required", status=400)

    super_admin = SuperAdmin.query.filter_by(
        email=data['email'].lower().strip()
    ).first()

    if not super_admin or not super_admin.is_active:
        return error_response("Invalid email or password", status=401)

    if not bcrypt.check_password_hash(super_admin.password_hash, data['password']):
        return error_response("Invalid email or password", status=401)

    identity = _identity_for(super_admin)
    claims = _build_sa_claims(super_admin)
    access_token = create_access_token(identity=identity, additional_claims=claims)
    refresh_token = create_refresh_token(identity=identity, additional_claims=claims)

    return success_response(
        data={
            'access_token': access_token,
            'refresh_token': refresh_token,
            'super_admin': super_admin.to_dict(),
        },
        message="Login successful",
    )


# ---------------------------------------------------------------------------
# ERP-002 — Token Refresh
# ---------------------------------------------------------------------------

@superadmin_auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
@limiter.limit("10/minute")
def sa_refresh():
    identity = get_jwt_identity()

    # Guard: only super admin refresh tokens should hit this endpoint
    if not identity or not identity.startswith('sa:'):
        return error_response("Invalid token for this endpoint", status=401)

    try:
        sa_id = int(identity.split(':', 1)[1])
    except (IndexError, ValueError):
        return error_response("Malformed token identity", status=401)

    super_admin = db.session.get(SuperAdmin, sa_id)
    if not super_admin or not super_admin.is_active:
        return error_response("Super admin not found or inactive", status=401)

    claims = _build_sa_claims(super_admin)
    access_token = create_access_token(identity=identity, additional_claims=claims)

    return success_response(
        data={'access_token': access_token},
        message="Token refreshed",
    )


# ---------------------------------------------------------------------------
# ERP-002 — Logout (revoke current token)
# ---------------------------------------------------------------------------

@superadmin_auth_bp.route('/logout', methods=['DELETE'])
@jwt_required()
def sa_logout():
    jwt_payload = get_jwt()

    # Only allow super admin tokens to use this logout endpoint
    if jwt_payload.get('role') != 'super_admin':
        return error_response("Forbidden", status=403)

    jti = jwt_payload['jti']
    revoked = SuperAdminRevokedToken(jti=jti)
    db.session.add(revoked)
    db.session.commit()

    return success_response(message="Logged out successfully")


# ---------------------------------------------------------------------------
# ERP-002 — Me (current super admin profile)
# ---------------------------------------------------------------------------

@superadmin_auth_bp.route('/me', methods=['GET'])
@jwt_required()
def sa_me():
    jwt_payload = get_jwt()

    if jwt_payload.get('role') != 'super_admin':
        return error_response("Forbidden", status=403)

    sa_id = jwt_payload.get('super_admin_id')
    if not sa_id:
        return error_response("Malformed token: missing super_admin_id", status=401)

    super_admin = db.session.get(SuperAdmin, sa_id)
    if not super_admin or not super_admin.is_active:
        return error_response("Super admin not found or inactive", status=404)

    return success_response(
        data=super_admin.to_dict(),
        message="Super admin profile retrieved",
    )
