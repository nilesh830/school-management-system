from flask import abort

from app.utils.tenant import get_db
from app.models.parent import Parent, student_parent
from app.models.student import Student
from app.models.leave_application import LeaveApplication
from app.models.notification import Notification
from app.models.attendance import Attendance
from app.models.fee_record import FeeRecord
from app.models.fee_payment import FeePayment
from app.models.exam import Exam
from app.models.exam_result import ExamResult
from app.models.subject import Subject
from app.models.student_section import StudentSection
from app.models.section import Section
from app.models.teacher import Teacher
from app.models.user import User
from app.models.parent_message import MessageThread, ParentMessage
from datetime import datetime, date
from sqlalchemy import func, extract


def _percentage_to_grade(pct: float) -> str:
    """Convert a percentage score to a letter grade."""
    if pct >= 90:
        return "A+"
    if pct >= 80:
        return "A"
    if pct >= 70:
        return "B+"
    if pct >= 60:
        return "B"
    if pct >= 50:
        return "C"
    if pct >= 40:
        return "D"
    return "F"


class ParentPortalService:

    @staticmethod
    def _verify_child_access(parent_id: int, child_id: int) -> Student:
        """Aborts 403 if this parent does not own the given child. Always call before any child data access."""
        link = get_db().query(student_parent).filter_by(parent_id=parent_id, student_id=child_id).first()
        if not link:
            abort(403, description="Access denied to this student's data")
        student = get_db().query(Student).filter_by(id=child_id, is_active=True).first()
        if not student:
            abort(404, description="Student not found")
        return student

    @staticmethod
    def get_children(parent_id: int) -> list:
        parent = get_db().query(Parent).filter_by(id=parent_id, is_active=True).first()
        if not parent:
            abort(404)
        return [s.to_dict() for s in parent.students.filter_by(is_active=True).all()]

    @staticmethod
    def get_notices(parent_id: int) -> list:
        """SMS-045 — published, non-expired announcements targeted to the
        'parent' role OR to any of this parent's children's classes."""
        from app.services.announcement_service import AnnouncementService

        parent = get_db().query(Parent).filter_by(id=parent_id, is_active=True).first()
        if not parent:
            abort(404)
        student_ids = [s.id for s in parent.students.filter_by(is_active=True).all()]
        class_ids = list(AnnouncementService._student_class_ids(student_ids))
        return AnnouncementService.get_for_user("parent", class_ids)

    @staticmethod
    def get_dashboard(parent_id: int) -> dict:
        parent = get_db().query(Parent).filter_by(id=parent_id, is_active=True).first()
        if not parent:
            abort(404)
        children_data = []
        for child in parent.students.filter_by(is_active=True).all():
            children_data.append(
                {
                    "student": child.to_dict(),
                    "attendance_summary": ParentPortalService._get_attendance_summary(child.id),
                    "pending_fees": ParentPortalService._get_pending_fees(child.id),
                    "recent_grades": ParentPortalService._get_recent_grades(child.id),
                }
            )
        unread_notifications = get_db().query(Notification).filter_by(user_id=parent.user_id, is_read=False).count()
        return {
            "parent": parent.to_dict(),
            "children": children_data,
            "unread_notifications": unread_notifications,
        }

    @staticmethod
    def _get_attendance_summary(student_id: int) -> dict:
        today = date.today()
        rows = (
            get_db()
            .query(Attendance.status, func.count(Attendance.id).label("cnt"))
            .filter(
                Attendance.student_id == student_id,
                extract("month", Attendance.date) == today.month,
                extract("year", Attendance.date) == today.year,
            )
            .group_by(Attendance.status)
            .all()
        )
        counts = {r.status: r.cnt for r in rows}
        present = counts.get("present", 0)
        absent = counts.get("absent", 0)
        late = counts.get("late", 0)
        total = present + absent + late
        percentage = round(present / total * 100, 1) if total > 0 else 0.0
        return {
            "month": today.month,
            "year": today.year,
            "present": present,
            "absent": absent,
            "late": late,
            "percentage": percentage,
        }

    @staticmethod
    def _get_pending_fees(student_id: int) -> dict:
        # FeeRecord status values: pending, paid, partial, waived
        # "pending" and "partial" represent outstanding balances.
        result = (
            get_db()
            .query(func.coalesce(func.sum(FeeRecord.net_amount), 0.0))
            .filter(
                FeeRecord.student_id == student_id,
                FeeRecord.status.in_(["pending", "partial"]),
            )
            .scalar()
        )
        total_due = float(result) if result is not None else 0.0

        overdue_count = (
            get_db()
            .query(func.count(FeeRecord.id))
            .filter(
                FeeRecord.student_id == student_id,
                FeeRecord.status.in_(["pending", "partial"]),
                FeeRecord.due_date < date.today(),
            )
            .scalar()
        ) or 0

        return {"total_due": total_due, "overdue_count": overdue_count}

    @staticmethod
    def _get_recent_grades(student_id: int) -> dict | None:
        # Find the most recent exam this student has results for
        latest_row = (
            get_db()
            .query(ExamResult.exam_id)
            .join(Exam, Exam.id == ExamResult.exam_id)
            .filter(ExamResult.student_id == student_id)
            .order_by(Exam.conducted_date.desc().nullslast(), Exam.id.desc())
            .limit(1)
            .first()
        )
        if not latest_row:
            return None

        exam_id = latest_row.exam_id
        exam = get_db().get(Exam, exam_id)

        results = (
            get_db()
            .query(ExamResult)
            .filter(
                ExamResult.exam_id == exam_id,
                ExamResult.student_id == student_id,
                ExamResult.marks_obtained.isnot(None),
            )
            .all()
        )
        if not results:
            return None

        marks_list = [float(r.marks_obtained) for r in results]
        avg_marks = round(sum(marks_list) / len(marks_list), 1)
        # Use the grade from the first result as overall indicator
        overall_grade = results[0].grade or "N/A"

        return {
            "exam": exam.name,
            "average_marks": avg_marks,
            "grade": overall_grade,
        }

    @staticmethod
    def get_child_attendance(parent_id: int, child_id: int, month: int = None, year: int = None) -> dict:
        ParentPortalService._verify_child_access(parent_id, child_id)
        today = date.today()
        month = month or today.month
        year = year or today.year

        records = (
            get_db()
            .query(Attendance)
            .filter(
                Attendance.student_id == child_id,
                extract("month", Attendance.date) == month,
                extract("year", Attendance.date) == year,
            )
            .order_by(Attendance.date.asc())
            .all()
        )

        present = sum(1 for r in records if r.status == "present")
        absent = sum(1 for r in records if r.status == "absent")
        late = sum(1 for r in records if r.status == "late")
        total = present + absent + late
        percentage = round(present / total * 100, 1) if total > 0 else 0.0

        return {
            "student_id": child_id,
            "month": month,
            "year": year,
            "records": [{"date": r.date.isoformat(), "status": r.status} for r in records],
            "summary": {
                "present": present,
                "absent": absent,
                "late": late,
                "holidays": 0,
                "percentage": percentage,
            },
        }

    @staticmethod
    def get_child_grades(parent_id: int, child_id: int) -> dict:
        ParentPortalService._verify_child_access(parent_id, child_id)

        # Get all distinct exam IDs for this student
        exam_ids = get_db().query(ExamResult.exam_id).filter(ExamResult.student_id == child_id).distinct().all()
        exam_ids = [row.exam_id for row in exam_ids]

        exams_data = []
        for exam_id in exam_ids:
            exam = get_db().get(Exam, exam_id)
            if not exam:
                continue

            results = (
                get_db()
                .query(ExamResult, Subject)
                .join(Subject, Subject.id == ExamResult.subject_id)
                .filter(
                    ExamResult.exam_id == exam_id,
                    ExamResult.student_id == child_id,
                )
                .all()
            )
            if not results:
                continue

            subjects_data = []
            marks_pcts = []
            gpas = []
            for result, subject in results:
                marks = float(result.marks_obtained) if result.marks_obtained is not None else 0.0
                max_marks = float(subject.max_marks) if subject.max_marks else 100.0
                pct = round(marks / max_marks * 100, 1) if max_marks > 0 else 0.0
                marks_pcts.append(pct)
                if result.gpa is not None:
                    gpas.append(float(result.gpa))
                subjects_data.append(
                    {
                        "subject_id": subject.id,
                        "subject_name": subject.name,
                        "marks_obtained": marks,
                        "max_marks": max_marks,
                        "grade": result.grade or "N/A",
                    }
                )

            avg_pct = round(sum(marks_pcts) / len(marks_pcts), 1) if marks_pcts else 0.0
            avg_gpa = round(sum(gpas) / len(gpas), 2) if gpas else 0.0
            # Derive overall grade from average percentage
            overall_grade = _percentage_to_grade(avg_pct)

            exams_data.append(
                {
                    "exam_id": exam.id,
                    "exam_name": exam.name,
                    "term": exam.term,
                    "subjects": subjects_data,
                    "average_percentage": avg_pct,
                    "overall_grade": overall_grade,
                    "gpa": avg_gpa,
                }
            )

        return {"student_id": child_id, "exams": exams_data}

    @staticmethod
    def get_child_fees(parent_id: int, child_id: int) -> dict:
        ParentPortalService._verify_child_access(parent_id, child_id)

        fee_records = (
            get_db().query(FeeRecord).filter(FeeRecord.student_id == child_id).order_by(FeeRecord.due_date.desc()).all()
        )

        # Total still owed (all non-paid records)
        total_due = sum(float(r.net_amount) for r in fee_records if r.status != "paid" and r.net_amount is not None)

        # Total ever paid — sum all FeePayment rows for this student's fee records
        fee_record_ids = [r.id for r in fee_records]
        if fee_record_ids:
            total_paid_result = (
                get_db()
                .query(func.coalesce(func.sum(FeePayment.amount_paid), 0.0))
                .filter(FeePayment.fee_record_id.in_(fee_record_ids))
                .scalar()
            )
            total_paid = float(total_paid_result) if total_paid_result is not None else 0.0
        else:
            total_paid = 0.0

        records_data = []
        for r in fee_records:
            # Most recent payment for this fee record
            latest_payment = (
                get_db()
                .query(FeePayment)
                .filter(FeePayment.fee_record_id == r.id)
                .order_by(FeePayment.created_at.desc())
                .first()
            )
            records_data.append(
                {
                    "id": r.id,
                    "fee_type": r.fee_structure.fee_type if r.fee_structure else "",
                    "amount": float(r.amount),
                    "net_amount": float(r.net_amount),
                    "due_date": r.due_date.isoformat() if r.due_date else None,
                    "status": r.status,
                    "payment_id": latest_payment.id if latest_payment else None,
                    "receipt_no": latest_payment.receipt_no if latest_payment else None,
                }
            )

        return {
            "student_id": child_id,
            "total_due": total_due,
            "total_paid": total_paid,
            "records": records_data,
        }


