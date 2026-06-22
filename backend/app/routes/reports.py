from flask import Blueprint, request, make_response

from app.services.report_service import ReportService
from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required

reports_bp = Blueprint('reports', __name__, url_prefix='/api/v1/reports')

# SMS-060 — export format constants
_PDF_MIMETYPE = 'application/pdf'
_XLSX_MIMETYPE = (
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
)
_VALID_FORMATS = ('pdf', 'excel')


def _file_response(content: bytes, mimetype: str, filename: str):
    """Build an attachment download response for binary report exports."""
    response = make_response(content)
    response.headers['Content-Type'] = mimetype
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ---------------------------------------------------------------------------
# GET /api/v1/reports/attendance?section_id=&from_date=&to_date=
#   SMS-057 — Attendance analytics (admin + teacher)
# ---------------------------------------------------------------------------

@reports_bp.route('/attendance', methods=['GET'], strict_slashes=False)
@roles_required('admin', 'teacher')
def attendance_report():
    section_id = request.args.get('section_id', type=int)
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    if not section_id or not from_date or not to_date:
        return error_response(
            'section_id, from_date and to_date are required', status=400
        )

    result, err = ReportService.attendance_report(section_id, from_date, to_date)
    if err:
        return error_response(err['message'], status=err.get('status', 400))
    return success_response(data=result, message='Attendance report retrieved')


# ---------------------------------------------------------------------------
# GET /api/v1/reports/grades?exam_id=&section_id=
#   SMS-058 — Academic performance (admin + teacher)
# ---------------------------------------------------------------------------

@reports_bp.route('/grades', methods=['GET'], strict_slashes=False)
@roles_required('admin', 'teacher')
def grades_report():
    exam_id = request.args.get('exam_id', type=int)
    section_id = request.args.get('section_id', type=int)

    if not exam_id:
        return error_response('exam_id is required', status=400)

    result, err = ReportService.grades_report(exam_id, section_id)
    if err:
        return error_response(err['message'], status=err.get('status', 400))
    return success_response(data=result, message='Grades report retrieved')


# ---------------------------------------------------------------------------
# GET /api/v1/reports/fees?class_id=&academic_year_id=
#   SMS-059 — Fee collection (admin only)
# ---------------------------------------------------------------------------

@reports_bp.route('/fees', methods=['GET'], strict_slashes=False)
@roles_required('admin')
def fees_report():
    class_id = request.args.get('class_id', type=int)
    academic_year_id = request.args.get('academic_year_id', type=int)

    result, err = ReportService.fees_report(class_id, academic_year_id)
    if err:
        return error_response(err['message'], status=err.get('status', 400))
    return success_response(data=result, message='Fee collection report retrieved')


# ---------------------------------------------------------------------------
# SMS-060 — Export Reports to PDF / Excel
#
# GET /api/v1/reports/<report>/export?format=pdf|excel&...
# Default format = pdf; invalid format → 400. Same RBAC as the underlying
# report. Binary responses are returned directly as file attachments.
# ---------------------------------------------------------------------------

@reports_bp.route('/attendance/export', methods=['GET'], strict_slashes=False)
@roles_required('admin', 'teacher')
def export_attendance_report():
    fmt = request.args.get('format', 'pdf').lower()
    if fmt not in _VALID_FORMATS:
        return error_response("format must be 'pdf' or 'excel'", status=400)

    section_id = request.args.get('section_id', type=int)
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    if not section_id or not from_date or not to_date:
        return error_response(
            'section_id, from_date and to_date are required', status=400
        )

    if fmt == 'pdf':
        content, err = ReportService.export_attendance_pdf(
            section_id, from_date, to_date
        )
        if err:
            return error_response(err['message'], status=err.get('status', 400))
        return _file_response(
            content, _PDF_MIMETYPE, f'attendance_report_{section_id}.pdf'
        )

    content, err = ReportService.export_attendance_excel(
        section_id, from_date, to_date
    )
    if err:
        return error_response(err['message'], status=err.get('status', 400))
    return _file_response(
        content, _XLSX_MIMETYPE, f'attendance_report_{section_id}.xlsx'
    )


@reports_bp.route('/grades/export', methods=['GET'], strict_slashes=False)
@roles_required('admin', 'teacher')
def export_grades_report():
    fmt = request.args.get('format', 'pdf').lower()
    if fmt not in _VALID_FORMATS:
        return error_response("format must be 'pdf' or 'excel'", status=400)

    exam_id = request.args.get('exam_id', type=int)
    section_id = request.args.get('section_id', type=int)
    if not exam_id:
        return error_response('exam_id is required', status=400)

    if fmt == 'pdf':
        content, err = ReportService.export_grades_pdf(exam_id, section_id)
        if err:
            return error_response(err['message'], status=err.get('status', 400))
        return _file_response(
            content, _PDF_MIMETYPE, f'grades_report_{exam_id}.pdf'
        )

    content, err = ReportService.export_grades_excel(exam_id, section_id)
    if err:
        return error_response(err['message'], status=err.get('status', 400))
    return _file_response(
        content, _XLSX_MIMETYPE, f'grades_report_{exam_id}.xlsx'
    )


@reports_bp.route('/fees/export', methods=['GET'], strict_slashes=False)
@roles_required('admin')
def export_fees_report():
    fmt = request.args.get('format', 'pdf').lower()
    if fmt not in _VALID_FORMATS:
        return error_response("format must be 'pdf' or 'excel'", status=400)

    class_id = request.args.get('class_id', type=int)
    academic_year_id = request.args.get('academic_year_id', type=int)

    if fmt == 'pdf':
        content, err = ReportService.export_fees_pdf(class_id, academic_year_id)
        if err:
            return error_response(err['message'], status=err.get('status', 400))
        return _file_response(content, _PDF_MIMETYPE, 'fee_collection_report.pdf')

    content, err = ReportService.export_fees_excel(class_id, academic_year_id)
    if err:
        return error_response(err['message'], status=err.get('status', 400))
    return _file_response(content, _XLSX_MIMETYPE, 'fee_collection_report.xlsx')
