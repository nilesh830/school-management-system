from app import db
from datetime import datetime


class LeaveApplication(db.Model):
    __tablename__ = 'leave_applications'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('parents.id'), nullable=False, index=True)
    from_date = db.Column(db.Date, nullable=False)
    to_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    leave_type = db.Column(
        db.Enum('sick', 'family', 'personal', 'other', name='leave_types'), default='personal'
    )
    status = db.Column(
        db.Enum('pending', 'approved', 'rejected', name='leave_status'), default='pending', index=True
    )
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(db.DateTime)
    reviewer_remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    student = db.relationship('Student', backref=db.backref('leave_applications', lazy='dynamic'))
    parent = db.relationship('Parent', backref=db.backref('leave_applications', lazy='dynamic'))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])

    @property
    def duration_days(self):
        return (self.to_date - self.from_date).days + 1

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'parent_id': self.parent_id,
            'from_date': self.from_date.isoformat(),
            'to_date': self.to_date.isoformat(),
            'duration_days': self.duration_days,
            'reason': self.reason,
            'leave_type': self.leave_type,
            'status': self.status,
            'reviewer_remarks': self.reviewer_remarks,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'created_at': self.created_at.isoformat(),
        }
