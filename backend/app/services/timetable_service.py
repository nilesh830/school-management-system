from datetime import time

from sqlalchemy.exc import IntegrityError

from app.utils.tenant import get_db
from app.models.timetable import Timetable


def _parse_time(value, field_name: str):
    """Parse HH:MM or HH:MM:SS string into time object. Returns (time, error_str)."""
    if value is None:
        return None, f"{field_name} is required"
    if isinstance(value, time):
        return value, None
    try:
        parts = str(value).split(":")
        if len(parts) == 2:
            return time(int(parts[0]), int(parts[1])), None
        elif len(parts) == 3:
            return time(int(parts[0]), int(parts[1]), int(parts[2])), None
        return None, f"Invalid {field_name} format (use HH:MM or HH:MM:SS)"
    except (ValueError, TypeError):
        return None, f"Invalid {field_name} format (use HH:MM or HH:MM:SS)"


def _validate_conflicts(section_id: int, teacher_id: int, day_of_week: int, period_no: int, exclude_id: int = None):
    """
    Check for section-slot and teacher double-booking conflicts.
    Returns error string if conflict found, else None.
    """
    # Section slot conflict
    q_section = get_db().query(Timetable).filter_by(section_id=section_id, day_of_week=day_of_week, period_no=period_no)
    if exclude_id:
        q_section = q_section.filter(Timetable.id != exclude_id)
    if q_section.first():
        return "This section already has a subject assigned to this day/period slot"

    # Teacher double-booking
    q_teacher = get_db().query(Timetable).filter_by(teacher_id=teacher_id, day_of_week=day_of_week, period_no=period_no)
    if exclude_id:
        q_teacher = q_teacher.filter(Timetable.id != exclude_id)
    if q_teacher.first():
        return "Teacher already assigned to another class at this period"

    return None


class TimetableService:

    @staticmethod
    def get_by_section(section_id: int):
        """Return all timetable entries for a section, ordered by day then period."""
        entries = (
            get_db()
            .query(Timetable)
            .filter_by(section_id=section_id)
            .order_by(Timetable.day_of_week, Timetable.period_no)
            .all()
        )
        return [e.to_dict() for e in entries]

    @staticmethod
    def get_by_teacher(teacher_id: int):
        """Return all timetable entries for a teacher, ordered by day then period."""
        entries = (
            get_db()
            .query(Timetable)
            .filter_by(teacher_id=teacher_id)
            .order_by(Timetable.day_of_week, Timetable.period_no)
            .all()
        )
        return [e.to_dict() for e in entries]

    @staticmethod
    def create(data: dict):
        """
        Create a timetable entry with conflict checks.

        Returns (tt_dict, None) or (None, error_dict).
        """
        section_id = data.get("section_id")
        subject_id = data.get("subject_id")
        teacher_id = data.get("teacher_id")
        day_of_week = data.get("day_of_week")
        period_no = data.get("period_no")

        # Required field checks
        if section_id is None:
            return None, {"message": "section_id is required", "status": 400}
        if subject_id is None:
            return None, {"message": "subject_id is required", "status": 400}
        if teacher_id is None:
            return None, {"message": "teacher_id is required", "status": 400}
        if day_of_week is None:
            return None, {"message": "day_of_week is required (0=Monday to 5=Saturday)", "status": 400}
        if period_no is None:
            return None, {"message": "period_no is required", "status": 400}

        try:
            day_of_week = int(day_of_week)
            period_no = int(period_no)
        except (TypeError, ValueError):
            return None, {"message": "day_of_week and period_no must be integers", "status": 400}

        if not (0 <= day_of_week <= 5):
            return None, {"message": "day_of_week must be 0 (Monday) to 5 (Saturday)", "status": 400}

        start_time_val, err = _parse_time(data.get("start_time"), "start_time")
        if err:
            return None, {"message": err, "status": 400}

        end_time_val, err = _parse_time(data.get("end_time"), "end_time")
        if err:
            return None, {"message": err, "status": 400}

        if end_time_val <= start_time_val:
            return None, {"message": "end_time must be after start_time", "status": 400}

        # Conflict checks
        conflict = _validate_conflicts(section_id, teacher_id, day_of_week, period_no)
        if conflict:
            return None, {"message": conflict, "status": 409}

        entry = Timetable(
            section_id=section_id,
            subject_id=subject_id,
            teacher_id=teacher_id,
            day_of_week=day_of_week,
            period_no=period_no,
            start_time=start_time_val,
            end_time=end_time_val,
        )
        try:
            get_db().add(entry)
            get_db().commit()
        except IntegrityError:
            get_db().rollback()
            return None, {
                "message": "Timetable conflict: duplicate slot or teacher double-booking",
                "status": 409,
            }
        return entry.to_dict(), None

    @staticmethod
    def update(entry_id: int, data: dict):
        """
        Update a timetable entry with conflict checks.
        Returns (tt_dict, None) or (None, error_dict).
        """
        entry = get_db().query(Timetable).filter_by(id=entry_id).first()
        if not entry:
            return None, {"message": "Timetable entry not found", "status": 404}

        # Pick new values (fall back to existing)
        section_id = data.get("section_id", entry.section_id)
        subject_id = data.get("subject_id", entry.subject_id)
        teacher_id = data.get("teacher_id", entry.teacher_id)
        day_of_week = data.get("day_of_week", entry.day_of_week)
        period_no = data.get("period_no", entry.period_no)

        try:
            day_of_week = int(day_of_week)
            period_no = int(period_no)
        except (TypeError, ValueError):
            return None, {"message": "day_of_week and period_no must be integers", "status": 400}

        if not (0 <= day_of_week <= 5):
            return None, {"message": "day_of_week must be 0 (Monday) to 5 (Saturday)", "status": 400}

        start_time_val = entry.start_time
        end_time_val = entry.end_time

        if "start_time" in data:
            start_time_val, err = _parse_time(data["start_time"], "start_time")
            if err:
                return None, {"message": err, "status": 400}

        if "end_time" in data:
            end_time_val, err = _parse_time(data["end_time"], "end_time")
            if err:
                return None, {"message": err, "status": 400}

        if end_time_val <= start_time_val:
            return None, {"message": "end_time must be after start_time", "status": 400}

        # Conflict checks (exclude current entry)
        conflict = _validate_conflicts(section_id, teacher_id, day_of_week, period_no, exclude_id=entry_id)
        if conflict:
            return None, {"message": conflict, "status": 409}

        entry.section_id = section_id
        entry.subject_id = subject_id
        entry.teacher_id = teacher_id
        entry.day_of_week = day_of_week
        entry.period_no = period_no
        entry.start_time = start_time_val
        entry.end_time = end_time_val

        try:
            get_db().commit()
        except IntegrityError:
            get_db().rollback()
            return None, {
                "message": "Timetable conflict: duplicate slot or teacher double-booking",
                "status": 409,
            }
        return entry.to_dict(), None

    @staticmethod
    def delete(entry_id: int):
        """Hard delete a timetable entry (ephemeral config)."""
        entry = get_db().query(Timetable).filter_by(id=entry_id).first()
        if not entry:
            return False, {"message": "Timetable entry not found", "status": 404}
        get_db().delete(entry)
        get_db().commit()
        return True, None
