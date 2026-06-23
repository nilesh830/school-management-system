from app import db
from datetime import datetime


class Attendance(db.Model):
    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(
        db.Enum("present", "absent", "late", "leave", "holiday", name="attendance_status"), nullable=False
    )
    marked_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("student_id", "section_id", "date", name="uq_attendance_student_section_date"),
        # SMS-064 — attendance reports query by section over a date range; the
        # unique constraint leads with student_id and can't serve that pattern.
        db.Index("ix_attendance_section_date", "section_id", "date"),
    )

    # Relationships
    student = db.relationship("Student", backref=db.backref("attendances", lazy="dynamic"))
    section = db.relationship("Section", backref=db.backref("attendances", lazy="dynamic"))
    marker = db.relationship("User", foreign_keys=[marked_by], backref=db.backref("marked_attendances", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "section_id": self.section_id,
            "date": str(self.date),
            "status": self.status,
            "marked_by": self.marked_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return (
            f"<Attendance student_id={self.student_id} "
            f"section_id={self.section_id} date={self.date} status={self.status}>"
        )
