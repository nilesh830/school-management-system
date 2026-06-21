from app import db
from datetime import datetime
from sqlalchemy import CheckConstraint


class FeePayment(db.Model):
    __tablename__ = 'fee_payments'

    id = db.Column(db.Integer, primary_key=True)
    fee_record_id = db.Column(
        db.Integer, db.ForeignKey('fee_records.id'), nullable=False, index=True
    )
    amount_paid = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    receipt_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    transaction_reference = db.Column(db.String(100), nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    collected_by = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=True, index=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "payment_method IN ('cash', 'bank_transfer', 'cheque', 'online')",
            name='ck_fee_payments_payment_method'
        ),
    )

    # Relationships
    fee_record = db.relationship(
        'FeeRecord', backref=db.backref('payments', lazy='dynamic')
    )
    collected_by_user = db.relationship(
        'User',
        foreign_keys=[collected_by],
        backref=db.backref('collected_payments', lazy='dynamic')
    )

    def to_dict(self):
        return {
            'id': self.id,
            'fee_record_id': self.fee_record_id,
            'amount_paid': float(self.amount_paid) if self.amount_paid is not None else None,
            'payment_method': self.payment_method,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'receipt_no': self.receipt_no,
            'transaction_reference': self.transaction_reference,
            'remarks': self.remarks,
            'collected_by': self.collected_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<FeePayment id={self.id} receipt_no={self.receipt_no!r} amount_paid={self.amount_paid}>'
