from datetime import date, datetime

from app.utils.tenant import get_db
from app.models.attendance import Attendance
from app.models.student_section import StudentSection


def _parse_date(date_str: str) -> date:
    return datetime.strptime(date_str, '%Y-%m-%d').date()


class AttendanceService:

    @staticmethod
    def mark_attendance(section_id: int, date_str: str, records: list, marked_by_user_id: int):
        """
        Bulk-mark attendance for all students in a section for one date.

        records: [{"student_id": int, "status": str}, ...]
        Returns (result_dict, None) or (None, error_dict).
        409 if any row already exists for this section + date.
        """
        target_date = _parse_date(date_str)

        existing = (
            get_db()
            .query(Attendance)
            .filter_by(section_id=section_id, date=target_date)
            .first()
        )
        if existing:
            return None, {
                'message': f'Attendance already marked for section {section_id} on {date_str}',
                'status': 409,
            }

        created = []
        for rec in records:
            row = Attendance(
                student_id=rec['student_id'],
                section_id=section_id,
                date=target_date,
                status=rec['status'],
                marked_by=marked_by_user_id,
            )
            get_db().add(row)
            created.append(row)

        get_db().commit()

        # Fire absence notifications after commit
        from app.services.notification_service import NotificationService
        for row in created:
            if row.status == 'absent':
                NotificationService.notify_absence(row.student_id, target_date)

        return {
            'section_id': section_id,
            'date': date_str,
            'records_saved': len(created),
        }, None

    @staticmethod
    def get_for_student(student_id: int, month: int, year: int):
        """Return all attendance rows for a student in the given month/year."""
        import calendar
        _, last_day = calendar.monthrange(year, month)
        from_date = date(year, month, 1)
        to_date = date(year, month, last_day)

        rows = (
            get_db()
            .query(Attendance)
            .filter(
                Attendance.student_id == student_id,
                Attendance.date >= from_date,
                Attendance.date <= to_date,
            )
            .order_by(Attendance.date)
            .all()
        )
        return [r.to_dict() for r in rows]

    @staticmethod
    def get_report(section_id: int, from_date_str: str, to_date_str: str):
        """
        Aggregate attendance for a section over a date range.
        Returns per-student summary + per-day counts.
        """
        from_date = _parse_date(from_date_str)
        to_date = _parse_date(to_date_str)

        rows = (
            get_db()
            .query(Attendance)
            .filter(
                Attendance.section_id == section_id,
                Attendance.date >= from_date,
                Attendance.date <= to_date,
            )
            .order_by(Attendance.date, Attendance.student_id)
            .all()
        )

        student_summary: dict = {}
        for row in rows:
            sid = row.student_id
            if sid not in student_summary:
                student_summary[sid] = {'student_id': sid, 'present': 0, 'absent': 0,
                                        'late': 0, 'leave': 0, 'holiday': 0}
            student_summary[sid][row.status] = student_summary[sid].get(row.status, 0) + 1

        return {
            'section_id': section_id,
            'from_date': from_date_str,
            'to_date': to_date_str,
            'total_records': len(rows),
            'student_summaries': list(student_summary.values()),
        }

    @staticmethod
    def get_today_summary():
        """Count of each status value across all sections for today."""
        today = date.today()
        rows = (
            get_db()
            .query(Attendance)
            .filter(Attendance.date == today)
            .all()
        )
        summary = {'present': 0, 'absent': 0, 'late': 0, 'leave': 0, 'holiday': 0}
        for row in rows:
            summary[row.status] = summary.get(row.status, 0) + 1
        summary['total'] = len(rows)
        summary['date'] = str(today)
        return summary
