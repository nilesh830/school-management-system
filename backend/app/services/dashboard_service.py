"""
SMS-056 — Admin KPI Dashboard service.

Aggregates cross-module metrics for the admin overview screen. Reuses existing
service logic (attendance today-summary, fee defaulters) rather than duplicating
queries. All aggregates are defensive: empty data yields zeros / empty lists and
never divides by zero.
"""

from collections import defaultdict

from app.utils.tenant import get_db
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.attendance import Attendance
from app.models.announcement import Announcement
from app.models.leave_application import LeaveApplication


# Statuses that count toward an "attendance opportunity" when computing a
# student's overall percentage (leave / holiday are excluded from the denominator).
_COUNTED_STATUSES = ("present", "absent", "late")
_LOW_ATTENDANCE_THRESHOLD = 75.0
_LOW_ATTENDANCE_CAP = 10
_RECENT_ANNOUNCEMENTS_LIMIT = 5


class DashboardService:

    @staticmethod
    def get_admin_kpis() -> dict:
        """Return a dict of aggregated KPIs for the admin dashboard."""
        from app.services.attendance_service import AttendanceService
        from app.services.fee_service import FeeService

        db = get_db()

        # --- Headline counts -------------------------------------------------
        total_students = db.query(Student).filter(Student.is_active.is_(True)).count()
        total_teachers = db.query(Teacher).filter(Teacher.is_active.is_(True)).count()

        # --- Attendance today (reuse AttendanceService) ----------------------
        today = AttendanceService.get_today_summary()
        present = today.get("present", 0)
        absent = today.get("absent", 0)
        late = today.get("late", 0)
        # Percentage of present (+late counts as attended) over marked-countable rows
        denom = present + absent + late
        attended = present + late
        percentage = round((attended / denom) * 100, 2) if denom else 0.0
        attendance_today = {
            "present": present,
            "absent": absent,
            "late": late,
            "percentage": percentage,
        }

        # --- Fee collection this month + defaulters (reuse FeeService) -------
        fee_collection = DashboardService._fee_collection_this_month()
        defaulters = FeeService.get_defaulters()
        fee_defaulters_count = len(defaulters)

        # --- Pending leave applications --------------------------------------
        pending_leave_applications = db.query(LeaveApplication).filter(LeaveApplication.status == "pending").count()

        # --- Recent published announcements ----------------------------------
        recent_announcements = [
            a.to_dict()
            for a in (
                db.query(Announcement)
                .filter(Announcement.status == "published")
                .order_by(Announcement.published_at.desc().nullslast(), Announcement.created_at.desc())
                .limit(_RECENT_ANNOUNCEMENTS_LIMIT)
                .all()
            )
        ]

        # --- Low-attendance students -----------------------------------------
        low_attendance_students = DashboardService._low_attendance_students()

        return {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "attendance_today": attendance_today,
            "fee_collection_this_month": fee_collection,
            "pending_leave_applications": pending_leave_applications,
            "recent_announcements": recent_announcements,
            "low_attendance_students": low_attendance_students,
            "fee_defaulters_count": fee_defaulters_count,
        }

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _fee_collection_this_month() -> dict:
        """
        Sum of payments received in the current calendar month (collected) and
        the outstanding balance on overdue/pending records (pending).
        """
        from datetime import date
        import calendar

        from app.models.fee_payment import FeePayment
        from app.models.fee_record import FeeRecord

        db = get_db()
        today = date.today()
        _, last_day = calendar.monthrange(today.year, today.month)
        month_start = date(today.year, today.month, 1)
        month_end = date(today.year, today.month, last_day)

        payments = (
            db.query(FeePayment)
            .filter(
                FeePayment.payment_date >= month_start,
                FeePayment.payment_date <= month_end,
            )
            .all()
        )
        collected = sum(float(p.amount_paid) for p in payments)

        # Pending = net_amount minus payments for all non-paid / non-waived records
        open_records = db.query(FeeRecord).filter(FeeRecord.status.in_(["pending", "partial"])).all()
        pending = 0.0
        for rec in open_records:
            paid = sum(float(p.amount_paid) for p in db.query(FeePayment).filter_by(fee_record_id=rec.id).all())
            balance = float(rec.net_amount) - paid
            if balance > 0:
                pending += balance

        return {
            "collected": round(collected, 2),
            "pending": round(pending, 2),
        }

    @staticmethod
    def _low_attendance_students() -> list:
        """
        Return students whose overall attendance percentage is below the
        threshold, capped at _LOW_ATTENDANCE_CAP, ascending by percentage.
        """
        db = get_db()

        rows = db.query(Attendance.student_id, Attendance.status).filter(Attendance.status.in_(_COUNTED_STATUSES)).all()

        counts = defaultdict(lambda: {"attended": 0, "total": 0})
        for student_id, status in rows:
            counts[student_id]["total"] += 1
            if status in ("present", "late"):
                counts[student_id]["attended"] += 1

        if not counts:
            return []

        # Resolve names in one query
        student_ids = list(counts.keys())
        students = {
            s.id: f"{s.first_name} {s.last_name}" for s in db.query(Student).filter(Student.id.in_(student_ids)).all()
        }

        low = []
        for student_id, c in counts.items():
            total = c["total"]
            if total == 0:
                continue
            pct = round((c["attended"] / total) * 100, 2)
            if pct < _LOW_ATTENDANCE_THRESHOLD:
                low.append(
                    {
                        "student_id": student_id,
                        "name": students.get(student_id, f"Student {student_id}"),
                        "percentage": pct,
                    }
                )

        low.sort(key=lambda x: x["percentage"])
        return low[:_LOW_ATTENDANCE_CAP]