class LeaveService:

    @staticmethod
    def submit(parent_id: int, data: dict) -> tuple:
        # 1. Parse dates first
        from_date = datetime.strptime(data["from_date"], "%Y-%m-%d").date()
        to_date = datetime.strptime(data["to_date"], "%Y-%m-%d").date()

        # 2. Validate from_date >= today
        if from_date < date.today():
            return None, {"message": "Cannot apply leave for past dates", "status": 422}

        # 3. Validate to_date >= from_date
        if to_date < from_date:
            return None, {"message": "End date must be after start date", "status": 422}

        # 4. Check parent-child link
        child_id = data.get("student_id")
        link = get_db().query(student_parent).filter_by(parent_id=parent_id, student_id=child_id).first()
        if not link:
            return None, {"message": "You are not linked to this student", "status": 403}

        # 5. Validate required fields
        reason = data.get("reason")
        if not reason:
            return None, {"message": "reason is required", "status": 400}

        # 6. Create and commit LeaveApplication
        leave = LeaveApplication(
            student_id=child_id,
            parent_id=parent_id,
            from_date=from_date,
            to_date=to_date,
            reason=reason,
            leave_type=data.get("leave_type", "personal"),
        )
        get_db().add(leave)
        get_db().commit()

        # 6. Fire notifications to class teacher and all admins
        student = get_db().query(Student).filter_by(id=child_id).first()
        title = f"Leave Application: {student.first_name} {student.last_name}"
        body = f"{leave.duration_days}-day {leave.leave_type} leave requested from {leave.from_date}"

        recipient_user_ids = []

        # Find class teacher via student's current section
        ss = get_db().query(StudentSection).filter_by(student_id=child_id, is_current=True).first()
        if ss:
            section = get_db().query(Section).filter_by(id=ss.section_id).first()
            if section and section.class_teacher_id:
                teacher = get_db().query(Teacher).filter_by(id=section.class_teacher_id).first()
                if teacher:
                    recipient_user_ids.append(teacher.user_id)

        # All admin users
        admin_users = get_db().query(User).filter_by(role="admin").all()
        for au in admin_users:
            recipient_user_ids.append(au.id)

        for uid in recipient_user_ids:
            NotificationService.create(uid, "leave", title, body, reference_id=leave.id, reference_type="leave")

        return leave.to_dict(), None

    @staticmethod
    def get_by_parent(parent_id: int) -> list:
        leaves = (
            get_db()
            .query(LeaveApplication)
            .filter_by(parent_id=parent_id)
            .order_by(LeaveApplication.created_at.desc())
            .all()
        )
        return [leave.to_dict() for leave in leaves]

    @staticmethod
    def review(leave_id: int, reviewer_user_id: int, status: str, remarks: str = None) -> tuple:
        leave = get_db().get(LeaveApplication, leave_id)
        if not leave:
            abort(404)
        if status not in ("approved", "rejected"):
            return None, {"message": "Invalid status", "status": 400}
        leave.status = status
        leave.reviewed_by = reviewer_user_id
        leave.reviewed_at = datetime.utcnow()
        leave.reviewer_remarks = remarks
        get_db().commit()

        # Notify the parent
        parent = leave.parent
        parent_user_id = parent.user_id
        notif_title = f"Leave {status.capitalize()}: {leave.student.first_name}"
        notif_body = f"Your leave application from {leave.from_date} to {leave.to_date} " f"has been {status}."
        if remarks:
            notif_body += f" Remarks: {remarks}"
        NotificationService.create(
            parent_user_id, "leave_update", notif_title, notif_body, reference_id=leave_id, reference_type="leave"
        )

        # If approved, mark attendance as leave
        if status == "approved":
            from app.services.attendance_service import AttendanceService

            AttendanceService.mark_as_leave(leave.student_id, leave.from_date, leave.to_date)

        return leave.to_dict(), None

    @staticmethod
    def get_all(status_filter=None) -> list:
        query = get_db().query(LeaveApplication)
        if status_filter:
            query = query.filter_by(status=status_filter)
        leaves = query.order_by(LeaveApplication.created_at.desc()).all()
        return [leave.to_dict() for leave in leaves]


