from flask import Blueprint, request
from flask_jwt_extended import get_jwt
from app.services.parent_portal_service import ParentPortalService, LeaveService, NotificationService
from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required

parent_portal_bp = Blueprint('parent_portal', __name__, url_prefix='/api/v1/parent-portal')


@parent_portal_bp.route('/dashboard', methods=['GET'])
@roles_required('parent')
def dashboard():
    parent_id = get_jwt().get('parent_id')
    if not parent_id:
        return error_response("Parent profile not linked to this account", status=403)
    data = ParentPortalService.get_dashboard(parent_id)
    return success_response(data=data, message="Dashboard loaded")


@parent_portal_bp.route('/children', methods=['GET'])
@roles_required('parent')
def list_children():
    parent_id = get_jwt().get('parent_id')
    children = ParentPortalService.get_children(parent_id)
    return success_response(data={'children': children}, message="Children retrieved")


@parent_portal_bp.route('/children/<int:child_id>/attendance', methods=['GET'])
@roles_required('parent')
def child_attendance(child_id):
    parent_id = get_jwt().get('parent_id')
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    data = ParentPortalService.get_child_attendance(parent_id, child_id, month, year)
    return success_response(data=data, message="Attendance retrieved")


@parent_portal_bp.route('/children/<int:child_id>/grades', methods=['GET'])
@roles_required('parent')
def child_grades(child_id):
    parent_id = get_jwt().get('parent_id')
    data = ParentPortalService.get_child_grades(parent_id, child_id)
    return success_response(data=data, message="Grades retrieved")


@parent_portal_bp.route('/children/<int:child_id>/fees', methods=['GET'])
@roles_required('parent')
def child_fees(child_id):
    parent_id = get_jwt().get('parent_id')
    data = ParentPortalService.get_child_fees(parent_id, child_id)
    return success_response(data=data, message="Fee records retrieved")


# ---------------------------------------------------------------------------
# Leave Applications
# ---------------------------------------------------------------------------
leave_bp = Blueprint('leave', __name__, url_prefix='/api/v1/leave-applications')


@leave_bp.route('', methods=['GET'])
@roles_required('parent')
def list_leaves():
    parent_id = get_jwt().get('parent_id')
    leaves = LeaveService.get_by_parent(parent_id)
    return success_response(data={'leaves': leaves}, message="Leave applications retrieved")


@leave_bp.route('', methods=['POST'])
@roles_required('parent')
def submit_leave():
    parent_id = get_jwt().get('parent_id')
    data = request.get_json()
    if not data:
        return error_response("Request body required", status=400)
    leave, err = LeaveService.submit(parent_id, data)
    if err:
        return error_response(err['message'], status=err.get('status', 400))
    return success_response(data=leave, message="Leave application submitted", status=201)


@leave_bp.route('/<int:leave_id>/review', methods=['PUT'])
@roles_required('admin', 'teacher')
def review_leave(leave_id):
    data = request.get_json()
    reviewer_id = get_jwt().get('user_id')
    leave, err = LeaveService.review(leave_id, reviewer_id, data.get('status'), data.get('remarks'))
    if err:
        return error_response(err['message'], status=err.get('status', 400))
    return success_response(data=leave, message=f"Leave {data.get('status')}")


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
notifications_bp = Blueprint('notifications', __name__, url_prefix='/api/v1/notifications')


@notifications_bp.route('', methods=['GET'])
@roles_required('admin', 'teacher', 'student', 'parent')
def list_notifications():
    user_id = get_jwt().get('user_id')
    unread_only = request.args.get('unread', 'false').lower() == 'true'
    notifications = NotificationService.get_for_user(user_id, unread_only)
    return success_response(data={'notifications': notifications}, message="Notifications retrieved")


@notifications_bp.route('/<int:notification_id>/read', methods=['PUT'])
@roles_required('admin', 'teacher', 'student', 'parent')
def mark_read(notification_id):
    user_id = get_jwt().get('user_id')
    ok = NotificationService.mark_read(notification_id, user_id)
    if not ok:
        return error_response("Notification not found", status=404)
    return success_response(message="Notification marked as read")
