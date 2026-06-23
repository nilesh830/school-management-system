from app import db
from datetime import datetime
from sqlalchemy import UniqueConstraint


class TeacherSubject(db.Model):
    __tablename__ = "teacher_subjects"

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False, index=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    subject = db.relationship("Subject", backref=db.backref("teacher_subjects", lazy="dynamic"))
    class_ = db.relationship("Class", backref=db.backref("teacher_subjects", lazy="dynamic"))
    academic_year = db.relationship("AcademicYear", backref=db.backref("teacher_subjects", lazy="dynamic"))

    __table_args__ = (
        UniqueConstraint(
            "teacher_id", "subject_id", "class_id", "academic_year_id", name="uq_teacher_subject_class_year"
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "teacher_id": self.teacher_id,
            "subject_id": self.subject_id,
            "subject_name": self.subject.name if self.subject else None,
            "subject_code": self.subject.code if self.subject else None,
            "class_id": self.class_id,
            "class_name": self.class_.name if self.class_ else None,
            "academic_year_id": self.academic_year_id,
            "academic_year_name": self.academic_year.name if self.academic_year else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return (
            f"<TeacherSubject teacher_id={self.teacher_id} " f"subject_id={self.subject_id} class_id={self.class_id}>"
        )
