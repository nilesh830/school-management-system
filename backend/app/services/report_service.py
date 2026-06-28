"""
Reports & Analytics services.

SMS-057  attendance_report — per-student attendance counts + class average.
SMS-058  grades_report     — per-student exam results + grade distribution.
SMS-059  fees_report       — collected vs pending per fee type + defaulters.

All queries use the tenant session via get_db(); no raw SQL. Aggregates are
defensive against empty data and never divide by zero.
"""

from collections import defaultdict
from datetime import datetime, date
from io import BytesIO

from app.utils.tenant import get_db
from app.utils.excel import build_xlsx
from app.models.attendance import Attendance
from app.models.section import Section
from app.models.student import Student
from app.models.student_section import StudentSection
from app.models.exam import Exam
from app.models.exam_result import ExamResult
from app.models.subject import Subject
from app.models.fee_structure import FeeStructure
from app.models.fee_record import FeeRecord
from app.models.fee_payment import FeePayment


_COUNTED_STATUSES = ("present", "absent", "late")


def _parse_date(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()


class ReportService:

    # -----------------------------------------------------------------------
    # SMS-057 — Attendance Analytics Report
    # -----------------------------------------------------------------------

    @staticmethod
    def attendance_report(section_id: int, from_date_str: str, to_date_str: str):
        """
        Per-student attendance breakdown for a section over [from_date, to_date].

        Returns (result_dict, None) on success or (None, error_dict) on failure.
        error_dict has 'message' and 'status'. Validates dates (400) and that the
        section exists (404).
        """
        db = get_db()

        try:
            from_date = _parse_date(from_date_str)
            to_date = _parse_date(to_date_str)
        except (ValueError, TypeError):
            return None, {
                "message": "from_date and to_date must be valid YYYY-MM-DD dates",
                "status": 400,
            }

        if from_date > to_date:
            return None, {
                "message": "from_date must not be after to_date",
                "status": 400,
            }

        section = db.query(Section).filter_by(id=section_id).first()
        if not section:
            return None, {
                "message": f"Section {section_id} not found",
                "status": 404,
            }

        rows = (
            db.query(Attendance)
            .filter(
                Attendance.section_id == section_id,
                Attendance.date >= from_date,
                Attendance.date <= to_date,
            )
            .order_by(Attendance.student_id, Attendance.date)
            .all()
        )

        # Resolve student names for everyone with at least one row
        student_ids = {r.student_id for r in rows}
        names = (
            {s.id: f"{s.first_name} {s.last_name}" for s in db.query(Student).filter(Student.id.in_(student_ids)).all()}
            if student_ids
            else {}
        )

        summary = {}
        for row in rows:
            sid = row.student_id
            if sid not in summary:
                summary[sid] = {
                    "student_id": sid,
                    "name": names.get(sid, f"Student {sid}"),
                    "present": 0,
                    "absent": 0,
                    "late": 0,
                    "total": 0,
                    "percentage": 0.0,
                }
            entry = summary[sid]
            if row.status in entry:
                entry[row.status] += 1
            # total counts only present/absent/late as attendance opportunities
            if row.status in _COUNTED_STATUSES:
                entry["total"] += 1

        # Per-student percentages (present + late counted as attended)
        pct_values = []
        for entry in summary.values():
            total = entry["total"]
            attended = entry["present"] + entry["late"]
            pct = round((attended / total) * 100, 2) if total else 0.0
            entry["percentage"] = pct
            if total:
                pct_values.append(pct)

        class_average = round(sum(pct_values) / len(pct_values), 2) if pct_values else 0.0

        return {
            "section_id": section_id,
            "from_date": from_date_str,
            "to_date": to_date_str,
            "students": list(summary.values()),
            "student_count": len(summary),
            "class_average": class_average,
        }, None

    # -----------------------------------------------------------------------
    # SMS-058 — Academic Performance Report
    # -----------------------------------------------------------------------

    @staticmethod
    def grades_report(exam_id: int, section_id: int = None):
        """
        All students' results for an exam, with per-subject breakdown and an
        overall (percentage / grade / gpa) per student, plus grade-distribution
        counts over the overall grades.

        Returns (result_dict, None) on success or (None, error_dict) on failure.
        Validates that the exam exists (404). section_id is an optional filter
        on currently-enrolled students.
        """
        from app.services.exam_service import ExamService

        db = get_db()

        exam = db.query(Exam).filter_by(id=exam_id).first()
        if not exam:
            return None, {"message": f"Exam {exam_id} not found", "status": 404}

        # Optional section filter — restrict to students currently in that section.
        allowed_student_ids = None
        if section_id is not None:
            section = db.query(Section).filter_by(id=section_id).first()
            if not section:
                return None, {
                    "message": f"Section {section_id} not found",
                    "status": 404,
                }
            allowed_student_ids = {
                ss.student_id for ss in db.query(StudentSection).filter_by(section_id=section_id, is_current=True).all()
            }

        rows = (
            db.query(ExamResult, Subject, Student)
            .join(Subject, ExamResult.subject_id == Subject.id)
            .join(Student, ExamResult.student_id == Student.id)
            .filter(ExamResult.exam_id == exam_id)
            .all()
        )

        # Group by student
        student_map = defaultdict(list)
        student_obj = {}
        for result, subject, student in rows:
            if allowed_student_ids is not None and student.id not in allowed_student_ids:
                continue
            student_map[student.id].append((result, subject))
            student_obj[student.id] = student

        students = []
        grade_distribution = defaultdict(int)

        for student_id, entries in student_map.items():
            student = student_obj[student_id]
            subjects = []
            gpa_values = []
            total_obtained = None
            total_max = 0

            for result, subject in entries:
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
                        "percentage": pct,
                    }
                )
                total_max += subject.max_marks
                if mo is not None:
                    total_obtained = (total_obtained or 0) + mo
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

            if overall_grade is not None:
                grade_distribution[overall_grade] += 1

            students.append(
                {
                    "student_id": student_id,
                    "name": f"{student.first_name} {student.last_name}",
                    "admission_no": student.admission_no,
                    "subjects": subjects,
                    "overall_percentage": overall_percentage,
                    "overall_grade": overall_grade,
                    "overall_gpa": overall_gpa,
                }
            )

        students.sort(key=lambda s: s["student_id"])

        return {
            "exam_id": exam_id,
            "exam_name": exam.name,
            "section_id": section_id,
            "students": students,
            "student_count": len(students),
            "grade_distribution": dict(grade_distribution),
        }, None

    # -----------------------------------------------------------------------
    # SMS-059 — Fee Collection Report
    # -----------------------------------------------------------------------

    @staticmethod
    def fees_report(class_id: int = None, academic_year_id: int = None):
        """
        Collected vs pending totals grouped by fee type/structure, overall
        totals, and a defaulters list.

        Returns (result_dict, None). class_id / academic_year_id are optional
        filters on the FeeStructure. Reuses FeeService.get_defaulters for the
        defaulters list.
        """
        from app.services.fee_service import FeeService

        db = get_db()

        # Auto: catch up recurring monthly dues so the report reflects the
        # current month before aggregating. Best-effort — never break the report.
        try:
            FeeService.run_recurring_catchup()
        except Exception:
            db.rollback()

        # FeeStructures in scope
        fs_query = db.query(FeeStructure)
        if class_id is not None:
            fs_query = fs_query.filter(FeeStructure.class_id == class_id)
        if academic_year_id is not None:
            fs_query = fs_query.filter(FeeStructure.academic_year_id == academic_year_id)
        structures = fs_query.all()

        by_type = []
        total_collected = 0.0
        total_pending = 0.0

        for fs in structures:
            records = db.query(FeeRecord).filter(FeeRecord.fee_structure_id == fs.id).all()
            collected = 0.0
            pending = 0.0
            for rec in records:
                paid = sum(float(p.amount_paid) for p in db.query(FeePayment).filter_by(fee_record_id=rec.id).all())
                collected += paid
                if rec.status in ("pending", "partial"):
                    balance = float(rec.net_amount) - paid
                    if balance > 0:
                        pending += balance

            by_type.append(
                {
                    "fee_structure_id": fs.id,
                    "fee_type": fs.fee_type,
                    "class_id": fs.class_id,
                    "academic_year_id": fs.academic_year_id,
                    "amount": float(fs.amount) if fs.amount is not None else 0.0,
                    "collected": round(collected, 2),
                    "pending": round(pending, 2),
                    "record_count": len(records),
                }
            )
            total_collected += collected
            total_pending += pending

        defaulters = FeeService.get_defaulters(class_id=class_id)

        return {
            "class_id": class_id,
            "academic_year_id": academic_year_id,
            "by_fee_type": by_type,
            "totals": {
                "collected": round(total_collected, 2),
                "pending": round(total_pending, 2),
            },
            "defaulters": defaulters,
            "defaulters_count": len(defaulters),
        }, None

    # -----------------------------------------------------------------------
    # SMS-060 — Export Reports to PDF / Excel
    #
    # Each exporter calls the corresponding *_report query above, then renders
    # the result as a PDF (xhtml2pdf + Jinja2) or an .xlsx (openpyxl helper).
    # All return (bytes, None) on success or (None, error_dict) on failure;
    # error_dict carries the same {'message', 'status'} envelope used by the
    # report queries so the route can surface 400/404 unchanged.
    # -----------------------------------------------------------------------

    @staticmethod
    def _render_pdf(template_name: str, **context):
        """Render a Jinja2 template to PDF bytes via xhtml2pdf."""
        from flask import render_template
        from xhtml2pdf import pisa

        try:
            html = render_template(template_name, **context)
        except Exception as exc:
            return None, {
                "message": f"Template rendering failed: {exc}",
                "status": 500,
            }

        try:
            buffer = BytesIO()
            result = pisa.CreatePDF(html, dest=buffer)
            if result.err:
                return None, {"message": "PDF generation failed", "status": 500}
            return buffer.getvalue(), None
        except Exception as exc:
            return None, {"message": f"PDF generation error: {exc}", "status": 500}

    # --- Attendance -------------------------------------------------------

    @classmethod
    def export_attendance_pdf(cls, section_id, from_date_str, to_date_str):
        report, err = cls.attendance_report(section_id, from_date_str, to_date_str)
        if err:
            return None, err
        return cls._render_pdf(
            "report_attendance.html",
            report=report,
            generated_date=date.today().strftime("%d %B %Y"),
        )

    @classmethod
    def export_attendance_excel(cls, section_id, from_date_str, to_date_str):
        report, err = cls.attendance_report(section_id, from_date_str, to_date_str)
        if err:
            return None, err
        headers = ["Student", "Present", "Absent", "Late", "Total", "Percentage"]
        rows = [
            [s["name"], s["present"], s["absent"], s["late"], s["total"], s["percentage"]] for s in report["students"]
        ]
        rows.append(["CLASS AVERAGE", "", "", "", "", report["class_average"]])
        return build_xlsx("Attendance Report", headers, rows), None

    # --- Grades -----------------------------------------------------------

    @classmethod
    def export_grades_pdf(cls, exam_id, section_id=None):
        report, err = cls.grades_report(exam_id, section_id)
        if err:
            return None, err
        return cls._render_pdf(
            "report_grades.html",
            report=report,
            generated_date=date.today().strftime("%d %B %Y"),
        )

    @classmethod
    def export_grades_excel(cls, exam_id, section_id=None):
        report, err = cls.grades_report(exam_id, section_id)
        if err:
            return None, err
        headers = ["Student", "Admission No.", "Overall %", "Grade", "GPA"]
        rows = [
            [
                s["name"],
                s["admission_no"],
                s["overall_percentage"],
                s["overall_grade"],
                s["overall_gpa"],
            ]
            for s in report["students"]
        ]
        return build_xlsx("Grades Report", headers, rows), None

    # --- Fees -------------------------------------------------------------

    @classmethod
    def export_fees_pdf(cls, class_id=None, academic_year_id=None):
        report, err = cls.fees_report(class_id, academic_year_id)
        if err:
            return None, err
        return cls._render_pdf(
            "report_fees.html",
            report=report,
            generated_date=date.today().strftime("%d %B %Y"),
        )

    @classmethod
    def export_fees_excel(cls, class_id=None, academic_year_id=None):
        report, err = cls.fees_report(class_id, academic_year_id)
        if err:
            return None, err
        headers = ["Fee Type", "Amount", "Collected", "Pending", "Records"]
        rows = [
            [
                ft["fee_type"],
                ft["amount"],
                ft["collected"],
                ft["pending"],
                ft["record_count"],
            ]
            for ft in report["by_fee_type"]
        ]
        rows.append(
            [
                "TOTALS",
                "",
                report["totals"]["collected"],
                report["totals"]["pending"],
                "",
            ]
        )
        return build_xlsx("Fee Collection Report", headers, rows), None
