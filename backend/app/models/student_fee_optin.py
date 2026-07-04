from app import db
from datetime import datetime
from sqlalchemy import UniqueConstraint


class StudentFeeOptin(db.Model):
    __tablename__ = "student_fee_optins"

    id = db.Column(db.Integer, primary_key=True)
    fee_structure_id = db.Column(
        db.Integer,
        db.ForeignKey("fee_structures.id", name="fk_student_fee_optins_fee_structure"),
        nullable=False,
        index=True,
    )
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id", name="fk_student_fee_optins_student"),
        nullable=False,
        index=True,
    )
    # Optional per-student base amount. When set, fee generation uses this
    # instead of FeeStructure.amount (e.g. Hostel: single room ₹5000 vs
    # double room ₹3500). Distinct from FeeRecord.amount_override which is a
    # post-generation adjustment.
    amount_override = db.Column(db.Numeric(10, 2), nullable=True)
    # Audit trail — who opted this student in and when.
    opted_in_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", name="fk_student_fee_optins_user"),
        nullable=True,
        index=True,
    )
    opted_in_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    # Soft-delete: set is_active=False to remove the student from this fee
    # without losing the audit trail.
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "fee_structure_id",
            "student_id",
            name="uq_student_fee_optins_structure_student",
        ),
    )

    # Relationships
    fee_structure = db.relationship(
        "FeeStructure",
        backref=db.backref("optins", lazy="dynamic"),
    )
    student = db.relationship(
        "Student",
        backref=db.backref("fee_optins", lazy="dynamic"),
    )
    opted_in_by_user = db.relationship(
        "User",
        foreign_keys=[opted_in_by],
        backref=db.backref("fee_optins_approved", lazy="dynamic"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "fee_structure_id": self.fee_structure_id,
            "student_id": self.student_id,
            "student_name": (
                f"{self.student.first_name} {self.student.last_name}"
                if self.student
                else None
            ),
            "admission_no": self.student.admission_no if self.student else None,
            "amount_override": (
                float(self.amount_override) if self.amount_override is not None else None
            ),
            "opted_in_by": self.opted_in_by,
            "opted_in_at": self.opted_in_at.isoformat() if self.opted_in_at else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return (
            f"<StudentFeeOptin id={self.id} "
            f"student_id={self.student_id} "
            f"fee_structure_id={self.fee_structure_id} "
            f"active={self.is_active}>"
        )
