from app import db
from datetime import datetime
from sqlalchemy import CheckConstraint


class BookIssue(db.Model):
    __tablename__ = "book_issues"

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("library_books.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    issued_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    due_date = db.Column(db.Date, nullable=False)
    returned_date = db.Column(db.Date, nullable=True)
    fine_amount = db.Column(db.Numeric(8, 2), nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default="issued", index=True)
    issued_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (CheckConstraint("status IN ('issued','returned','overdue')", name="ck_book_issues_status"),)

    book = db.relationship("LibraryBook", backref=db.backref("issues", lazy="dynamic"))
    student = db.relationship("Student", backref=db.backref("book_issues", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "book_id": self.book_id,
            "book_title": self.book.title if self.book else None,
            "student_id": self.student_id,
            "student_name": (f"{self.student.first_name} {self.student.last_name}" if self.student else None),
            "issued_date": self.issued_date.isoformat() if self.issued_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "returned_date": self.returned_date.isoformat() if self.returned_date else None,
            "fine_amount": float(self.fine_amount) if self.fine_amount is not None else 0.0,
            "status": self.status,
            "issued_by": self.issued_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<BookIssue id={self.id} book_id={self.book_id} student_id={self.student_id} status={self.status}>"
