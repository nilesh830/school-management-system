from app import db
from datetime import datetime
from sqlalchemy import CheckConstraint


class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    # null target_roles  => all roles (school-wide)
    # null target_class_ids => all classes
    target_roles = db.Column(db.JSON, nullable=True)
    target_class_ids = db.Column(db.JSON, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="draft", index=True)
    published_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (CheckConstraint("status IN ('draft','published','archived')", name="ck_announcements_status"),)

    creator = db.relationship("User", backref=db.backref("announcements", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "target_roles": self.target_roles,
            "target_class_ids": self.target_class_ids,
            "status": self.status,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Announcement id={self.id} title={self.title!r} status={self.status}>"
