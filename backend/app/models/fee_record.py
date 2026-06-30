from app import db
from datetime import datetime
from sqlalchemy import CheckConstraint, UniqueConstraint


class FeeRecord(db.Model):
    __tablename__ = "fee_records"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    fee_structure_id = db.Column(db.Integer, db.ForeignKey("fee_structures.id"), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    discount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    net_amount = db.Column(db.Numeric(10, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    # Billing period this record covers. "ONCE" for one-time fees; "YYYY-MM"
    # for a recurring (monthly/quarterly) installment; "YYYY" for annual.
    period = db.Column(db.String(10), nullable=False, default="ONCE")
    # Admin-set base amount for this single record (concession fare, partial month).
    # When set, generation/repair uses it as the record's `amount` instead of the
    # computed amount; distinct from Discount (which reduces with an audit trail).
    amount_override = db.Column(db.Numeric(10, 2), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "student_id", "fee_structure_id", "period",
            name="uq_fee_records_student_structure_period",
        ),
        CheckConstraint("status IN ('pending','paid','partial','waived')", name="ck_fee_records_status"),
        CheckConstraint("amount_override IS NULL OR amount_override >= 0", name="ck_fee_records_amount_override_nonneg"),
    )

    # Relationships
    student = db.relationship("Student", backref=db.backref("fee_records", lazy="dynamic"))
    fee_structure = db.relationship("FeeStructure", backref=db.backref("fee_records", lazy="dynamic"))
    discounts = db.relationship("Discount", backref="fee_record", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "fee_structure_id": self.fee_structure_id,
            "amount": float(self.amount) if self.amount is not None else None,
            "discount": float(self.discount) if self.discount is not None else None,
            "net_amount": float(self.net_amount) if self.net_amount is not None else None,
            "amount_override": float(self.amount_override) if self.amount_override is not None else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "period": self.period,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<FeeRecord id={self.id} student_id={self.student_id} status={self.status!r}>"
