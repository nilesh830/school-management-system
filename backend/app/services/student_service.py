import os
import secrets

from flask import current_app
from sqlalchemy import or_, select
from werkzeug.utils import secure_filename

from app.utils.tenant import get_db
from app.models.student import Student
from app.models.student_section import StudentSection
from app.models.section import Section
from app.models.student_document import StudentDocument
from app.models.parent import Parent, student_parent
from app.models.user import User
from app.schemas.student_schema import StudentBulkRowSchema

ALLOWED_DOC_EXTENSIONS = {"pdf", "jpg", "jpeg", "png"}
MAX_DOC_BYTES = 5 * 1024 * 1024  # 5 MB

# Upper bound on a single bulk import to protect the request/transaction.
MAX_BULK_ROWS = 1000

_bulk_row_schema = StudentBulkRowSchema()


class _RowError(Exception):
    """Raised inside a per-row savepoint to roll back just that row."""


def _allowed_doc(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_DOC_EXTENSIONS


def _paginate(query, page: int, per_page: int) -> tuple:
    """Returns (items_list, total_count) without Flask-SQLAlchemy dependency."""
    total = query.count()
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    return items, total


class StudentService:

    # -------------------------------------------------------------------------
    # SMS-008 — Student list
    # -------------------------------------------------------------------------

    @staticmethod
    def _teacher_section_ids(teacher_user_id: int) -> set:
        """Section ids a teacher is responsible for.

        Union of sections where the teacher is the class (homeroom) teacher and
        sections where the teacher teaches at least one period in the timetable.
        Returns an empty set if the user has no teacher record / no sections.
        """
        from app.models.teacher import Teacher
        from app.models.timetable import Timetable

        db = get_db()
        teacher = db.query(Teacher).filter_by(user_id=teacher_user_id, is_active=True).first()
        if not teacher:
            return set()

        section_ids = set()
        for (sid,) in db.query(Section.id).filter_by(class_teacher_id=teacher.id).all():
            section_ids.add(sid)
        for (sid,) in db.query(Timetable.section_id).filter_by(teacher_id=teacher.id).distinct().all():
            section_ids.add(sid)
        return section_ids

    @staticmethod
    def get_all(page=1, per_page=20, search="", section_id=None, teacher_user_id=None):
        # class_id filter deferred to Sprint 3 when Class model is available.
        query = get_db().query(Student).filter_by(is_active=True)

        if search:
            query = query.filter(
                or_(
                    Student.first_name.ilike(f"%{search}%"),
                    Student.last_name.ilike(f"%{search}%"),
                    Student.admission_no.ilike(f"%{search}%"),
                )
            )

        if section_id:
            query = query.join(
                StudentSection,
                (StudentSection.student_id == Student.id)
                & (StudentSection.section_id == section_id)
                & (StudentSection.is_current.is_(True)),
            )
        elif teacher_user_id is not None:
            # "My Students" — restrict the roster to the teacher's own sections.
            # Only applied to the unfiltered listing; an explicit section_id
            # (e.g. marks entry) keeps the existing section-scoped behaviour.
            allowed_sections = StudentService._teacher_section_ids(teacher_user_id)
            if not allowed_sections:
                return {
                    "students": [],
                    "meta": {"total": 0, "page": page, "per_page": per_page, "pages": 0},
                }
            query = query.join(
                StudentSection,
                (StudentSection.student_id == Student.id)
                & (StudentSection.section_id.in_(allowed_sections))
                & (StudentSection.is_current.is_(True)),
            )

        items, total = _paginate(query.order_by(Student.admission_no), page, per_page)
        pages = (total + per_page - 1) // per_page
        return {
            "students": [s.to_dict() for s in items],
            "meta": {
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": pages,
            },
        }

    # -------------------------------------------------------------------------
    # SMS-009 — Student profile
    # -------------------------------------------------------------------------

    @staticmethod
    def get_by_id(student_id):
        student = get_db().query(Student).filter_by(id=student_id, is_active=True).first()
        if not student:
            return None
        result = student.to_dict()
        # Attach current section info
        current_section = get_db().query(StudentSection).filter_by(student_id=student_id, is_current=True).first()
        result["current_section"] = current_section.to_dict() if current_section else None
        return result

    # -------------------------------------------------------------------------
    # SMS-007 — Student enrollment (T-007-02 / T-007-03)
    # -------------------------------------------------------------------------

    @staticmethod
    def create(data: dict):
        """
        Create a new student record.

        Raises 409 if admission_no is already taken.
        Expects pre-validated data (dates already parsed to date objects by Marshmallow).
        Returns (student_dict, None) on success or (None, error_dict) on failure.
        """
        if get_db().query(Student).filter_by(admission_no=data.get("admission_no")).first():
            return None, {
                "message": "Admission number already exists",
                "status": 409,
            }

        section_id = data.get("section_id")
        if section_id:
            section = get_db().query(Section).filter_by(id=section_id, is_active=True).first()
            if not section:
                return None, {"message": "Section not found", "status": 404}

        # Optional login account. If the admin supplied email/password (or either),
        # provision a User(role=student) and link it. Otherwise the student is a
        # profile-only record (user_id stays null — valid for pupils who don't log in).
        user_id = data.get("user_id")
        if data.get("email") or data.get("password"):
            from app.services.user_service import UserService

            user, err = UserService.build_login(
                get_db(),
                email=data.get("email"),
                password=data.get("password"),
                role="student",
                first_name=data["first_name"],
                last_name=data["last_name"],
            )
            if err:
                get_db().rollback()
                return None, err
            user_id = user.id

        student = Student(
            admission_no=data["admission_no"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            date_of_birth=data["date_of_birth"],
            gender=data["gender"],
            admission_date=data["admission_date"],
            blood_group=data.get("blood_group"),
            address=data.get("address"),
            phone=data.get("phone"),
            photo_url=data.get("photo_url"),
            user_id=user_id,
        )
        get_db().add(student)
        get_db().flush()  # assign student.id before creating the enrollment

        # Optional initial section placement → first (current) enrollment.
        if section_id:
            adm = data["admission_date"]
            academic_year = (
                f"{adm.year}-{adm.year + 1}" if adm.month >= 6 else f"{adm.year - 1}-{adm.year}"
            )
            get_db().add(
                StudentSection(
                    student_id=student.id,
                    section_id=section_id,
                    academic_year=academic_year,
                    start_date=adm,
                    is_current=True,
                )
            )

        get_db().commit()
        return student.to_dict(), None

    # -------------------------------------------------------------------------
    # Bulk student registration — screen / preview / commit
    # -------------------------------------------------------------------------

    @staticmethod
    def get_section_reference() -> list:
        """Active sections for the bulk-import template's reference sheet.

        Label matches the single-student form's dropdown ("{class} — {name}").
        """
        db = get_db()
        sections = db.query(Section).filter_by(is_active=True).all()
        ref = []
        for s in sections:
            d = s.to_dict()
            class_name = d.get("class_name")
            label = f"{class_name} — {s.name}" if class_name else s.name
            ref.append(
                {"id": s.id, "label": label, "class_name": class_name, "capacity": s.capacity}
            )
        # Sort by class then section name for a readable reference sheet.
        ref.sort(key=lambda x: (str(x["class_name"] or ""), x["label"]))
        return ref

    @staticmethod
    def _screen_bulk_rows(rows: list) -> list:
        """Validate + flag each parsed row WITHOUT writing anything.

        Returns a list aligned to ``rows``, each entry:
          {index, row (1-based sheet row or ordinal), status, data, errors,
           will_create_login, label}
        status ∈ {"valid", "error", "duplicate"}.

        Duplicate = admission_no already used (in-file OR in DB), or the login
        email already used (in-file OR in DB) — either makes the row un-insertable.
        Shared by preview_bulk() and create_many() so the committed set is
        re-screened against live DB state (never trusts the client).
        """
        db = get_db()

        # Load supplied rows through the schema, collecting per-row errors.
        loaded = []
        for i, raw in enumerate(rows):
            sheet_row = raw.get("_row", i + 2) if isinstance(raw, dict) else i + 2
            payload = {k: v for k, v in raw.items() if k != "_row"} if isinstance(raw, dict) else {}
            errors = _bulk_row_schema.validate(payload)
            data = _bulk_row_schema.load(payload) if not errors else None
            loaded.append(
                {
                    "index": i,
                    "row": sheet_row,
                    "status": "error" if errors else "valid",
                    "data": data,
                    "errors": errors or {},
                    "will_create_login": bool(data and data.get("email")),
                    "label": (
                        f"{payload.get('first_name', '')} {payload.get('last_name', '')}".strip()
                        or payload.get("admission_no")
                        or f"Row {sheet_row}"
                    ),
                }
            )

        valid = [e for e in loaded if e["status"] == "valid"]

        # --- admission_no duplicates -----------------------------------------
        adm_nos = [e["data"]["admission_no"] for e in valid]
        db_adm = set()
        existing = [a for a in adm_nos if a]
        if existing:
            db_adm = {
                r[0]
                for r in db.query(Student.admission_no).filter(Student.admission_no.in_(existing)).all()
            }
        seen_adm = {}
        for e in valid:
            adm = e["data"]["admission_no"]
            if adm in db_adm:
                e["status"] = "duplicate"
                e["errors"]["admission_no"] = ["Admission number already exists in this school"]
            elif adm in seen_adm:
                e["status"] = "duplicate"
                e["errors"]["admission_no"] = [f"Duplicate admission number in file (also row {seen_adm[adm]})"]
            else:
                seen_adm[adm] = e["row"]

        # --- login email duplicates ------------------------------------------
        emails = [e["data"].get("email") for e in valid if e["status"] == "valid" and e["data"].get("email")]
        db_emails = set()
        if emails:
            db_emails = {
                r[0].lower()
                for r in db.query(User.email).filter(User.email.in_([m.lower() for m in emails])).all()
            }
        seen_email = {}
        for e in valid:
            if e["status"] != "valid":
                continue
            email = (e["data"].get("email") or "").lower()
            if not email:
                continue
            if email in db_emails:
                e["status"] = "error"
                e["errors"]["email"] = ["A user with this email already exists"]
            elif email in seen_email:
                e["status"] = "error"
                e["errors"]["email"] = [f"Duplicate login email in file (also row {seen_email[email]})"]
            else:
                seen_email[email] = e["row"]

        # --- section existence -----------------------------------------------
        section_ids = {
            e["data"]["section_id"]
            for e in valid
            if e["status"] == "valid" and e["data"].get("section_id")
        }
        known_sections = set()
        if section_ids:
            known_sections = {
                r[0]
                for r in db.query(Section.id)
                .filter(Section.id.in_(section_ids), Section.is_active.is_(True))
                .all()
            }
        for e in valid:
            if e["status"] != "valid":
                continue
            sid = e["data"].get("section_id")
            if sid and sid not in known_sections:
                e["status"] = "error"
                e["errors"]["section_id"] = [f"Section {sid} not found"]

        return loaded

    @staticmethod
    def _summarize(screened: list) -> dict:
        summary = {"total": len(screened), "valid": 0, "error": 0, "duplicate": 0, "created": 0}
        for e in screened:
            summary[e["status"]] = summary.get(e["status"], 0) + 1
        return summary

    @staticmethod
    def preview_bulk(rows: list):
        """Dry-run: validate + flag every row. No DB writes.

        Returns (result_dict, None) or (None, error_dict).
        """
        if not rows:
            return None, {"message": "No rows found in the uploaded file", "status": 400}
        if len(rows) > MAX_BULK_ROWS:
            return None, {
                "message": f"Too many rows ({len(rows)}). Split the file into batches of {MAX_BULK_ROWS} or fewer.",
                "status": 400,
            }
        screened = StudentService._screen_bulk_rows(rows)
        return {
            "rows": [
                {
                    "row": e["row"],
                    "status": e["status"],
                    "label": e["label"],
                    "will_create_login": e["will_create_login"] and e["status"] == "valid",
                    "errors": e["errors"],
                    "data": {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in (e["data"] or {}).items()},
                }
                for e in screened
            ],
            "summary": StudentService._summarize(screened),
        }, None

    @staticmethod
    def create_many(rows: list, school_slug: str | None = None, school_name: str | None = None):
        """Insert all valid rows in one tenant transaction (partial success).

        Bad/duplicate rows are skipped, valid rows committed. Each row is wrapped
        in a SAVEPOINT so one failing insert can't discard the rows before it.
        Rows that supply an email get an auto-generated temp password and a
        login account; the credentials are emailed asynchronously.

        Returns (result_dict, None) or (None, error_dict).
        """
        from app.services.user_service import UserService
        from app.utils.validators import generate_temp_password
        from app.utils.email import resolve_smtp_settings, send_emails_async

        if not rows:
            return None, {"message": "No rows found in the uploaded file", "status": 400}
        if len(rows) > MAX_BULK_ROWS:
            return None, {
                "message": f"Too many rows ({len(rows)}). Split the file into batches of {MAX_BULK_ROWS} or fewer.",
                "status": 400,
            }

        # Resolve the school name for the email body (master DB lookup).
        if school_slug and not school_name:
            try:
                from app.models.master.school import School

                school = School.query.filter_by(slug=school_slug).first()
                school_name = school.name if school else None
            except Exception:
                school_name = None

        db = get_db()
        screened = StudentService._screen_bulk_rows(rows)

        email_messages = []
        credentials = []

        for e in screened:
            if e["status"] != "valid":
                continue
            row = e["data"]
            temp_password = None
            try:
                with db.begin_nested():  # SAVEPOINT — isolates this row
                    user_id = None
                    if row.get("email"):
                        temp_password = generate_temp_password()
                        user, err = UserService.build_login(
                            db,
                            email=row["email"],
                            password=temp_password,
                            role="student",
                            first_name=row["first_name"],
                            last_name=row["last_name"],
                        )
                        if err:
                            raise _RowError(err["message"])
                        user_id = user.id

                    student = Student(
                        admission_no=row["admission_no"],
                        first_name=row["first_name"],
                        last_name=row["last_name"],
                        date_of_birth=row["date_of_birth"],
                        gender=row["gender"],
                        admission_date=row["admission_date"],
                        blood_group=row.get("blood_group"),
                        address=row.get("address"),
                        phone=row.get("phone"),
                        user_id=user_id,
                    )
                    db.add(student)
                    db.flush()

                    section_id = row.get("section_id")
                    if section_id:
                        section = db.query(Section).filter_by(id=section_id, is_active=True).first()
                        if not section:
                            raise _RowError(f"Section {section_id} not found")
                        adm = row["admission_date"]
                        academic_year = (
                            f"{adm.year}-{adm.year + 1}" if adm.month >= 6 else f"{adm.year - 1}-{adm.year}"
                        )
                        db.add(
                            StudentSection(
                                student_id=student.id,
                                section_id=section_id,
                                academic_year=academic_year,
                                start_date=adm,
                                is_current=True,
                            )
                        )
            except _RowError as exc:
                e["status"] = "error"
                e["errors"]["_"] = [str(exc)]
                continue
            except Exception as exc:  # unexpected DB error — skip row, keep batch
                e["status"] = "error"
                e["errors"]["_"] = [f"Could not create student: {exc}"]
                continue

            e["status"] = "created"
            if row.get("email") and temp_password:
                credentials.append(
                    {
                        "admission_no": row["admission_no"],
                        "name": f"{row['first_name']} {row['last_name']}",
                        "email": row["email"],
                    }
                )
                email_messages.append(
                    StudentService._build_credential_email(
                        row, temp_password, school_slug, school_name
                    )
                )

        db.commit()

        # Fire the credential emails after the DB is durably committed.
        settings = resolve_smtp_settings(school_slug)
        queued = send_emails_async(settings, email_messages) if settings else 0

        return {
            "rows": [
                {"row": e["row"], "status": e["status"], "label": e["label"], "errors": e["errors"]}
                for e in screened
            ],
            "summary": StudentService._summarize(screened),
            "emails": {
                "with_login": len(email_messages),
                "queued": queued,
                "configured": bool(settings),
            },
        }, None

    @staticmethod
    def _build_credential_email(row: dict, temp_password: str, school_slug, school_name) -> dict:
        """Compose one credential email dict {to, subject, body}."""
        frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:4200")
        login_link = f"{frontend_url}/auth/login"
        if school_slug:
            login_link += f"?school_slug={school_slug}"
        school_label = school_name or "your school"
        body = (
            f"Hello {row['first_name']} {row['last_name']},\n\n"
            f"An account has been created for you at {school_label}.\n\n"
            f"Login email: {row['email']}\n"
            f"Temporary password: {temp_password}\n\n"
            f"Sign in here: {login_link}\n\n"
            f"Please change your password after your first login.\n"
        )
        return {
            "to": row["email"],
            "subject": f"Your {school_label} student account",
            "body": body,
        }

    # -------------------------------------------------------------------------
    # SMS-009 — Student update
    # -------------------------------------------------------------------------

    @staticmethod
    def update(student_id: int, data: dict, role: str = "admin"):
        """
        Update student record.

        Admin can update any allowed field.
        Students can only update phone and address on their own record.
        Returns (student_dict, None) or (None, error_dict).
        """
        student = get_db().query(Student).filter_by(id=student_id, is_active=True).first()
        if not student:
            return None, {"message": "Student not found", "status": 404}

        if role == "admin":
            allowed = [
                "first_name",
                "last_name",
                "date_of_birth",
                "gender",
                "blood_group",
                "address",
                "phone",
                "photo_url",
            ]
        else:
            # student self-service
            allowed = ["phone", "address"]

        for field in allowed:
            if field in data:
                setattr(student, field, data[field])

        get_db().commit()
        return student.to_dict(), None

    # -------------------------------------------------------------------------
    # SMS-013 — Soft delete
    # -------------------------------------------------------------------------

    @staticmethod
    def delete(student_id: int):
        student = get_db().query(Student).filter_by(id=student_id, is_active=True).first()
        if not student:
            return False, {"message": "Student not found", "status": 404}
        student.is_active = False
        get_db().commit()
        return True, None

    # -------------------------------------------------------------------------
    # SMS-013 — Status / leaving date update
    # -------------------------------------------------------------------------

    @staticmethod
    def update_status(student_id: int, data: dict):
        student = get_db().query(Student).filter_by(id=student_id, is_active=True).first()
        if not student:
            return None, {"message": "Student not found", "status": 404}
        student.status = data["status"]
        if data.get("leaving_date"):
            student.leaving_date = data["leaving_date"]
        get_db().commit()
        return student.to_dict(), None

    # -------------------------------------------------------------------------
    # SMS-010 — Parent linking
    # -------------------------------------------------------------------------

    @staticmethod
    def link_parent(student_id: int, parent_id: int, is_primary: bool):
        student = get_db().query(Student).filter_by(id=student_id, is_active=True).first()
        if not student:
            return None, {"message": "Student not found", "status": 404}

        parent = get_db().query(Parent).filter_by(id=parent_id, is_active=True).first()
        if not parent:
            return None, {"message": "Parent not found", "status": 404}

        # Check if already linked
        existing = (
            get_db()
            .execute(
                select(student_parent).where(
                    student_parent.c.student_id == student_id,
                    student_parent.c.parent_id == parent_id,
                )
            )
            .first()
        )
        if existing:
            return None, {"message": "Parent already linked to this student", "status": 409}

        get_db().execute(
            student_parent.insert().values(
                student_id=student_id,
                parent_id=parent_id,
                is_primary_contact=is_primary,
            )
        )
        get_db().commit()
        return parent.to_dict(), None

    @staticmethod
    def unlink_parent(student_id: int, parent_id: int):
        student = get_db().query(Student).filter_by(id=student_id, is_active=True).first()
        if not student:
            return False, {"message": "Student not found", "status": 404}

        result = get_db().execute(
            student_parent.delete().where(
                student_parent.c.student_id == student_id,
                student_parent.c.parent_id == parent_id,
            )
        )
        if result.rowcount == 0:
            return False, {"message": "Parent-student link not found", "status": 404}

        get_db().commit()
        return True, None

    @staticmethod
    def get_parents(student_id: int):
        student = get_db().query(Student).filter_by(id=student_id, is_active=True).first()
        if not student:
            return None, {"message": "Student not found", "status": 404}

        rows = (
            get_db()
            .execute(
                select(Parent, student_parent.c.is_primary_contact)
                .join(student_parent, Parent.id == student_parent.c.parent_id)
                .where(student_parent.c.student_id == student_id)
            )
            .all()
        )

        result = []
        for parent, is_primary in rows:
            d = parent.to_dict()
            d["is_primary_contact"] = is_primary
            result.append(d)

        return result, None

    # -------------------------------------------------------------------------
    # SMS-011 — Student transfer
    # -------------------------------------------------------------------------

    @staticmethod
    def transfer(student_id: int, data: dict):
        """
        Transfer student to a new section.

        Closes the current StudentSection row and opens a new one.
        data keys: new_section_id (int), effective_date (date), reason (str).
        """
        student = get_db().query(Student).filter_by(id=student_id, is_active=True).first()
        if not student:
            return None, {"message": "Student not found", "status": 404}

        effective_date = data["effective_date"]
        new_section_id = data["new_section_id"]

        # Close current enrollment
        current = get_db().query(StudentSection).filter_by(student_id=student_id, is_current=True).first()
        if current:
            current.is_current = False
            current.end_date = effective_date

        # Determine academic year from effective_date
        year = effective_date.year
        month = effective_date.month
        academic_year = f"{year}-{year + 1}" if month >= 6 else f"{year - 1}-{year}"

        new_enrollment = StudentSection(
            student_id=student_id,
            section_id=new_section_id,
            academic_year=academic_year,
            start_date=effective_date,
            is_current=True,
        )
        get_db().add(new_enrollment)
        get_db().commit()
        return new_enrollment.to_dict(), None

    # -------------------------------------------------------------------------
    # SMS-012 — Document upload
    # -------------------------------------------------------------------------

    @staticmethod
    def upload_document(student_id: int, document_type: str, file, uploaded_by: int):
        """
        Save uploaded document to disk and create StudentDocument record.

        Returns (doc_dict, None) or (None, error_dict).
        """
        student = get_db().query(Student).filter_by(id=student_id, is_active=True).first()
        if not student:
            return None, {"message": "Student not found", "status": 404}

        if not file or not file.filename:
            return None, {"message": "No file provided", "status": 400}

        if not _allowed_doc(file.filename):
            return None, {
                "message": "Invalid file type. Allowed: PDF, JPG, JPEG, PNG",
                "status": 400,
            }

        # Read content once to check size (werkzeug stream)
        content = file.read()
        if len(content) > MAX_DOC_BYTES:
            return None, {"message": "File exceeds maximum size of 5 MB", "status": 400}

        upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "students", str(student_id))
        os.makedirs(upload_dir, exist_ok=True)

        ext = file.filename.rsplit(".", 1)[1].lower()
        safe_name = secure_filename(f"{document_type}_{secrets.token_hex(8)}.{ext}")
        abs_path = os.path.join(upload_dir, safe_name)
        with open(abs_path, "wb") as fh:
            fh.write(content)

        rel_path = os.path.join("students", str(student_id), safe_name)

        doc = StudentDocument(
            student_id=student_id,
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
    def list_documents(student_id: int):
        student = get_db().query(Student).filter_by(id=student_id, is_active=True).first()
        if not student:
            return None, {"message": "Student not found", "status": 404}

        docs = (
            get_db()
            .query(StudentDocument)
            .filter_by(student_id=student_id, is_active=True)
            .order_by(StudentDocument.created_at.desc())
            .all()
        )
        return [d.to_dict() for d in docs], None

    @staticmethod
    def delete_document(student_id: int, doc_id: int):
        doc = get_db().query(StudentDocument).filter_by(id=doc_id, student_id=student_id, is_active=True).first()
        if not doc:
            return False, {"message": "Document not found", "status": 404}
        doc.is_active = False
        get_db().commit()
        return True, None
