from flask import Blueprint, request
from flask_jwt_extended import get_jwt
from app.services.parent_portal_service import (
    ParentPortalService,
    LeaveService,
    NotificationService,
    MessageService,
    ParentProfileService,
)
from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required

parent_portal_bp = Blueprint("parent_portal", __name__, url_prefix="/api/v1/parent-portal")


@parent_portal_bp.route("/dashboard", methods=["GET"])
@roles_required("parent")
def dashboard():
    parent_id = get_jwt().get("parent_id")
    if not parent_id:
        return error_response("Parent profile not linked to this account", status=403)
    data = ParentPortalService.get_dashboard(parent_id)
    return success_response(data=data, message="Dashboard loaded")


@parent_portal_bp.route("/children", methods=["GET"])
@roles_required("parent")
def list_children():
    parent_id = get_jwt().get("parent_id")
    children = ParentPortalService.get_children(parent_id)
    return success_response(data={"children": children}, message="Children retrieved")


@parent_portal_bp.route("/children/<int:child_id>/attendance", methods=["GET"])
@roles_required("parent")
def child_attendance(child_id):
    parent_id = get_jwt().get("parent_id")
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)
    data = ParentPortalService.get_child_attendance(parent_id, child_id, month, year)
    return success_response(data=data, message="Attendance retrieved")


@parent_portal_bp.route("/children/<int:child_id>/grades", methods=["GET"])
@roles_required("parent")
def child_grades(child_id):
    parent_id = get_jwt().get("parent_id")
    data = ParentPortalService.get_child_grades(parent_id, child_id)
    return success_response(data=data, message="Grades retrieved")


@parent_portal_bp.route("/children/<int:child_id>/fees", methods=["GET"])
@roles_required("parent")
def child_fees(child_id):
    parent_id = get_jwt().get("parent_id")
    data = ParentPortalService.get_child_fees(parent_id, child_id)
    return success_response(data=data, message="Fee records retrieved")


# ---------------------------------------------------------------------------
# SMS-045: School Notice Board (Parent View)
# ---------------------------------------------------------------------------


@parent_portal_bp.route("/notices", methods=["GET"])
@roles_required("parent")
def list_notices():
    parent_id = get_jwt().get("parent_id")
    if not parent_id:
        return error_response("Parent profile not linked to this account", status=403)
    notices = ParentPortalService.get_notices(parent_id)
    return success_response(data={"notices": notices}, message="Notices retrieved")


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


@parent_portal_bp.route("/messages/threads", methods=["GET"])
@roles_required("parent", "teacher")
def list_threads():
    claims = get_jwt()
    user_id = claims.get("user_id")
    role = claims.get("role")
    threads = MessageService.list_threads(user_id, role)
    return success_response(data={"threads": threads}, message="Threads retrieved")


@parent_portal_bp.route("/messages/threads", methods=["POST"])
@roles_required("parent")
def create_thread():
    parent_id = get_jwt().get("parent_id")
    data = request.get_json() or {}
    child_id = data.get("student_id")
    subject = data.get("subject")
    first_message = data.get("message")
    if not all([child_id, subject, first_message]):
        return error_response("student_id, subject, and message are required", status=400)
    thread, err = MessageService.create_thread(parent_id, child_id, subject, first_message)
    if err:
        return error_response(err["message"], status=err.get("status", 400))
    return success_response(data=thread, message="Thread created", status=201)


@parent_portal_bp.route("/messages/threads/<string:thread_id>", methods=["GET"])
@roles_required("parent", "teacher")
def get_thread(thread_id):
    claims = get_jwt()
    user_id = claims.get("user_id")
    role = claims.get("role")
    thread = MessageService.get_thread(thread_id, user_id, role)
    if thread is None:
        return error_response("Thread not found or access denied", status=404)
    return success_response(data=thread, message="Thread retrieved")


@parent_portal_bp.route("/messages/threads/<string:thread_id>/reply", methods=["POST"])
@roles_required("parent", "teacher")
def reply_to_thread(thread_id):
    claims = get_jwt()
    user_id = claims.get("user_id")
    role = claims.get("role")
    data = request.get_json() or {}
    body = data.get("message")
    if not body:
        return error_response("message is required", status=400)
    msg, err = MessageService.reply(thread_id, user_id, body, role)
    if err:
        return error_response(err["message"], status=err.get("status", 400))
    return success_response(data=msg, message="Reply sent", status=201)


