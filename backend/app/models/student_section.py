from app import db
from datetime import datetime


class StudentSection(db.Model):
    """Tracks which section a student is enrolled in for a given academic year.

    A student may only have one current enrollment (is_current=True) at a time.
    Historical rows are kept for audit purposes (is_current=False, end_date set).
    """

    __tablename__ = "student_sections"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=False, index=True)
    academic_year = db.Column(db.String(9), nullable=False)  # e.g. "2024-2025"
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    is_current = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    section = db.relationship("Section", backref=db.backref("student_sections", lazy="dynamic"))

    def to_dict(self):
        data = {
            "id": self.id,
            "student_id": self.student_id,
            "section_id": self.section_id,
            "academic_year": self.academic_year,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_current": self.is_current,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        # Readable section / class details for display
        if self.section:
            data["section_name"] = self.section.name
            data["class_name"] = self.section.class_.name if self.section.class_ else None
            data["grade_level"] = self.section.class_.grade_level if self.section.class_ else None
            data["label"] = (
                f"{data['class_name']} — {self.section.name}"
                if data["class_name"]
                else self.section.name
            )
        else:
            data["section_name"] = None
            data["class_name"] = None
            data["grade_level"] = None
            data["label"] = None
        return data

    def __repr__(self):
        return (
            f"<StudentSection student_id={self.student_id} " f"section_id={self.section_id} year={self.academic_year}>"
        )
