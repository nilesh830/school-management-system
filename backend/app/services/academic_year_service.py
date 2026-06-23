from datetime import date

from app.utils.tenant import get_db
from app.models.academic_year import AcademicYear


class AcademicYearService:

    @staticmethod
    def get_all():
        """Return all active academic years ordered by start_date descending."""
        years = get_db().query(AcademicYear).filter_by(is_active=True).order_by(AcademicYear.start_date.desc()).all()
        return [y.to_dict() for y in years]

    @staticmethod
    def get_current():
        """Return the single academic year where is_current=True, or None."""
        year = get_db().query(AcademicYear).filter_by(is_current=True).first()
        return year.to_dict() if year else None

    @staticmethod
    def get_by_id(year_id: int):
        """Return a single academic year dict or None."""
        year = get_db().query(AcademicYear).filter_by(id=year_id, is_active=True).first()
        return year.to_dict() if year else None

    @staticmethod
    def create(data: dict):
        """
        Create a new academic year.

        If is_current=True, unsets is_current on all other years first.
        Returns (ay_dict, None) on success or (None, error_dict) on failure.
        """
        # Validate required fields
        name = data.get("name", "").strip()
        if not name:
            return None, {"message": "Name is required", "status": 400}

        start_date = data.get("start_date")
        end_date = data.get("end_date")
        if not start_date or not end_date:
            return None, {"message": "start_date and end_date are required", "status": 400}

        # Parse date strings if needed
        if isinstance(start_date, str):
            try:
                start_date = date.fromisoformat(start_date)
            except ValueError:
                return None, {"message": "Invalid start_date format (use YYYY-MM-DD)", "status": 400}
        if isinstance(end_date, str):
            try:
                end_date = date.fromisoformat(end_date)
            except ValueError:
                return None, {"message": "Invalid end_date format (use YYYY-MM-DD)", "status": 400}

        if end_date <= start_date:
            return None, {"message": "end_date must be after start_date", "status": 400}

        # Check for duplicate name
        if get_db().query(AcademicYear).filter_by(name=name).first():
            return None, {"message": "Academic year with this name already exists", "status": 409}

        is_current = bool(data.get("is_current", False))

        if is_current:
            # Unset is_current on all existing years
            get_db().query(AcademicYear).filter_by(is_current=True).update({"is_current": False})

        year = AcademicYear(
            name=name,
            start_date=start_date,
            end_date=end_date,
            is_current=is_current,
            is_active=bool(data.get("is_active", True)),
        )
        get_db().add(year)
        get_db().commit()
        return year.to_dict(), None

    @staticmethod
    def update(year_id: int, data: dict):
        """
        Update an academic year.

        If setting is_current=True, unsets all other years first.
        Returns (ay_dict, None) or (None, error_dict).
        """
        year = get_db().query(AcademicYear).filter_by(id=year_id, is_active=True).first()
        if not year:
            return None, {"message": "Academic year not found", "status": 404}

        if "name" in data:
            name = data["name"].strip()
            duplicate = get_db().query(AcademicYear).filter_by(name=name).first()
            if duplicate and duplicate.id != year_id:
                return None, {"message": "Academic year with this name already exists", "status": 409}
            year.name = name

        if "start_date" in data:
            sd = data["start_date"]
            if isinstance(sd, str):
                try:
                    sd = date.fromisoformat(sd)
                except ValueError:
                    return None, {"message": "Invalid start_date format", "status": 400}
            year.start_date = sd

        if "end_date" in data:
            ed = data["end_date"]
            if isinstance(ed, str):
                try:
                    ed = date.fromisoformat(ed)
                except ValueError:
                    return None, {"message": "Invalid end_date format", "status": 400}
            year.end_date = ed

        if year.end_date <= year.start_date:
            return None, {"message": "end_date must be after start_date", "status": 400}

        if "is_current" in data:
            if bool(data["is_current"]) and not year.is_current:
                # Unset all other current years
                get_db().query(AcademicYear).filter(
                    AcademicYear.is_current.is_(True), AcademicYear.id != year_id
                ).update({"is_current": False})
            year.is_current = bool(data["is_current"])

        if "is_active" in data:
            year.is_active = bool(data["is_active"])

        get_db().commit()
        return year.to_dict(), None

    @staticmethod
    def delete(year_id: int):
        """Soft delete an academic year."""
        year = get_db().query(AcademicYear).filter_by(id=year_id, is_active=True).first()
        if not year:
            return False, {"message": "Academic year not found", "status": 404}
        year.is_active = False
        if year.is_current:
            year.is_current = False
        get_db().commit()
        return True, None
