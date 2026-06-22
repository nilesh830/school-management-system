from app import db
from datetime import datetime
from sqlalchemy import UniqueConstraint


class StudentTransport(db.Model):
    __tablename__ = 'student_transport'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False, index=True)
    route_id = db.Column(db.Integer, db.ForeignKey('transport_routes.id'), nullable=False, index=True)
    pickup_stop = db.Column(db.String(100), nullable=True)
    drop_stop = db.Column(db.String(100), nullable=True)
    academic_year_id = db.Column(
        db.Integer, db.ForeignKey('academic_years.id'), nullable=False, index=True
    )
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint('student_id', 'academic_year_id', name='uq_student_transport_student_year'),
    )

    # Relationships
    student = db.relationship('Student', backref=db.backref('transport_assignments', lazy='dynamic'))
    route = db.relationship('TransportRoute', backref=db.backref('assignments', lazy='dynamic'))
    academic_year = db.relationship('AcademicYear', backref=db.backref('transport_assignments', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'student_name': f'{self.student.first_name} {self.student.last_name}' if self.student else None,
            'admission_no': self.student.admission_no if self.student else None,
            'route_id': self.route_id,
            'route_name': self.route.name if self.route else None,
            'pickup_stop': self.pickup_stop,
            'drop_stop': self.drop_stop,
            'academic_year_id': self.academic_year_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<StudentTransport id={self.id} student_id={self.student_id} route_id={self.route_id}>'
