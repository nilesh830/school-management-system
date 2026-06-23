from flask import Blueprint, request
from flask_jwt_extended import get_jwt

from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required
from app.services.teacher_service import TeacherService

teachers_bp = Blueprint("teachers", __name__, url_prefix="/api/v1/teachers")


# ---------------------------------------------------------------------------
# Teacher CRUD
# ---------------------------------------------------------------------------


@teachers_bp.route("/", methods=["GET"], strict_slashes=False)
@roles_required("admin", "teacher")
def list_teachers():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "", type=str)
    result = TeacherService.get_all(page=page, per_page=per_page, search=search)
    return success_response(data=result, message="Teachers retrieved")


@teachers_bp.route("/<int:teacher_id>", methods=["GET"])
@roles_required("admin", "teacher")
def get_teacher(teacher_id):
    teacher = TeacherService.get_by_id(teacher_id)
    if not teacher:
        return error_response("Teacher not found", status=404)
    return success_response(data=teacher, message="Teacher retrieved")


@teachers_bp.route("/", methods=["POST"], strict_slashes=False)
@roles_required("admin")
def create_teacher():
    data = request.get_json(silent=True) or {}
    result, err = TeacherService.create(data)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(data=result, message="Teacher created", status=201)


@teachers_bp.route("/<int:teacher_id>", methods=["PUT"])
@roles_required("admin")
def update_teacher(teacher_id):
    data = request.get_json(silent=True) or {}
    result, err = TeacherService.update(teacher_id, data)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(data=result, message="Teacher updated")


@teachers_bp.route("/<int:teacher_id>", methods=["DELETE"])
@roles_required("admin")
def delete_teacher(teacher_id):
    ok, err = TeacherService.delete(teacher_id)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(message="Teacher deleted")


# ---------------------------------------------------------------------------
# Subject assignments
# ---------------------------------------------------------------------------


@teachers_bp.route("/<int:teacher_id>/subjects", methods=["GET"])
@roles_required("admin", "teacher")
def get_teacher_subjects(teacher_id):
    subjects, err = TeacherService.get_subjects(teacher_id)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(data={"subjects": subjects}, message="Teacher subjects retrieved")


@teachers_bp.route("/<int:teacher_id>/subjects", methods=["POST"])
@roles_required("admin")
def assign_subject(teacher_id):
    """Body: {subject_id, class_id (optional), academic_year_id (optional)}"""
    data = request.get_json(silent=True) or {}
    subject_id = data.get("subject_id")
    if not subject_id:
        return error_response("subject_id is required", status=400)

    result, err = TeacherService.assign_subject(
        teacher_id=teacher_id,
        subject_id=subject_id,
        class_id=data.get("class_id"),
        academic_year_id=data.get("academic_year_id"),
    )
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(data=result, message="Subject assigned to teacher", status=201)


@teachers_bp.route("/<int:teacher_id>/subjects/<int:subject_id>", methods=["DELETE"])
@roles_required("admin")
def unassign_subject(teacher_id, subject_id):
    """Query param: ?class_id= (optional) to scope the removal."""
    class_id = request.args.get("class_id", type=int)
    ok, err = TeacherService.unassign_subject(teacher_id=teacher_id, subject_id=subject_id, class_id=class_id)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(message="Subject unassigned from teacher")


# ---------------------------------------------------------------------------
# Documents (multipart upload)
# ---------------------------------------------------------------------------


@teachers_bp.route("/<int:teacher_id>/documents", methods=["POST"])
@roles_required("admin")
def upload_document(teacher_id):
    """
    Multipart form upload.
    Form fields: document_type (required)
    File field: file
    """
    document_type = request.form.get("document_type", "").strip()
    if not document_type:
        return error_response("document_type is required", status=400)

    file = request.files.get("file")
    if not file:
        return error_response("file is required", status=400)

    claims = get_jwt()
    uploaded_by = claims.get("sub")
    try:
        uploaded_by = int(uploaded_by)
    except (TypeError, ValueError):
        uploaded_by = 1

    result, err = TeacherService.upload_document(
        teacher_id=teacher_id,
        document_type=document_type,
        file=file,
        uploaded_by=uploaded_by,
    )
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(data=result, message="Document uploaded", status=201)


@teachers_bp.route("/<int:teacher_id>/documents", methods=["GET"])
@roles_required("admin", "teacher")
def list_documents(teacher_id):
    docs, err = TeacherService.list_documents(teacher_id)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(data={"documents": docs}, message="Teacher documents retrieved")


@teachers_bp.route("/<int:teacher_id>/documents/<int:doc_id>", methods=["DELETE"])
@roles_required("admin")
def delete_document(teacher_id, doc_id):
    ok, err = TeacherService.delete_document(teacher_id=teacher_id, doc_id=doc_id)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(message="Document deleted")


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------


@teachers_bp.route("/<int:teacher_id>/schedule", methods=["GET"])
@roles_required("admin", "teacher")
def get_schedule(teacher_id):
    """Query param: ?academic_year_id= (optional)"""
    academic_year_id = request.args.get("academic_year_id", type=int)
    schedule, err = TeacherService.get_schedule(teacher_id=teacher_id, academic_year_id=academic_year_id)
    if err:
        return error_response(err["message"], status=err["status"])
    return success_response(data={"schedule": schedule}, message="Teacher schedule retrieved")
