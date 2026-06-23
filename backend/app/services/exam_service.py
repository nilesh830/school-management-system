from io import BytesIO

from app.utils.tenant import get_db
from app.models.exam import Exam
from app.models.exam_result import ExamResult
from app.models.subject import Subject
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.teacher_subject import TeacherSubject
from app.models.section import Section
from app.models.academic_year import AcademicYear

VALID_EXAM_TYPES = ("midterm", "final", "unit_test", "practical")


class ExamService:

    @staticmethod
    def create_exam(data: dict, created_by: int):
        """
        Create a new exam definition.

        Returns (exam_dict, None) on success or (None, error_dict) on failure.
        error_dict always contains 'message' and 'status' keys.
        """
        exam_type = data.get("exam_type")
        if exam_type not in VALID_EXAM_TYPES:
            return None, {
                "message": f"Invalid exam_type '{exam_type}'. Must be one of: {', '.join(VALID_EXAM_TYPES)}",
                "status": 422,
            }

        section_id = data.get("section_id")
        section = get_db().query(Section).filter_by(id=section_id, is_active=True).first()
        if not section:
            return None, {
                "message": f"Section {section_id} not found or is inactive",
                "status": 404,
            }

        academic_year_id = data.get("academic_year_id")
        academic_year = get_db().query(AcademicYear).filter_by(id=academic_year_id).first()
        if not academic_year:
            return None, {
                "message": f"AcademicYear {academic_year_id} not found",
                "status": 404,
            }

        name = data.get("name")
        duplicate = (
            get_db()
            .query(Exam)
            .filter_by(
                name=name,
                section_id=section_id,
                academic_year_id=academic_year_id,
            )
            .first()
        )
        if duplicate:
            return None, {
                "message": (
                    f"Exam '{name}' already exists for section {section_id} " f"in academic year {academic_year_id}"
                ),
                "status": 409,
            }

        exam = Exam(
            name=name,
            term=data.get("term"),
            exam_type=exam_type,
            section_id=section_id,
            academic_year_id=academic_year_id,
            conducted_date=data.get("conducted_date"),
            is_active=data.get("is_active", True),
            created_by=created_by,
        )
        get_db().add(exam)
        get_db().commit()
        return exam.to_dict(), None

    @staticmethod
    def get_exams(section_id=None, academic_year_id=None, is_active=None):
        """
        Return a list of exam dicts, optionally filtered.
        """
        query = get_db().query(Exam)
        if section_id is not None:
            query = query.filter_by(section_id=section_id)
        if academic_year_id is not None:
            query = query.filter_by(academic_year_id=academic_year_id)
        if is_active is not None:
            query = query.filter_by(is_active=is_active)
        exams = query.order_by(Exam.created_at.desc()).all()
        return [e.to_dict() for e in exams]

    @staticmethod
    def get_exam(exam_id: int):
        """
        Fetch a single exam by id.

        Returns (exam_dict, None) or (None, {'message': ..., 'status': 404}).
        """
        exam = get_db().query(Exam).filter_by(id=exam_id).first()
        if not exam:
            return None, {"message": f"Exam {exam_id} not found", "status": 404}
        return exam.to_dict(), None

    @staticmethod
    def update_exam(exam_id: int, data: dict):
        """
        Update mutable fields of an exam.

        Allowed fields: name, term, exam_type, conducted_date, is_active.
        Returns (exam_dict, None) or (None, error_dict).
        """
        exam = get_db().query(Exam).filter_by(id=exam_id).first()
        if not exam:
            return None, {"message": f"Exam {exam_id} not found", "status": 404}

        if "exam_type" in data and data["exam_type"] is not None:
            if data["exam_type"] not in VALID_EXAM_TYPES:
                return None, {
                    "message": (
                        f"Invalid exam_type '{data['exam_type']}'. " f"Must be one of: {', '.join(VALID_EXAM_TYPES)}"
                    ),
                    "status": 422,
                }
            exam.exam_type = data["exam_type"]

        if "name" in data and data["name"] is not None:
            exam.name = data["name"]
        if "term" in data and data["term"] is not None:
            exam.term = data["term"]
        if "conducted_date" in data:
            exam.conducted_date = data["conducted_date"]
        if "is_active" in data and data["is_active"] is not None:
            exam.is_active = data["is_active"]

        get_db().commit()
        return exam.to_dict(), None

    # -----------------------------------------------------------------------
    # T-030-02: Grade calculator
    # -----------------------------------------------------------------------

    @staticmethod
    def calculate_grade(marks_obtained: float, max_marks: float) -> tuple[str, float]:
        """
        Return (grade, gpa) from a percentage-based scale.

        Edge case: max_marks == 0 is treated as F / 0.0 to avoid division by zero.
        """
        if max_marks == 0:
            return "F", 0.0

        pct = (marks_obtained / max_marks) * 100

        if pct >= 90:
            return "A+", 4.0
        elif pct >= 80:
            return "A", 3.7
        elif pct >= 70:
            return "B", 3.0
        elif pct >= 60:
            return "C", 2.3
        elif pct >= 50:
            return "D", 1.7
        elif pct >= 40:
            return "E", 1.0
        else:
            return "F", 0.0

    # -----------------------------------------------------------------------
    # T-030-03: Bulk marks entry with upsert
    # -----------------------------------------------------------------------

    @staticmethod
    def enter_marks(
        exam_id: int,
        subject_id: int,
        section_id: int,
        marks_list: list,
        created_by_user_id: int,
        role: str,
    ) -> tuple[dict | None, dict | None]:
        """
        Upsert marks for a list of students for a given exam + subject.

        Returns (result_dict, None) on success or (None, error_dict) on failure.
        error_dict always contains 'message' and 'status' keys.
        """
        session = get_db()

        # 1. Exam must exist and be active
        exam = session.query(Exam).filter_by(id=exam_id, is_active=True).first()
        if not exam:
            return None, {
                "message": f"Exam {exam_id} not found or is inactive",
                "status": 404,
            }

        # 2. Subject must exist
        subject = session.query(Subject).filter_by(id=subject_id).first()
        if not subject:
            return None, {
                "message": f"Subject {subject_id} not found",
                "status": 404,
            }

        # 3. Teacher authorisation: must be assigned to this subject
        if role == "teacher":
            teacher = session.query(Teacher).filter_by(user_id=created_by_user_id).first()
            if not teacher:
                return None, {
                    "message": "Teacher profile not found for this user",
                    "status": 403,
                }
            assignment = (
                session.query(TeacherSubject)
                .filter_by(
                    teacher_id=teacher.id,
                    subject_id=subject_id,
                )
                .first()
            )
            if not assignment:
                return None, {
                    "message": "You are not assigned to teach this subject",
                    "status": 403,
                }

        # 4. Validate all marks_obtained <= subject.max_marks
        max_marks = float(subject.max_marks)
        invalid = [entry["student_id"] for entry in marks_list if float(entry["marks_obtained"]) > max_marks]
        if invalid:
            return None, {
                "message": (f"marks_obtained exceeds max_marks ({max_marks}) " f"for student_id(s): {invalid}"),
                "status": 422,
            }

        # 5. Reject if any result for this batch is already finalised
        student_ids = [e["student_id"] for e in marks_list]
        finalized = (
            session.query(ExamResult)
            .filter(
                ExamResult.exam_id == exam_id,
                ExamResult.subject_id == subject_id,
                ExamResult.student_id.in_(student_ids),
                ExamResult.status == "finalized",
            )
            .first()
        )
        if finalized:
            return None, {
                "message": "Marks are finalized and cannot be edited",
                "status": 409,
            }

        # 6. Upsert each entry
        saved = 0
        for entry in marks_list:
            sid = entry["student_id"]
            mo = float(entry["marks_obtained"])
            grade, gpa = ExamService.calculate_grade(mo, max_marks)

            existing = (
                session.query(ExamResult)
                .filter_by(
                    exam_id=exam_id,
                    student_id=sid,
                    subject_id=subject_id,
                )
                .first()
            )
            if existing:
                existing.marks_obtained = mo
                existing.grade = grade
                existing.gpa = gpa
                existing.created_by = created_by_user_id
            else:
                result = ExamResult(
                    exam_id=exam_id,
                    student_id=sid,
                    subject_id=subject_id,
                    marks_obtained=mo,
                    grade=grade,
                    gpa=gpa,
                    status="draft",
                    created_by=created_by_user_id,
                )
                session.add(result)
            saved += 1

        # Fire low-marks notifications to parents (< 40%)
        for entry in marks_list:
            sid = entry["student_id"]
            mo = float(entry["marks_obtained"])
            max_m = float(subject.max_marks)
            if max_m > 0 and (mo / max_m * 100) < 40:
                from app.models.notification import Notification as _Notification
                from app.models.parent import Parent as _Parent, student_parent as _sp
                from sqlalchemy import select

                student_obj = session.query(Student).filter_by(id=sid).first()
                if student_obj:
                    parent_links = session.execute(select(_sp).where(_sp.c.student_id == sid)).fetchall()
                    for link in parent_links:
                        parent_obj = session.query(_Parent).filter_by(id=link.parent_id).first()
                        if parent_obj:
                            notif = _Notification(
                                user_id=parent_obj.user_id,
                                type="low_marks",
                                title=f"Low Marks Alert: {subject.name}",
                                body=f"{student_obj.first_name} scored {mo}/{max_m} in {subject.name}",
                                reference_id=None,
                                reference_type="exam_result",
                            )
                            session.add(notif)

        session.commit()

        return {
            "saved": saved,
            "exam_id": exam_id,
            "subject_id": subject_id,
        }, None

    # -----------------------------------------------------------------------
    # SMS-034-A: Update a single ExamResult (marks edit workflow)
    # -----------------------------------------------------------------------

    @classmethod
    def update_marks(cls, exam_id: int, result_id: int, marks_obtained: float) -> tuple[dict | None, dict | None]:
        """
        Edit the marks_obtained on a single draft ExamResult row and
        recalculate grade + gpa.

        Returns (result_dict, None) on success or (None, error_dict) on failure.
        error_dict always contains 'message' and 'status' keys.
        """
        session = get_db()

        result = session.query(ExamResult).filter_by(id=result_id).first()
        if not result:
            return None, {"message": "Result not found", "status": 404}

        if result.exam_id != exam_id:
            return None, {
                "message": "Result does not belong to this exam",
                "status": 404,
            }

        if result.status == "finalized":
            return None, {
                "message": "Cannot edit finalized results",
                "status": 409,
            }

        if marks_obtained < 0:
            return None, {"message": "marks_obtained must be >= 0", "status": 422}

        subject = session.query(Subject).filter_by(id=result.subject_id).first()
        max_marks = float(subject.max_marks) if subject else 0.0

        if marks_obtained > max_marks:
            return None, {
                "message": f"Marks cannot exceed {max_marks}",
                "status": 422,
            }

        grade, gpa = cls.calculate_grade(marks_obtained, max_marks)
        result.marks_obtained = marks_obtained
        result.grade = grade
        result.gpa = gpa
        session.commit()

        return result.to_dict(), None

    # -----------------------------------------------------------------------
    # SMS-034-B: Finalize all draft results for an exam
    # -----------------------------------------------------------------------

    @staticmethod
    def finalize_exam(exam_id: int) -> tuple[dict | None, dict | None]:
        """
        Bulk-transition all draft ExamResult rows for the given exam to
        'finalized'.

        Returns ({'finalized_count': N}, None) on success or (None, error_dict)
        on failure.  error_dict always contains 'message' and 'status' keys.
        """
        session = get_db()

        exam = session.query(Exam).filter_by(id=exam_id).first()
        if not exam:
            return None, {"message": f"Exam {exam_id} not found", "status": 404}

        drafts = (
            session.query(ExamResult)
            .filter(
                ExamResult.exam_id == exam_id,
                ExamResult.status == "draft",
            )
            .all()
        )

        if not drafts:
            return None, {
                "message": "No draft results to finalize",
                "status": 400,
            }

        for row in drafts:
            row.status = "finalized"

        session.commit()

        return {"finalized_count": len(drafts)}, None

    # -----------------------------------------------------------------------
    # T-031-01: Per-student subject-by-subject result breakdown + overall GPA
    # -----------------------------------------------------------------------

    @staticmethod
    def get_student_results(exam_id: int, student_id: int) -> tuple[dict, None]:
        """
        Return a subject-by-subject result breakdown for one student in one exam.

        Always returns (result_dict, None) — an empty subjects list is valid when
        no marks have been entered yet.
        """
        session = get_db()

        rows = (
            session.query(ExamResult, Subject)
            .join(Subject, ExamResult.subject_id == Subject.id)
            .filter(
                ExamResult.exam_id == exam_id,
                ExamResult.student_id == student_id,
            )
            .all()
        )

        subjects = []
        total_marks_obtained = None
        total_max_marks = 0
        gpa_values = []

        for result, subject in rows:
            mo = float(result.marks_obtained) if result.marks_obtained is not None else None
            pct = round((mo / subject.max_marks) * 100, 2) if mo is not None and subject.max_marks else None

            subjects.append(
                {
                    "subject_id": subject.id,
                    "subject_name": subject.name,
                    "subject_code": subject.code,
                    "max_marks": subject.max_marks,
                    "marks_obtained": mo,
                    "grade": result.grade,
                    "gpa": float(result.gpa) if result.gpa is not None else None,
                    "status": result.status,
                    "percentage": pct,
                }
            )

            total_max_marks += subject.max_marks
            if mo is not None:
                total_marks_obtained = (total_marks_obtained or 0) + mo
            if result.gpa is not None:
                gpa_values.append(float(result.gpa))

        # Aggregates — all None when no marks entered
        overall_gpa = round(sum(gpa_values) / len(gpa_values), 2) if gpa_values else None
        overall_percentage = (
            round((total_marks_obtained / total_max_marks) * 100, 2)
            if total_marks_obtained is not None and total_max_marks
            else None
        )
        overall_grade = (
            ExamService.calculate_grade(total_marks_obtained, total_max_marks)[0]
            if total_marks_obtained is not None and total_max_marks
            else None
        )

        return {
            "exam_id": exam_id,
            "student_id": student_id,
            "subjects": subjects,
            "overall_gpa": overall_gpa,
            "total_marks_obtained": total_marks_obtained,
            "total_max_marks": total_max_marks,
            "overall_percentage": overall_percentage,
            "overall_grade": overall_grade,
        }, None

    # -----------------------------------------------------------------------
    # T-031-02: All-student result summary for one exam (admin / teacher view)
    # -----------------------------------------------------------------------

    @staticmethod
    def get_all_results(exam_id: int) -> dict:
        """
        Return a per-student summary for every student who has at least one
        ExamResult row for this exam.
        """
        session = get_db()

        rows = (
            session.query(ExamResult, Subject)
            .join(Subject, ExamResult.subject_id == Subject.id)
            .filter(ExamResult.exam_id == exam_id)
            .all()
        )

        # Group rows by student_id
        from collections import defaultdict

        student_map: dict[int, list] = defaultdict(list)
        for result, subject in rows:
            student_map[result.student_id].append((result, subject))

        summaries = []
        for student_id, entries in student_map.items():
            gpa_values = []
            total_obtained = None
            total_max = 0
            subject_count = 0

            for result, subject in entries:
                total_max += subject.max_marks
                mo = float(result.marks_obtained) if result.marks_obtained is not None else None
                if mo is not None:
                    total_obtained = (total_obtained or 0) + mo
                    subject_count += 1
                if result.gpa is not None:
                    gpa_values.append(float(result.gpa))

            overall_gpa = round(sum(gpa_values) / len(gpa_values), 2) if gpa_values else None
            overall_percentage = (
                round((total_obtained / total_max) * 100, 2) if total_obtained is not None and total_max else None
            )
            overall_grade = (
                ExamService.calculate_grade(total_obtained, total_max)[0]
                if total_obtained is not None and total_max
                else None
            )

            summaries.append(
                {
                    "student_id": student_id,
                    "overall_gpa": overall_gpa,
                    "overall_percentage": overall_percentage,
                    "overall_grade": overall_grade,
                    "subject_count": subject_count,
                }
            )

        return {
            "exam_id": exam_id,
            "results": summaries,
        }

    # -----------------------------------------------------------------------
    # T-032-03: Generate a PDF report card for one student / one exam
    # -----------------------------------------------------------------------

    @staticmethod
    def generate_report_card_pdf(exam_id: int, student_id: int) -> tuple[bytes | None, dict | None]:
        """
        Render the report_card.html Jinja2 template with exam + student data,
        then convert it to PDF bytes via xhtml2pdf.

        Returns (pdf_bytes, None) on success or (None, error_dict) on failure.
        error_dict always contains 'message' and 'status' keys.
        """
        from datetime import date
        from flask import render_template
        from xhtml2pdf import pisa

        session = get_db()

        # 1. Fetch Exam
        exam = session.query(Exam).filter_by(id=exam_id).first()
        if not exam:
            return None, {"message": f"Exam {exam_id} not found", "status": 404}

        # 2. Fetch Student
        student = session.query(Student).filter_by(id=student_id).first()
        if not student:
            return None, {"message": f"Student {student_id} not found", "status": 404}

        # 3. Fetch Section for display name
        section = session.query(Section).filter_by(id=exam.section_id).first()
        if section and section.class_:
            section_name = f"{section.class_.name} {section.name}"
        elif section:
            section_name = section.name
        else:
            section_name = "—"

        # 4. Fetch AcademicYear for name
        academic_year = session.query(AcademicYear).filter_by(id=exam.academic_year_id).first()
        academic_year_name = academic_year.name if academic_year else "—"

        # 5. Get subject-wise result breakdown
        results, _ = ExamService.get_student_results(exam_id, student_id)

        # 6. Build the template context
        generated_date = date.today().strftime("%d %B %Y")
        context = {
            "student": {
                "first_name": student.first_name,
                "last_name": student.last_name,
                "admission_no": student.admission_no,
            },
            "exam": {
                "name": exam.name,
                "exam_type": exam.exam_type,
                "term": exam.term,
                "conducted_date": (exam.conducted_date.isoformat() if exam.conducted_date else None),
            },
            "section_name": section_name,
            "academic_year": academic_year_name,
            "results": results,
            "generated_date": generated_date,
        }

        # 7. Render HTML via Flask's template engine
        try:
            html = render_template("report_card.html", **context)
        except Exception as exc:
            return None, {
                "message": f"Template rendering failed: {exc}",
                "status": 500,
            }

        # 8. Convert HTML to PDF bytes
        try:
            buffer = BytesIO()
            result = pisa.CreatePDF(html, dest=buffer)
            if result.err:
                return None, {
                    "message": "PDF generation failed",
                    "status": 500,
                }
            return buffer.getvalue(), None
        except Exception as exc:
            return None, {
                "message": f"PDF generation error: {exc}",
                "status": 500,
            }
