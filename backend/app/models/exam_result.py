from app import db
from datetime import datetime
from sqlalchemy import CheckConstraint, UniqueConstraint


class ExamResult(db.Model):
    __tablename__ = "exam_results"

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("exams.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False, index=True)
    marks_obtained = db.Column(db.Numeric(5, 2), nullable=True)
    grade = db.Column(db.String(2), nullable=True)
    gpa = db.Column(db.Numeric(3, 2), nullable=True)
    status = db.Column(db.String(10), nullable=False, default="draft")
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", "subject_id", name="uq_exam_results_exam_student_subject"),
        CheckConstraint("status IN ('draft', 'finalized')", name="ck_exam_results_status"),
    )

    # Relationships
    exam = db.relationship("Exam", backref=db.backref("results", lazy="dynamic"))
    student = db.relationship("Student", backref=db.backref("exam_results", lazy="dynamic"))
    subject = db.relationship("Subject", backref=db.backref("exam_results", lazy="dynamic"))
    creator = db.relationship(
        "User", foreign_keys=[created_by], backref=db.backref("created_exam_results", lazy="dynamic")
    )

    def to_dict(self):
        return {
            "id": self.id,
            "exam_id": self.exam_id,
            "student_id": self.student_id,
            "subject_id": self.subject_id,
            "marks_obtained": float(self.marks_obtained) if self.marks_obtained is not None else None,
            "grade": self.grade if self.grade is not None else None,
            "gpa": float(self.gpa) if self.gpa is not None else None,
            "status": self.status,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return (
            f"<ExamResult id={self.id} exam_id={self.exam_id} "
            f"student_id={self.student_id} subject_id={self.subject_id} "
            f"status={self.status!r}>"
        )
