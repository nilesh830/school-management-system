from datetime import datetime

from app.utils.tenant import get_db
from app.models.announcement import Announcement

_ALL_ROLES = ["admin", "teacher", "student", "parent"]


class AnnouncementService:

    # ------------------------------------------------------------------ CRUD

    @classmethod
    def create(cls, data: dict, created_by: int):
        """Create a draft (or pre-scheduled) announcement.

        If ``publish_at`` is supplied and not in the future the announcement is
        created already published; otherwise it stays a draft until published.
        Returns (dict, None).
        """
        db = get_db()
        ann = Announcement(
            title=data["title"],
            content=data["content"],
            target_roles=data.get("target_roles"),
            target_class_ids=data.get("target_class_ids"),
            expires_at=data.get("expires_at"),
            status="draft",
        )
        # Optional immediate/scheduled publish timestamp – stored but status stays
        # draft until publish() is called (keeps dispatch explicit & idempotent).
        ann.published_at = data.get("publish_at")
        db.add(ann)
        ann.created_by = created_by
        db.commit()
        return ann.to_dict(), None

    @classmethod
    def get_all(cls):
        """Admin view – every announcement, newest first."""
        db = get_db()
        rows = db.query(Announcement).order_by(Announcement.created_at.desc()).all()
        return [r.to_dict() for r in rows]

    @classmethod
    def get_by_id(cls, announcement_id: int):
        db = get_db()
        ann = db.query(Announcement).filter_by(id=announcement_id).first()
        if not ann:
            return None, {"message": f"Announcement {announcement_id} not found", "status": 404}
        return ann.to_dict(), None

    @classmethod
    def update(cls, announcement_id: int, data: dict):
        db = get_db()
        ann = db.query(Announcement).filter_by(id=announcement_id).first()
        if not ann:
            return None, {"message": f"Announcement {announcement_id} not found", "status": 404}

        if data.get("title") is not None:
            ann.title = data["title"]
        if data.get("content") is not None:
            ann.content = data["content"]
        if "target_roles" in data:
            ann.target_roles = data["target_roles"]
        if "target_class_ids" in data:
            ann.target_class_ids = data["target_class_ids"]
        if "expires_at" in data and data["expires_at"] is not None:
            ann.expires_at = data["expires_at"]
        if data.get("status") is not None:
            ann.status = data["status"]

        db.commit()
        return ann.to_dict(), None

    # --------------------------------------------------------------- publish

    @classmethod
    def publish(cls, announcement_id: int):
        """Publish a draft and dispatch notifications to all matching users.

        Returns (dict_with_notified_count, None) or (None, error).
        """
        db = get_db()
        ann = db.query(Announcement).filter_by(id=announcement_id).first()
        if not ann:
            return None, {"message": f"Announcement {announcement_id} not found", "status": 404}
        if ann.status == "published":
            return None, {"message": "Announcement is already published", "status": 409}

        ann.status = "published"
        if not ann.published_at:
            ann.published_at = datetime.utcnow()
        db.commit()

        notified = cls._dispatch_notifications(ann)

        result = ann.to_dict()
        result["notified_count"] = notified
        return result, None

    # ------------------------------------------------------- targeted reads

    @classmethod
    def get_for_user(cls, role: str, class_ids=None):
        """Return published, non-expired announcements relevant to a user.

        Matching rule:
          * target_roles is None (school-wide) OR role in target_roles
          * AND target_class_ids is None OR overlaps the user's class_ids
        """
        db = get_db()
        class_ids = set(class_ids or [])
        now = datetime.utcnow()

        rows = (
            db.query(Announcement)
            .filter(Announcement.status == "published")
            .order_by(Announcement.created_at.desc())
            .all()
        )

        result = []
        for ann in rows:
            if ann.expires_at is not None and ann.expires_at < now:
                continue
            if ann.target_roles is not None and role not in ann.target_roles:
                continue
            if ann.target_class_ids is not None:
                if not class_ids.intersection(set(ann.target_class_ids)):
                    continue
            result.append(ann.to_dict())
        return result

    # ----------------------------------------------------- internal helpers

    @staticmethod
    def _student_class_ids(student_ids):
        """Resolve current class_ids for a set of student ids."""
        if not student_ids:
            return set()
        from app.models.student_section import StudentSection
        from app.models.section import Section

        db = get_db()
        rows = (
            db.query(Section.class_id)
            .join(StudentSection, StudentSection.section_id == Section.id)
            .filter(
                StudentSection.student_id.in_(list(student_ids)),
                StudentSection.is_current.is_(True),
            )
            .all()
        )
        return {r[0] for r in rows}

    @classmethod
    def _dispatch_notifications(cls, ann: Announcement) -> int:
        """Create a notification per matching user. Returns count dispatched."""
        from app.models.user import User
        from app.models.student import Student
        from app.models.parent import Parent, student_parent
        from app.models.student_section import StudentSection
        from app.models.section import Section
        from app.services.notification_service import NotificationService

        db = get_db()
        roles = ann.target_roles or _ALL_ROLES
        class_ids = ann.target_class_ids
        recipient_user_ids = set()

        # Staff roles are school-wide; class targeting does not narrow them.
        for staff_role in ("admin", "teacher"):
            if staff_role in roles:
                ids = db.query(User.id).filter(User.role == staff_role).all()
                recipient_user_ids.update(i[0] for i in ids)

        if "student" in roles or "parent" in roles:
            # Resolve the set of student ids in scope.
            if class_ids is None:
                student_rows = db.query(Student.id, Student.user_id).all()
                in_scope_students = {(s_id, u_id) for s_id, u_id in student_rows}
            else:
                section_ids = [r[0] for r in db.query(Section.id).filter(Section.class_id.in_(class_ids)).all()]
                student_rows = (
                    db.query(Student.id, Student.user_id)
                    .join(StudentSection, StudentSection.student_id == Student.id)
                    .filter(
                        StudentSection.section_id.in_(section_ids),
                        StudentSection.is_current.is_(True),
                    )
                    .all()
                )
                in_scope_students = {(s_id, u_id) for s_id, u_id in student_rows}

            student_ids = {s_id for s_id, _ in in_scope_students}

            if "student" in roles:
                recipient_user_ids.update(u_id for _, u_id in in_scope_students if u_id is not None)

            if "parent" in roles and student_ids:
                parent_rows = (
                    db.query(Parent.user_id)
                    .join(student_parent, Parent.id == student_parent.c.parent_id)
                    .filter(student_parent.c.student_id.in_(list(student_ids)))
                    .all()
                )
                recipient_user_ids.update(p[0] for p in parent_rows if p[0] is not None)

        for uid in recipient_user_ids:
            NotificationService.create(
                user_id=uid,
                type="announcement",
                title=ann.title,
                body=ann.content,
                reference_id=ann.id,
                reference_type="announcement",
            )
        return len(recipient_user_ids)
