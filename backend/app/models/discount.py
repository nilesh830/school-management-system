from app import db
from datetime import datetime
from sqlalchemy import CheckConstraint


class Discount(db.Model):
    __tablename__ = "discounts"

    id = db.Column(db.Integer, primary_key=True)
    fee_record_id = db.Column(db.Integer, db.ForeignKey("fee_records.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    discount_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    reason = db.Column(db.String(500), nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "discount_type IN ('scholarship', 'sibling', 'staff', 'custom')", name="ck_discounts_discount_type"
        ),
        CheckConstraint("amount > 0", name="ck_discounts_amount_positive"),
    )

    # Relationships
    student = db.relationship("Student", backref=db.backref("discounts", lazy="dynamic"))
    approved_by_user = db.relationship(
        "User", foreign_keys=[approved_by], backref=db.backref("approved_discounts", lazy="dynamic")
    )

    def to_dict(self):
        return {
            "id": self.id,
            "fee_record_id": self.fee_record_id,
            "student_id": self.student_id,
            "discount_type": self.discount_type,
            "amount": float(self.amount) if self.amount is not None else None,
            "reason": self.reason,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return (
            f"<Discount id={self.id} student_id={self.student_id} " f"type={self.discount_type!r} amount={self.amount}>"
        )
