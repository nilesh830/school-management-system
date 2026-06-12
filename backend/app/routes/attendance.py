from flask import Blueprint, request
from flask_jwt_extended import get_jwt, get_jwt_identity

from app.services.attendance_service import AttendanceService
from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required
from app.utils.tenant import get_db
from app.schemas.attendance_schema import AttendanceMarkSchema

attendance_bp = Blueprint('attendance', __name__, url_prefix='/api/v1/attendance')

_mark_schema = AttendanceMarkSchema()


def _validate(schema, payload):
    errors = schema.validate(payload or {})
    if errors:
        return None, error_response('Validation failed', errors=errors, status=422)
    return schema.load(payload), None


# ---------------------------------------------------------------------------
# POST /api/v1/attendance/mark — mark daily attendance (teacher / admin)
# ---------------------------------------------------------------------------

@attendance_bp.route('/mark', methods=['POST'], strict_slashes=False)
@roles_required('admin', 'teacher')
def mark_attendance():
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())

    data, err = _validate(_mark_schema, request.get_json())
    if err:
        return err

    section_id = data['section_id']
    date_str = str(data['date'])
    records = [{'student_id': r['student_id'], 'status': r['status']} for r in data['records']]

    # Teachers may only mark attendance for sections they are class teacher of
    if role == 'teacher':
        from app.models.teacher import Teacher
        from app.models.section import Section
        teacher = get_db().query(Teacher).filter_by(user_id=user_id, is_active=True).first()
        if not teacher:
            return error_response('Teacher profile not found', status=403)
        section = get_db().query(Section).filter_by(id=section_id, is_active=True).first()
        if not section:
            return error_response('Section not found', status=404)
        if section.class_teacher_id != teacher.id:
            return error_response(
                'You are not the class teacher for this section', status=403
            )

    result, svc_err = AttendanceService.mark_attendance(
        section_id=section_id,
        date_str=date_str,
        records=records,
        marked_by_user_id=user_id,
    )
    if svc_err:
        return error_response(svc_err['message'], status=svc_err.get('status', 400))
    return success_response(data=result, message='Attendance marked successfully', status=201)


# ---------------------------------------------------------------------------
# GET /api/v1/attendance — view attendance for a student (?student_id, month, year)
# ---------------------------------------------------------------------------

@attendance_bp.route('', methods=['GET'], strict_slashes=False)
@roles_required('admin', 'teacher', 'student', 'parent')
def get_attendance():
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())

    student_id = request.args.get('student_id', type=int)
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)

    if not student_id or not month or not year:
        return error_response('student_id, month and year are required', status=400)

    # Students may only view their own attendance
    if role == 'student':
        from app.models.student import Student
        student = get_db().query(Student).filter_by(user_id=user_id, is_active=True).first()
        if not student or student.id != student_id:
            return error_response('Access denied', status=403)

    # Parents may only view attendance for their own children
    if role == 'parent':
        from app.models.parent import Parent, student_parent
        from sqlalchemy import select
        parent = get_db().query(Parent).filter_by(user_id=user_id, is_active=True).first()
        if not parent:
            return error_response('Parent profile not found', status=403)
        link = get_db().execute(
            select(student_parent).where(
                student_parent.c.parent_id == parent.id,
                student_parent.c.student_id == student_id,
            )
        ).first()
        if not link:
            return error_response('Access denied', status=403)

    rows = AttendanceService.get_for_student(student_id, month, year)
    return success_response(data={'attendance': rows}, message='Attendance retrieved')


# ---------------------------------------------------------------------------
# GET /api/v1/attendance/report — section report for a date range
# ---------------------------------------------------------------------------

@attendance_bp.route('/report', methods=['GET'], strict_slashes=False)
@roles_required('admin', 'teacher')
def get_report():
    section_id = request.args.get('section_id', type=int)
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    if not section_id or not from_date or not to_date:
        return error_response('section_id, from_date and to_date are required', status=400)

    result = AttendanceService.get_report(section_id, from_date, to_date)
    return success_response(data=result, message='Attendance report retrieved')


# ---------------------------------------------------------------------------
# GET /api/v1/attendance/today-summary — admin dashboard widget
# ---------------------------------------------------------------------------

@attendance_bp.route('/today-summary', methods=['GET'], strict_slashes=False)
@roles_required('admin')
def get_today_summary():
    summary = AttendanceService.get_today_summary()
    return success_response(data=summary, message='Today summary retrieved')
