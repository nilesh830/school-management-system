from flask import Blueprint, request
from flask_jwt_extended import get_jwt

from app.services.announcement_service import AnnouncementService
from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required
from app.schemas.announcement_schema import AnnouncementCreateSchema, AnnouncementUpdateSchema

announcements_bp = Blueprint("announcements", __name__, url_prefix="/api/v1/announcements")

_create_schema = AnnouncementCreateSchema()
_update_schema = AnnouncementUpdateSchema()


def _validate(schema, payload):
    errors = schema.validate(payload or {})
    if errors:
        return None, error_response("Validation failed", errors=errors, status=422)
    return schema.load(payload), None


# ---------------------------------------------------------------------------
# POST /api/v1/announcements — create (admin)
# ---------------------------------------------------------------------------


@announcements_bp.route("", methods=["POST"], strict_slashes=False)
@roles_required("admin")
def create_announcement():
    user_id = get_jwt().get("user_id")
    data, err = _validate(_create_schema, request.get_json())
    if err:
        return err
    result, svc_err = AnnouncementService.create(data, created_by=user_id)
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 400))
    return success_response(data=result, message="Announcement created", status=201)


# ---------------------------------------------------------------------------
# GET /api/v1/announcements
#   - admin: all announcements
#   - ?role_view=true (any role): only notices relevant to the current user
# ---------------------------------------------------------------------------


@announcements_bp.route("", methods=["GET"], strict_slashes=False)
@roles_required("admin", "teacher", "student", "parent")
def list_announcements():
    claims = get_jwt()
    role = claims.get("role")
    role_view = request.args.get("role_view", "false").lower() == "true"

    if role == "admin" and not role_view:
        return success_response(
            data={"announcements": AnnouncementService.get_all()},
            message="Announcements retrieved",
        )

    class_ids = _resolve_class_ids(claims)
    notices = AnnouncementService.get_for_user(role, class_ids)
    return success_response(data={"announcements": notices}, message="Announcements retrieved")


# ---------------------------------------------------------------------------
# GET /api/v1/announcements/<id> — single (admin)
# ---------------------------------------------------------------------------


@announcements_bp.route("/<int:announcement_id>", methods=["GET"], strict_slashes=False)
@roles_required("admin")
def get_announcement(announcement_id):
    result, svc_err = AnnouncementService.get_by_id(announcement_id)
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 404))
    return success_response(data=result, message="Announcement retrieved")


# ---------------------------------------------------------------------------
# PUT /api/v1/announcements/<id> — update (admin)
# ---------------------------------------------------------------------------


@announcements_bp.route("/<int:announcement_id>", methods=["PUT"], strict_slashes=False)
@roles_required("admin")
def update_announcement(announcement_id):
    data, err = _validate(_update_schema, request.get_json())
    if err:
        return err
    result, svc_err = AnnouncementService.update(announcement_id, data)
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 400))
    return success_response(data=result, message="Announcement updated")


# ---------------------------------------------------------------------------
# POST /api/v1/announcements/<id>/publish — publish draft + dispatch (admin)
# ---------------------------------------------------------------------------


@announcements_bp.route("/<int:announcement_id>/publish", methods=["POST"], strict_slashes=False)
@roles_required("admin")
def publish_announcement(announcement_id):
    result, svc_err = AnnouncementService.publish(announcement_id)
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 400))
    return success_response(data=result, message="Announcement published")


# ----------------------------------------------------- internal helper


def _resolve_class_ids(claims):
    """Resolve the class_ids relevant to the current (non-admin) user."""
    from app.utils.tenant import get_db
    from app.models.student import Student

    role = claims.get("role")
    user_id = claims.get("user_id")
    db = get_db()

    if role == "student":
        student = db.query(Student).filter_by(user_id=user_id, is_active=True).first()
        if not student:
            return []
        return list(AnnouncementService._student_class_ids([student.id]))

    if role == "parent":
        parent_id = claims.get("parent_id")
        if not parent_id:
            return []
        from app.models.parent import Parent

        parent = db.query(Parent).filter_by(id=parent_id).first()
        if not parent:
            return []
        student_ids = [s.id for s in parent.students]
        return list(AnnouncementService._student_class_ids(student_ids))

    return []
