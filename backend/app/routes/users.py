from flask import Blueprint, request

from app.services.user_service import UserService
from app.utils.decorators import roles_required
from app.utils.response import success_response, error_response

users_bp = Blueprint("users", __name__, url_prefix="/api/v1/users")


@users_bp.route("", methods=["GET"])
@roles_required("admin")
def list_users():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    role = request.args.get("role")
    search = request.args.get("q")
    is_active_param = request.args.get("is_active")

    is_active = None
    if is_active_param is not None:
        is_active = is_active_param.lower() == "true"

    result = UserService.get_all(page=page, per_page=per_page, role=role, search=search, is_active=is_active)
    return success_response(
        data={"users": result["data"], "meta": result["meta"]},
        message="Users retrieved successfully",
    )


@users_bp.route("", methods=["POST"])
@roles_required("admin")
def create_user():
    data = request.get_json()
    if not data:
        return error_response("Request body is required", status=400)

    user = UserService.create_user(data)
    return success_response(data={"user": user.to_dict()}, message="User created successfully", status=201)


@users_bp.route("/<int:user_id>", methods=["GET"])
@roles_required("admin")
def get_user(user_id):
    user = UserService.get_by_id(user_id)
    return success_response(data=user.to_dict(), message="User retrieved successfully")


@users_bp.route("/<int:user_id>", methods=["PATCH"])
@roles_required("admin")
def update_user(user_id):
    data = request.get_json()
    if not data:
        return error_response("Request body is required", status=400)

    user = UserService.update_user(user_id, data)
    return success_response(data={"user": user.to_dict()}, message="User updated successfully")


@users_bp.route("/<int:user_id>/activate", methods=["PATCH"])
@roles_required("admin")
def activate_user(user_id):
    user = UserService.reactivate(user_id)
    return success_response(data={"user": user.to_dict()}, message="User activated successfully")


@users_bp.route("/<int:user_id>", methods=["DELETE"])
@roles_required("admin")
def deactivate_user(user_id):
    from flask_jwt_extended import get_jwt

    requesting_user_id = get_jwt().get("user_id")
    user = UserService.deactivate(user_id, requesting_user_id)
    return success_response(data=user.to_dict(), message="User deactivated successfully")