@parent_portal_bp.route("/messages/threads/<string:thread_id>/read", methods=["PUT"])
@roles_required("parent", "teacher")
def mark_thread_read(thread_id):
    user_id = get_jwt().get("user_id")
    MessageService.mark_thread_read(thread_id, user_id)
    return success_response(message="Thread marked as read")


# ---------------------------------------------------------------------------
# Leave Applications
# ---------------------------------------------------------------------------
leave_bp = Blueprint("leave", __name__, url_prefix="/api/v1/leave-applications")


@leave_bp.route("", methods=["GET"])
@roles_required("parent")
def list_leaves():
    parent_id = get_jwt().get("parent_id")
    leaves = LeaveService.get_by_parent(parent_id)
    return success_response(data={"leaves": leaves}, message="Leave applications retrieved")


@leave_bp.route("", methods=["POST"])
@roles_required("parent")
def submit_leave():
    parent_id = get_jwt().get("parent_id")
    data = request.get_json()
    if not data:
        return error_response("Request body required", status=400)
    leave, err = LeaveService.submit(parent_id, data)
    if err:
        return error_response(err["message"], status=err.get("status", 400))
    return success_response(data=leave, message="Leave application submitted", status=201)


@leave_bp.route("/<int:leave_id>/review", methods=["PUT"])
@roles_required("admin", "teacher")
def review_leave(leave_id):
    data = request.get_json()
    reviewer_id = get_jwt().get("user_id")
    leave, err = LeaveService.review(leave_id, reviewer_id, data.get("status"), data.get("remarks"))
    if err:
        return error_response(err["message"], status=err.get("status", 400))
    return success_response(data=leave, message=f"Leave {data.get('status')}")


@leave_bp.route("/all", methods=["GET"])
@roles_required("admin", "teacher")
def list_all_leaves():
    status_filter = request.args.get("status")
    leaves = LeaveService.get_all(status_filter)
    return success_response(data={"leaves": leaves}, message="All leave applications retrieved")


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/v1/notifications")


@notifications_bp.route("", methods=["GET"])
@roles_required("admin", "teacher", "student", "parent")
def list_notifications():
    user_id = get_jwt().get("user_id")
    unread_only = request.args.get("unread", "false").lower() == "true"
    notifications = NotificationService.get_for_user(user_id, unread_only)
    return success_response(data={"notifications": notifications}, message="Notifications retrieved")


@notifications_bp.route("/<int:notification_id>/read", methods=["PUT"])
@roles_required("admin", "teacher", "student", "parent")
def mark_read(notification_id):
    user_id = get_jwt().get("user_id")
    ok = NotificationService.mark_read(notification_id, user_id)
    if not ok:
        return error_response("Notification not found", status=404)
    return success_response(message="Notification marked as read")


@notifications_bp.route("/read-all", methods=["PUT"])
@roles_required("admin", "teacher", "student", "parent")
def mark_all_read():
    user_id = get_jwt().get("user_id")
    count = NotificationService.mark_all_read(user_id)
    return success_response(message=f"{count} notifications marked as read")


# ---------------------------------------------------------------------------
# Parent Profile
# ---------------------------------------------------------------------------
parents_bp = Blueprint("parents_profile", __name__, url_prefix="/api/v1/parents")


@parents_bp.route("/me", methods=["GET"])
@roles_required("parent")
def get_my_profile():
    user_id = get_jwt().get("user_id")
    profile = ParentProfileService.get_me(user_id)
    if not profile:
        return error_response("Parent profile not found", status=404)
    return success_response(data=profile, message="Profile retrieved")


@parents_bp.route("/me", methods=["PATCH"])
@roles_required("parent")
def update_my_profile():
    user_id = get_jwt().get("user_id")
    data = request.get_json() or {}
    profile, err = ParentProfileService.update_me(user_id, data)
    if err:
        return error_response(err["message"], status=err.get("status", 400))
    return success_response(data=profile, message="Profile updated")
