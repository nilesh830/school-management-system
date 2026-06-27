from app import db
from datetime import datetime
from sqlalchemy import CheckConstraint


class FeeStructure(db.Model):
    __tablename__ = "fee_structures"

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False, index=True)
    academic_year_id = db.Column(db.Integer, db.ForeignKey("academic_years.id"), nullable=False, index=True)
    fee_type = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    is_recurring = db.Column(db.Boolean, nullable=False, default=False)
    frequency = db.Column(db.String(20), nullable=False, default="one_time")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("frequency IN ('monthly','quarterly','annual','one_time')", name="ck_fee_structures_frequency"),
    )

    # Relationships
    class_ = db.relationship("Class", backref=db.backref("fee_structures", lazy="dynamic"))
    academic_year = db.relationship("AcademicYear", backref=db.backref("fee_structures", lazy="dynamic"))

    def to_dict(self):
        return {
            "id": self.id,
            "class_id": self.class_id,
            "academic_year_id": self.academic_year_id,
            "fee_type": self.fee_type,
            "amount": float(self.amount) if self.amount is not None else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "is_recurring": self.is_recurring,
            "frequency": self.frequency,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<FeeStructure id={self.id} class_id={self.class_id} fee_type={self.fee_type!r}>"
