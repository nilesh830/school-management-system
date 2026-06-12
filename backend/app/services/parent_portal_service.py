from flask import abort

from app.utils.tenant import get_db
from app.models.parent import Parent, student_parent
from app.models.student import Student
from app.models.leave_application import LeaveApplication
from app.models.notification import Notification
from datetime import datetime, date


class ParentPortalService:

    @staticmethod
    def _verify_child_access(parent_id: int, child_id: int) -> Student:
        """Aborts 403 if this parent does not own the given child. Always call before any child data access."""
        link = get_db().query(student_parent).filter_by(
            parent_id=parent_id, student_id=child_id
        ).first()
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
    def get_dashboard(parent_id: int) -> dict:
        parent = get_db().query(Parent).filter_by(id=parent_id, is_active=True).first()
        if not parent:
            abort(404)
        children_data = []
        for child in parent.students.filter_by(is_active=True).all():
            children_data.append({
                'student': child.to_dict(),
                'attendance_summary': ParentPortalService._get_attendance_summary(child.id),
                'pending_fees': ParentPortalService._get_pending_fees(child.id),
                'recent_grades': ParentPortalService._get_recent_grades(child.id),
            })
        unread_notifications = get_db().query(Notification).filter_by(
            user_id=parent.user_id, is_read=False
        ).count()
        return {
            'parent': parent.to_dict(),
            'children': children_data,
            'unread_notifications': unread_notifications,
        }

    @staticmethod
    def _get_attendance_summary(student_id: int) -> dict:
        today = date.today()
        return {
            'month': today.month,
            'year': today.year,
            'present': 0,
            'absent': 0,
            'percentage': 0.0,
        }

    @staticmethod
    def _get_pending_fees(student_id: int) -> dict:
        return {'total_due': 0.0, 'overdue_count': 0}

    @staticmethod
    def _get_recent_grades(student_id: int) -> list:
        return []

    @staticmethod
    def get_child_attendance(parent_id: int, child_id: int, month: int = None, year: int = None) -> dict:
        ParentPortalService._verify_child_access(parent_id, child_id)
        today = date.today()
        month = month or today.month
        year = year or today.year
        return {
            'student_id': child_id,
            'month': month,
            'year': year,
            'records': [],
            'summary': {'present': 0, 'absent': 0, 'late': 0, 'percentage': 0.0},
        }

    @staticmethod
    def get_child_grades(parent_id: int, child_id: int) -> dict:
        ParentPortalService._verify_child_access(parent_id, child_id)
        return {'student_id': child_id, 'exams': [], 'gpa': 0.0}

    @staticmethod
    def get_child_fees(parent_id: int, child_id: int) -> dict:
        ParentPortalService._verify_child_access(parent_id, child_id)
        return {'student_id': child_id, 'records': [], 'total_due': 0.0, 'total_paid': 0.0}


class LeaveService:

    @staticmethod
    def submit(parent_id: int, data: dict) -> tuple:
        child_id = data.get('student_id')
        link = get_db().query(student_parent).filter_by(
            parent_id=parent_id, student_id=child_id
        ).first()
        if not link:
            return None, {'message': 'You are not linked to this student', 'status': 403}

        leave = LeaveApplication(
            student_id=child_id,
            parent_id=parent_id,
            from_date=datetime.strptime(data['from_date'], '%Y-%m-%d').date(),
            to_date=datetime.strptime(data['to_date'], '%Y-%m-%d').date(),
            reason=data['reason'],
            leave_type=data.get('leave_type', 'personal'),
        )
        get_db().add(leave)
        get_db().commit()
        return leave.to_dict(), None

    @staticmethod
    def get_by_parent(parent_id: int) -> list:
        leaves = get_db().query(LeaveApplication).filter_by(parent_id=parent_id)\
            .order_by(LeaveApplication.created_at.desc()).all()
        return [l.to_dict() for l in leaves]

    @staticmethod
    def review(leave_id: int, reviewer_user_id: int, status: str, remarks: str = None) -> tuple:
        leave = get_db().get(LeaveApplication, leave_id)
        if not leave:
            abort(404)
        if status not in ('approved', 'rejected'):
            return None, {'message': 'Invalid status', 'status': 400}
        leave.status = status
        leave.reviewed_by = reviewer_user_id
        leave.reviewed_at = datetime.utcnow()
        leave.reviewer_remarks = remarks
        get_db().commit()
        return leave.to_dict(), None


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
    def create(user_id: int, ntype: str, title: str, body: str,
               reference_id: int = None, reference_type: str = None):
        n = Notification(
            user_id=user_id, type=ntype, title=title, body=body,
            reference_id=reference_id, reference_type=reference_type
        )
        get_db().add(n)
        get_db().commit()
        return n
