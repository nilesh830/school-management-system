from flask import Blueprint, request
from flask_jwt_extended import get_jwt

from app.services.library_service import LibraryService
from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required
from app.schemas.library_schema import (
    BookCreateSchema,
    BookUpdateSchema,
    BookIssueSchema,
    BookReturnSchema,
)

library_bp = Blueprint("library", __name__, url_prefix="/api/v1/library")

_create_schema = BookCreateSchema()
_update_schema = BookUpdateSchema()
_issue_schema = BookIssueSchema()
_return_schema = BookReturnSchema()


def _validate(schema, payload):
    errors = schema.validate(payload or {})
    if errors:
        return None, error_response("Validation failed", errors=errors, status=422)
    return schema.load(payload), None


# ---------------------------------------------------------------------------
# Book catalog (SMS-053)
# ---------------------------------------------------------------------------


@library_bp.route("/books", methods=["POST"], strict_slashes=False)
@roles_required("admin")
def create_book():
    data, err = _validate(_create_schema, request.get_json())
    if err:
        return err
    result, svc_err = LibraryService.create_book(data)
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 400))
    return success_response(data=result, message="Book added", status=201)


@library_bp.route("/books", methods=["GET"], strict_slashes=False)
@roles_required("admin", "teacher")
def list_books():
    search = request.args.get("search")
    books = LibraryService.get_books(search=search)
    return success_response(data={"books": books}, message="Books retrieved")


@library_bp.route("/books/<int:book_id>", methods=["GET"], strict_slashes=False)
@roles_required("admin", "teacher")
def get_book(book_id):
    result, svc_err = LibraryService.get_book(book_id)
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 404))
    return success_response(data=result, message="Book retrieved")


@library_bp.route("/books/<int:book_id>", methods=["PUT"], strict_slashes=False)
@roles_required("admin")
def update_book(book_id):
    data, err = _validate(_update_schema, request.get_json())
    if err:
        return err
    result, svc_err = LibraryService.update_book(book_id, data)
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 400))
    return success_response(data=result, message="Book updated")


@library_bp.route("/books/<int:book_id>", methods=["DELETE"], strict_slashes=False)
@roles_required("admin")
def delete_book(book_id):
    result, svc_err = LibraryService.delete_book(book_id)
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 400))
    return success_response(data=result, message="Book deleted")


# ---------------------------------------------------------------------------
# Issue / Return (SMS-054)
# ---------------------------------------------------------------------------


@library_bp.route("/issue", methods=["POST"], strict_slashes=False)
@roles_required("admin", "teacher")
def issue_book():
    user_id = get_jwt().get("user_id")
    data, err = _validate(_issue_schema, request.get_json())
    if err:
        return err
    result, svc_err = LibraryService.issue_book(
        book_id=data["book_id"],
        student_id=data["student_id"],
        due_date=data["due_date"],
        issued_by=user_id,
    )
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 400))
    return success_response(data=result, message="Book issued", status=201)


@library_bp.route("/issues", methods=["GET"], strict_slashes=False)
@roles_required("admin", "teacher")
def list_issues():
    status = request.args.get("status")
    student_id = request.args.get("student_id", type=int)
    issues = LibraryService.get_issues(status=status, student_id=student_id)
    return success_response(data={"issues": issues}, message="Issues retrieved")


@library_bp.route("/issue/<int:issue_id>/return", methods=["PUT"], strict_slashes=False)
@roles_required("admin", "teacher")
def return_book(issue_id):
    data, err = _validate(_return_schema, request.get_json())
    if err:
        return err
    result, svc_err = LibraryService.return_book(issue_id, data.get("returned_date"))
    if svc_err:
        return error_response(svc_err["message"], status=svc_err.get("status", 400))
    return success_response(data=result, message="Book returned")


# ---------------------------------------------------------------------------
# Overdue (SMS-055)
# ---------------------------------------------------------------------------


@library_bp.route("/overdue", methods=["GET"], strict_slashes=False)
@roles_required("admin", "teacher")
def list_overdue():
    LibraryService.mark_overdue()
    overdue = LibraryService.get_overdue()
    return success_response(data={"overdue": overdue}, message="Overdue issues retrieved")
