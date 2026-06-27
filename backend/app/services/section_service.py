from datetime import date

from app.utils.tenant import get_db
from app.models.section import Section
from app.models.student_section import StudentSection
from app.models.student import Student


def _paginate(query, page: int, per_page: int) -> tuple:
    """Returns (items_list, total_count)."""
    total = query.count()
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    return items, total


class SectionService:

    @staticmethod
    def get_all(class_id=None, page=1, per_page=50):
        query = get_db().query(Section).filter_by(is_active=True)
        if class_id:
            query = query.filter_by(class_id=class_id)
        query = query.order_by(Section.class_id, Section.name)
        items, total = _paginate(query, page, per_page)
        pages = (total + per_page - 1) // per_page
        return {
            "sections": [s.to_dict() for s in items],
            "meta": {
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": pages,
            },
        }

    @staticmethod
    def get_by_id(section_id: int):
        """Return section dict with class info and student count, or None."""
        section = get_db().query(Section).filter_by(id=section_id, is_active=True).first()
        if not section:
            return None
        data = section.to_dict()
        student_count = get_db().query(StudentSection).filter_by(section_id=section_id, is_current=True).count()
        data["student_count"] = student_count
        return data

    @staticmethod
    def create(data: dict):
        """
        Create a new section. Blocks duplicate name within same class.
        Returns (section_dict, None) or (None, error_dict).
        """
        name = data.get("name", "").strip()
        if not name:
            return None, {"message": "Name is required", "status": 400}

        class_id = data.get("class_id")
        if not class_id:
            return None, {"message": "class_id is required", "status": 400}

        # Duplicate name within class
        existing = get_db().query(Section).filter_by(name=name, class_id=class_id, is_active=True).first()
        if existing:
            return None, {
                "message": f'Section "{name}" already exists in this class',
                "status": 409,
            }

        section = Section(
            name=name,
            class_id=class_id,
            capacity=data.get("capacity", 40),
            class_teacher_id=data.get("class_teacher_id"),
            is_active=bool(data.get("is_active", True)),
        )
        get_db().add(section)
        get_db().commit()
        return section.to_dict(), None

    @staticmethod
    def update(section_id: int, data: dict):
        """Returns (section_dict, None) or (None, error_dict)."""
        section = get_db().query(Section).filter_by(id=section_id, is_active=True).first()
        if not section:
            return None, {"message": "Section not found", "status": 404}

        if "name" in data:
            new_name = data["name"].strip()
            class_id = data.get("class_id", section.class_id)
            duplicate = get_db().query(Section).filter_by(name=new_name, class_id=class_id, is_active=True).first()
            if duplicate and duplicate.id != section_id:
                return None, {
                    "message": f'Section "{new_name}" already exists in this class',
                    "status": 409,
                }
            section.name = new_name

        if "class_id" in data:
            section.class_id = data["class_id"]

        if "capacity" in data:
            section.capacity = data["capacity"]

        if "class_teacher_id" in data:
            section.class_teacher_id = data["class_teacher_id"]

        if "is_active" in data:
            section.is_active = bool(data["is_active"])

        get_db().commit()
        return section.to_dict(), None

    @staticmethod
    def delete(section_id: int):
        """Soft delete. Blocked if active student enrollments exist."""
        section = get_db().query(Section).filter_by(id=section_id, is_active=True).first()
        if not section:
            return False, {"message": "Section not found", "status": 404}

        active_enrollments = get_db().query(StudentSection).filter_by(section_id=section_id, is_current=True).count()
        if active_enrollments > 0:
            return False, {
                "message": (
                    f"Cannot delete section: {active_enrollments} active enrollment(s) exist. "
                    "Unenroll all students first."
                ),
                "status": 409,
            }

        section.is_active = False
        get_db().commit()
        return True, None

    @staticmethod
    def enroll_student(section_id: int, student_id: int, academic_year_id: int):
        """
        Enroll a student in a section.

        Closes any existing current enrollment across ALL sections first,
        then creates a new StudentSection row for this section.
        Returns (enrollment_dict, None) or (None, error_dict).
        """
        section = get_db().query(Section).filter_by(id=section_id, is_active=True).first()
        if not section:
            return None, {"message": "Section not found", "status": 404}

        student = get_db().query(Student).filter_by(id=student_id, is_active=True).first()
        if not student:
            return None, {"message": "Student not found", "status": 404}

        # Determine academic year string from academic_year_id (or derive from today)
        if academic_year_id:
            from app.models.academic_year import AcademicYear

            ay = get_db().query(AcademicYear).filter_by(id=academic_year_id).first()
            academic_year_str = ay.name if ay else _derive_academic_year()
        else:
            academic_year_str = _derive_academic_year()

        # Check if already enrolled in this section
        already = (
            get_db()
            .query(StudentSection)
            .filter_by(student_id=student_id, section_id=section_id, is_current=True)
            .first()
        )
        if already:
            return None, {
                "message": "Student is already enrolled in this section",
                "status": 409,
            }

        # Close old current enrollment
        old = get_db().query(StudentSection).filter_by(student_id=student_id, is_current=True).first()
        if old:
            old.is_current = False
            old.end_date = date.today()

        enrollment = StudentSection(
            student_id=student_id,
            section_id=section_id,
            academic_year=academic_year_str,
            start_date=date.today(),
            is_current=True,
        )
        get_db().add(enrollment)
        get_db().commit()
        return enrollment.to_dict(), None

    @staticmethod
    def unenroll_student(section_id: int, student_id: int):
        """
        Close the current StudentSection enrollment for a student in a section.
        Returns (True, None) or (False, error_dict).
        """
        enrollment = (
            get_db()
            .query(StudentSection)
            .filter_by(section_id=section_id, student_id=student_id, is_current=True)
            .first()
        )
        if not enrollment:
            return False, {
                "message": "No active enrollment found for this student in this section",
                "status": 404,
            }

        enrollment.is_current = False
        enrollment.end_date = date.today()
        get_db().commit()
        return True, None


def _derive_academic_year() -> str:
    """Derive academic year string from today's date (Jun–Dec → current/next, Jan–May → prev/current)."""
    today = date.today()
    if today.month >= 6:
        return f"{today.year}-{today.year + 1}"
    return f"{today.year - 1}-{today.year}"
