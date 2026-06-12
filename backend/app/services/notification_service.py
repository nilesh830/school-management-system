from app.utils.tenant import get_db
from app.models.notification import Notification


class NotificationService:

    @staticmethod
    def create(user_id: int, type: str, title: str, body: str,
               reference_id: int = None, reference_type: str = None):
        """Persist a single notification row. Returns the saved Notification."""
        notif = Notification(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            reference_id=reference_id,
            reference_type=reference_type,
        )
        get_db().add(notif)
        get_db().commit()
        return notif

    @staticmethod
    def notify_absence(student_id: int, absent_date):
        """
        Create an 'absence' notification for every parent linked to student_id.
        Silently no-ops if the student has no linked parents.
        """
        from app.models.parent import Parent, student_parent
        from sqlalchemy import select

        rows = get_db().execute(
            select(Parent).join(
                student_parent, Parent.id == student_parent.c.parent_id
            ).where(student_parent.c.student_id == student_id)
        ).scalars().all()

        date_str = str(absent_date)
        for parent in rows:
            NotificationService.create(
                user_id=parent.user_id,
                type='absence',
                title='Attendance Alert',
                body=f'Your child (student ID {student_id}) was marked absent on {date_str}.',
                reference_id=student_id,
                reference_type='student',
            )

    @staticmethod
    def get_for_user(user_id: int, unread_only: bool = False, limit: int = 50):
        """Return notifications for a user, newest first."""
        query = (
            get_db()
            .query(Notification)
            .filter(Notification.user_id == user_id)
        )
        if unread_only:
            query = query.filter(Notification.is_read.is_(False))
        rows = query.order_by(Notification.created_at.desc()).limit(limit).all()
        return [r.to_dict() for r in rows]

    @staticmethod
    def mark_read(notification_id: int, user_id: int):
        """Mark a single notification as read. Returns (True, None) or (False, error)."""
        notif = (
            get_db()
            .query(Notification)
            .filter_by(id=notification_id, user_id=user_id)
            .first()
        )
        if not notif:
            return False, {'message': 'Notification not found', 'status': 404}
        notif.is_read = True
        get_db().commit()
        return True, None

    @staticmethod
    def mark_all_read(user_id: int):
        """Mark all notifications for a user as read."""
        get_db().query(Notification).filter_by(
            user_id=user_id, is_read=False
        ).update({'is_read': True})
        get_db().commit()
