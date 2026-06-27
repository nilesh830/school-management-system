from app import db
from datetime import datetime


class Class(db.Model):
    __tablename__ = "classes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # e.g. "Grade 10"
    grade_level = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    academic_year = db.relationship("AcademicYear", backref=db.backref("classes", lazy="dynamic"))
    sections = db.relationship("Section", backref="class_", lazy="dynamic")

    def to_dict(self, include_sections=False):
        data = {
            "id": self.id,
            "name": self.name,
            "grade_level": self.grade_level,
            "description": self.description,
            "academic_year_id": self.academic_year_id,
            "academic_year_name": self.academic_year.name if self.academic_year else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_sections:
            data["sections"] = [s.to_dict() for s in self.sections.filter_by(is_active=True)]
        return data

    def __repr__(self):
        return f"<Class {self.name} (grade {self.grade_level})>"
