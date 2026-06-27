from flask import Blueprint, request
from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required
from app.services.timetable_service import TimetableService

timetables_bp = Blueprint("timetables", __name__, url_prefix="/api/v1/timetables")


@timetables_bp.route("/", methods=["GET"], strict_slashes=False)
@roles_required("admin", "teacher")
def list_timetables():
    """
    Filter by ?section_id= or ?teacher_id= (one must be provided).
    Returns entries ordered by day_of_week then period_no.
    """
    section_id = request.args.get("section_id", type=int)
    teacher_id = request.args.get("teacher_id", type=int)

    if section_id:
        entries = TimetableService.get_by_section(section_id)
    elif teacher_id:
        entries = TimetableService.get_by_teacher(teacher_id)
    else:
        return error_response("Provide ?section_id= or ?teacher_id= query parameter", status=400)

    return success_response(data={"timetable": entries}, message="Timetable retrieved")


@timetables_bp.route("/", methods=["POST"], strict_slashes=False)
@roles_required("admin")
def create_timetable_entry():
    data = request.get_json(silent=True) or {}
    result, err = TimetableService.create(data)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(data=result, message="Timetable entry created", status=201)


@timetables_bp.route("/<int:entry_id>", methods=["PUT"])
@roles_required("admin")
def update_timetable_entry(entry_id):
    data = request.get_json(silent=True) or {}
    result, err = TimetableService.update(entry_id, data)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(data=result, message="Timetable entry updated")


@timetables_bp.route("/<int:entry_id>", methods=["DELETE"])
@roles_required("admin")
def delete_timetable_entry(entry_id):
    ok, err = TimetableService.delete(entry_id)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(message="Timetable entry deleted")
