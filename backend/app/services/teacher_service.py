import os
import secrets

from datetime import date
from flask import current_app
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from app.utils.tenant import get_db
from app.models.teacher import Teacher
from app.models.teacher_subject import TeacherSubject
from app.models.teacher_document import TeacherDocument
from app.models.timetable import Timetable

ALLOWED_DOC_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
MAX_DOC_BYTES = 5 * 1024 * 1024  # 5 MB


def _allowed_doc(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_DOC_EXTENSIONS


def _paginate(query, page: int, per_page: int) -> tuple:
    """Returns (items_list, total_count)."""
    total = query.count()
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    return items, total


def _parse_date(value, field_name: str):
    """Parse ISO date string or pass through date objects. Returns (date, error_str)."""
    if value is None:
        return None, None
    if isinstance(value, date):
        return value, None
    try:
        return date.fromisoformat(str(value)), None
    except ValueError:
        return None, f"Invalid {field_name} format (use YYYY-MM-DD)"


class TeacherService:

    # -------------------------------------------------------------------------
    # SMS-014 — Teacher list
    # -------------------------------------------------------------------------

    @staticmethod
    def get_all(page=1, per_page=20, search=""):
        query = get_db().query(Teacher).filter_by(is_active=True)

        if search:
            query = query.filter(
                or_(
                    Teacher.first_name.ilike(f"%{search}%"),
                    Teacher.last_name.ilike(f"%{search}%"),
                    Teacher.employee_id.ilike(f"%{search}%"),
                )
            )

        query = query.order_by(Teacher.employee_id)
        items, total = _paginate(query, page, per_page)
        pages = (total + per_page - 1) // per_page
        return {
            "teachers": [t.to_dict() for t in items],
            "meta": {
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": pages,
            },
        }

    # -------------------------------------------------------------------------
    # SMS-014 — Teacher profile
    # -------------------------------------------------------------------------

    @staticmethod
    def get_by_id(teacher_id: int):
        teacher = get_db().query(Teacher).filter_by(id=teacher_id, is_active=True).first()
        if not teacher:
            return None
        data = teacher.to_dict(include_subjects=True)
        return data

    # -------------------------------------------------------------------------
    # SMS-014 — Create teacher
    # -------------------------------------------------------------------------

    @staticmethod
    def create(data: dict):
        """
        Create a new teacher record.

        Returns (teacher_dict, None) or (None, error_dict).
        """
        employee_id = data.get("employee_id", "").strip()
        if not employee_id:
            return None, {"message": "employee_id is required", "status": 400}

        first_name = data.get("first_name", "").strip()
        last_name = data.get("last_name", "").strip()
        if not first_name or not last_name:
            return None, {"message": "first_name and last_name are required", "status": 400}

        # Duplicate employee_id check (409)
        if get_db().query(Teacher).filter_by(employee_id=employee_id).first():
            return None, {
                "message": f'Teacher with employee_id "{employee_id}" already exists',
                "status": 409,
            }

        joining_date_val, err = _parse_date(data.get("joining_date"), "joining_date")
        if err:
            return None, {"message": err, "status": 400}
        if not joining_date_val:
            return None, {"message": "joining_date is required", "status": 400}

        dob_val, err = _parse_date(data.get("date_of_birth"), "date_of_birth")
        if err:
            return None, {"message": err, "status": 400}

        gender = data.get("gender")
        if gender and gender not in ("Male", "Female", "Other"):
            return None, {"message": "gender must be Male, Female, or Other", "status": 400}

        teacher = Teacher(
            user_id=data.get("user_id") or 1,
            employee_id=employee_id,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=dob_val,
            gender=gender,
            qualification=data.get("qualification"),
            specialization=data.get("specialization"),
            joining_date=joining_date_val,
            phone=data.get("phone"),
            address=data.get("address"),
            is_active=bool(data.get("is_active", True)),
        )
        get_db().add(teacher)
        get_db().commit()
        return teacher.to_dict(), None

    # -------------------------------------------------------------------------
    # SMS-014 — Update teacher
    # -------------------------------------------------------------------------

    @staticmethod
    def update(teacher_id: int, data: dict):
        """Returns (teacher_dict, None) or (None, error_dict)."""
        teacher = get_db().query(Teacher).filter_by(id=teacher_id, is_active=True).first()
        if not teacher:
            return None, {"message": "Teacher not found", "status": 404}

        allowed_fields = [
            "first_name",
            "last_name",
            "qualification",
            "specialization",
            "phone",
            "address",
            "gender",
        ]
        for field in allowed_fields:
            if field in data:
                setattr(teacher, field, data[field])

        if "date_of_birth" in data:
            dob_val, err = _parse_date(data["date_of_birth"], "date_of_birth")
            if err:
                return None, {"message": err, "status": 400}
            teacher.date_of_birth = dob_val

        if "joining_date" in data:
            jd_val, err = _parse_date(data["joining_date"], "joining_date")
            if err:
                return None, {"message": err, "status": 400}
            teacher.joining_date = jd_val

        if "gender" in data:
            gender = data["gender"]
            if gender and gender not in ("Male", "Female", "Other"):
                return None, {"message": "gender must be Male, Female, or Other", "status": 400}
            teacher.gender = gender

        if "employee_id" in data:
            new_eid = data["employee_id"].strip()
            duplicate = get_db().query(Teacher).filter_by(employee_id=new_eid).first()
            if duplicate and duplicate.id != teacher_id:
                return None, {
                    "message": f'Teacher with employee_id "{new_eid}" already exists',
                    "status": 409,
                }
            teacher.employee_id = new_eid

        get_db().commit()
        return teacher.to_dict(), None

    # -------------------------------------------------------------------------
    # SMS-014 — Soft delete
    # -------------------------------------------------------------------------

    @staticmethod
    def delete(teacher_id: int):
        teacher = get_db().query(Teacher).filter_by(id=teacher_id, is_active=True).first()
        if not teacher:
            return False, {"message": "Teacher not found", "status": 404}
        teacher.is_active = False
        get_db().commit()
        return True, None

    # -------------------------------------------------------------------------
    # SMS-015 — Subject assignment
    # -------------------------------------------------------------------------

    @staticmethod
    def assign_subject(teacher_id: int, subject_id: int, class_id=None, academic_year_id=None):
        """
        Assign a subject to a teacher (optionally scoped to a class/year).
        Returns (ts_dict, None) or (None, error_dict).
        """
        teacher = get_db().query(Teacher).filter_by(id=teacher_id, is_active=True).first()
        if not teacher:
            return None, {"message": "Teacher not found", "status": 404}

        # Check duplicate assignment
        query = (
            get_db()
            .query(TeacherSubject)
            .filter_by(
                teacher_id=teacher_id,
                subject_id=subject_id,
                class_id=class_id,
                academic_year_id=academic_year_id,
            )
        )
        if query.first():
            return None, {
                "message": "This subject is already assigned to the teacher for this class/year",
                "status": 409,
            }

        ts = TeacherSubject(
            teacher_id=teacher_id,
            subject_id=subject_id,
            class_id=class_id,
            academic_year_id=academic_year_id,
        )
        get_db().add(ts)
        get_db().commit()
        return ts.to_dict(), None

    @staticmethod
    def unassign_subject(teacher_id: int, subject_id: int, class_id=None):
        """Remove a TeacherSubject row. Returns (True, None) or (False, error_dict)."""
        ts = (
            get_db()
            .query(TeacherSubject)
            .filter_by(teacher_id=teacher_id, subject_id=subject_id, class_id=class_id)
            .first()
        )
        if not ts:
            return False, {"message": "Assignment not found", "status": 404}
        get_db().delete(ts)
        get_db().commit()
        return True, None

    @staticmethod
    def get_subjects(teacher_id: int):
        """Return list of subject dicts assigned to the teacher."""
        teacher = get_db().query(Teacher).filter_by(id=teacher_id, is_active=True).first()
        if not teacher:
            return None, {"message": "Teacher not found", "status": 404}
        assignments = get_db().query(TeacherSubject).filter_by(teacher_id=teacher_id).all()
        return [ts.to_dict() for ts in assignments], None

    # -------------------------------------------------------------------------
    # SMS-018 — Document upload / list
    # -------------------------------------------------------------------------

    @staticmethod
    def upload_document(teacher_id: int, document_type: str, file, uploaded_by: int):
        """
        Save uploaded document to UPLOAD_FOLDER/teachers/<teacher_id>/ and create DB record.
        Returns (doc_dict, None) or (None, error_dict).
        """
        teacher = get_db().query(Teacher).filter_by(id=teacher_id, is_active=True).first()
        if not teacher:
            return None, {"message": "Teacher not found", "status": 404}

        if not file or not file.filename:
            return None, {"message": "No file provided", "status": 400}

        if not _allowed_doc(file.filename):
            return None, {
                "message": "Invalid file type. Allowed: PDF, JPG, JPEG, PNG",
                "status": 400,
            }

        content = file.read()
        if len(content) > MAX_DOC_BYTES:
            return None, {"message": "File exceeds maximum size of 5 MB", "status": 400}

        upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "teachers", str(teacher_id))
        os.makedirs(upload_dir, exist_ok=True)

        ext = file.filename.rsplit(".", 1)[1].lower()
        safe_name = secure_filename(f"{document_type}_{secrets.token_hex(8)}.{ext}")
        abs_path = os.path.join(upload_dir, safe_name)
        with open(abs_path, "wb") as fh:
            fh.write(content)

        rel_path = os.path.join("teachers", str(teacher_id), safe_name)

        doc = TeacherDocument(
            teacher_id=teacher_id,
            document_type=document_type,
            file_name=safe_name,
            file_path=rel_path,
            uploaded_by=uploaded_by,
            is_active=True,
        )
        get_db().add(doc)
        get_db().commit()
        return doc.to_dict(), None

    @staticmethod
    def list_documents(teacher_id: int):
        """Return (list_of_doc_dicts, None) or (None, error_dict)."""
        teacher = get_db().query(Teacher).filter_by(id=teacher_id, is_active=True).first()
        if not teacher:
            return None, {"message": "Teacher not found", "status": 404}
        docs = (
            get_db()
            .query(TeacherDocument)
            .filter_by(teacher_id=teacher_id, is_active=True)
            .order_by(TeacherDocument.created_at.desc())
            .all()
        )
        return [d.to_dict() for d in docs], None

    @staticmethod
    def delete_document(teacher_id: int, doc_id: int):
        """Soft delete a teacher document."""
        doc = get_db().query(TeacherDocument).filter_by(id=doc_id, teacher_id=teacher_id, is_active=True).first()
        if not doc:
            return False, {"message": "Document not found", "status": 404}
        doc.is_active = False
        get_db().commit()
        return True, None

    # -------------------------------------------------------------------------
    # SMS-022 — Schedule
    # -------------------------------------------------------------------------

    @staticmethod
    def get_schedule(teacher_id: int, academic_year_id=None):
        """
        Return timetable entries for a teacher, ordered by day/period.
        academic_year_id is accepted for future filtering but timetable rows
        are already scoped to section (which belongs to a class/year).
        """
        teacher = get_db().query(Teacher).filter_by(id=teacher_id, is_active=True).first()
        if not teacher:
            return None, {"message": "Teacher not found", "status": 404}

        query = (
            get_db()
            .query(Timetable)
            .filter_by(teacher_id=teacher_id)
            .order_by(Timetable.day_of_week, Timetable.period_no)
        )
        entries = query.all()
        return [e.to_dict() for e in entries], None
