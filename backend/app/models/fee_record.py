from app import db
from datetime import datetime
from sqlalchemy import CheckConstraint, UniqueConstraint


class FeeRecord(db.Model):
    __tablename__ = 'fee_records'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    fee_structure_id = db.Column(db.Integer, db.ForeignKey('fee_structures.id'), nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    discount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    net_amount = db.Column(db.Numeric(10, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint('student_id', 'fee_structure_id', name='uq_fee_records_student_fee_structure'),
        CheckConstraint(
            "status IN ('pending','paid','partial','waived')",
            name='ck_fee_records_status'
        ),
    )

    # Relationships
    student = db.relationship('Student', backref=db.backref('fee_records', lazy='dynamic'))
    fee_structure = db.relationship('FeeStructure', backref=db.backref('fee_records', lazy='dynamic'))
    discounts = db.relationship('Discount', backref='fee_record', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'fee_structure_id': self.fee_structure_id,
            'amount': float(self.amount) if self.amount is not None else None,
            'discount': float(self.discount) if self.discount is not None else None,
            'net_amount': float(self.net_amount) if self.net_amount is not None else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<FeeRecord id={self.id} student_id={self.student_id} status={self.status!r}>'