class NotificationService:

    @staticmethod
    def get_for_user(user_id: int, unread_only: bool = False) -> list:
        query = get_db().query(Notification).filter_by(user_id=user_id)
        if unread_only:
            query = query.filter_by(is_read=False)
        notifications = query.order_by(Notification.created_at.desc()).limit(50).all()
        return [n.to_dict() for n in notifications]

    @staticmethod
    def mark_read(notification_id: int, user_id: int) -> bool:
        n = get_db().query(Notification).filter_by(id=notification_id, user_id=user_id).first()
        if not n:
            return False
        n.is_read = True
        get_db().commit()
        return True

    @staticmethod
    def create(user_id: int, ntype: str, title: str, body: str, reference_id: int = None, reference_type: str = None):
        n = Notification(
            user_id=user_id,
            type=ntype,
            title=title,
            body=body,
            reference_id=reference_id,
            reference_type=reference_type,
        )
        get_db().add(n)
        get_db().commit()
        return n

    @staticmethod
    def mark_all_read(user_id: int) -> int:
        count = get_db().query(Notification).filter_by(user_id=user_id, is_read=False).update({"is_read": True})
        get_db().commit()
        return count


class MessageService:

    @staticmethod
    def create_thread(parent_id: int, child_id: int, subject: str, first_message: str) -> tuple:
        """Returns (thread_dict, None) or (None, error_dict)."""
        # 1. Verify parent-child link
        link = get_db().query(student_parent).filter_by(parent_id=parent_id, student_id=child_id).first()
        if not link:
            return None, {"message": "You are not linked to this student", "status": 403}

        # 2. Find student's current section
        ss = get_db().query(StudentSection).filter_by(student_id=child_id, is_current=True).first()
        if not ss:
            return None, {"message": "Student has no current section enrolled", "status": 400}

        # 3. Get class teacher
        section = get_db().query(Section).filter_by(id=ss.section_id).first()
        if not section or not section.class_teacher_id:
            return None, {"message": "No class teacher assigned to this section", "status": 400}

        teacher = get_db().query(Teacher).filter_by(id=section.class_teacher_id).first()
        if not teacher:
            return None, {"message": "No class teacher assigned", "status": 400}

        # 4. Get parent's user_id
        parent = get_db().query(Parent).filter_by(id=parent_id).first()

        # 5. Create thread
        thread = MessageThread(
            parent_id=parent_id,
            teacher_user_id=teacher.user_id,
            student_id=child_id,
            subject=subject,
        )
        get_db().add(thread)
        get_db().flush()

        # 6. Create first message
        msg = ParentMessage(
            thread_id=thread.id,
            sender_id=parent.user_id,
            body=first_message,
        )
        get_db().add(msg)
        get_db().commit()

        # 7. Notify teacher
        NotificationService.create(
            teacher.user_id,
            "message",
            f"New message from {parent.first_name} {parent.last_name}",
            first_message[:100],
            reference_id=None,
            reference_type="message_thread",
        )

        result = thread.to_dict()
        result["messages"] = [msg.to_dict()]
        return result, None

    @staticmethod
    def list_threads(user_id: int, role: str) -> list:
        """List threads for a parent (by parent.id) or teacher (by teacher_user_id)."""
        if role == "parent":
            parent = get_db().query(Parent).filter_by(user_id=user_id).first()
            if not parent:
                return []
            threads = (
                get_db()
                .query(MessageThread)
                .filter_by(parent_id=parent.id)
                .order_by(MessageThread.last_message_at.desc())
                .all()
            )
        else:
            threads = (
                get_db()
                .query(MessageThread)
                .filter_by(teacher_user_id=user_id)
                .order_by(MessageThread.last_message_at.desc())
                .all()
            )

        result = []
        for t in threads:
            d = t.to_dict()
            unread = t.messages.filter_by(is_read=False).filter(ParentMessage.sender_id != user_id).count()
            d["unread_count"] = unread
            result.append(d)
        return result

    @staticmethod
    def get_thread(thread_id: str, user_id: int, role: str) -> dict | None:
        """Returns thread dict with messages or None if not found/unauthorized."""
        thread = get_db().query(MessageThread).filter_by(id=thread_id).first()
        if not thread:
            return None

        # Verify participant
        if role == "parent":
            parent = get_db().query(Parent).filter_by(user_id=user_id).first()
            if not parent or thread.parent_id != parent.id:
                return None
        else:
            if thread.teacher_user_id != user_id:
                return None

        d = thread.to_dict()
        d["messages"] = [m.to_dict() for m in thread.messages.all()]
        return d

    @staticmethod
    def reply(thread_id: str, sender_user_id: int, body: str, role: str) -> tuple:
        """Returns (message_dict, None) or (None, error_dict)."""
        thread = get_db().query(MessageThread).filter_by(id=thread_id).first()
        if not thread:
            return None, {"message": "Thread not found", "status": 404}

        # Verify sender is a participant
        if role == "parent":
            parent = get_db().query(Parent).filter_by(user_id=sender_user_id).first()
            if not parent or thread.parent_id != parent.id:
                return None, {"message": "Access denied", "status": 403}
            notify_user_id = thread.teacher_user_id
        else:
            if thread.teacher_user_id != sender_user_id:
                return None, {"message": "Access denied", "status": 403}
            parent = get_db().query(Parent).filter_by(id=thread.parent_id).first()
            notify_user_id = parent.user_id if parent else None

        msg = ParentMessage(
            thread_id=thread_id,
            sender_id=sender_user_id,
            body=body,
        )
        get_db().add(msg)

        thread.last_message_at = datetime.utcnow()
        get_db().commit()

        if notify_user_id:
            NotificationService.create(
                notify_user_id,
                "message",
                f"New reply in: {thread.subject}",
                body[:100],
                reference_type="message_thread",
            )

        return msg.to_dict(), None

    @staticmethod
    def mark_thread_read(thread_id: str, user_id: int):
        """Mark all messages in thread as read where sender is not user_id."""
        get_db().query(ParentMessage).filter(
            ParentMessage.thread_id == thread_id,
            ParentMessage.is_read.is_(False),
            ParentMessage.sender_id != user_id,
        ).update({"is_read": True})
        get_db().commit()


class ParentProfileService:

    @staticmethod
    def get_me(user_id: int) -> dict | None:
        parent = get_db().query(Parent).filter_by(user_id=user_id, is_active=True).first()
        return parent.to_dict() if parent else None

    @staticmethod
    def update_me(user_id: int, data: dict) -> tuple:
        parent = get_db().query(Parent).filter_by(user_id=user_id, is_active=True).first()
        if not parent:
            return None, {"message": "Parent profile not found", "status": 404}
        allowed = ["first_name", "last_name", "phone_primary", "phone_secondary", "occupation", "address"]
        for field in allowed:
            if field in data:
                setattr(parent, field, data[field])
        parent.updated_at = datetime.utcnow()
        get_db().commit()
        return parent.to_dict(), None
