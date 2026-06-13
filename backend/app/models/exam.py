from app import db
from datetime import datetime
from sqlalchemy import CheckConstraint


class Exam(db.Model):
    __tablename__ = 'exams'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    term = db.Column(db.String(50), nullable=False)
    exam_type = db.Column(db.String(20), nullable=False)
    section_id = db.Column(
        db.Integer, db.ForeignKey('sections.id'), nullable=False, index=True
    )
    conducted_date = db.Column(db.Date, nullable=True)
    academic_year_id = db.Column(
        db.Integer, db.ForeignKey('academic_years.id'), nullable=False, index=True
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    created_by = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "exam_type IN ('midterm', 'final', 'unit_test', 'practical')",
            name='ck_exam_exam_type'
        ),
    )

    # Relationships
    section = db.relationship(
        'Section', backref=db.backref('exams', lazy='dynamic')
    )
    academic_year = db.relationship(
        'AcademicYear', backref=db.backref('exams', lazy='dynamic')
    )
    creator = db.relationship(
        'User', foreign_keys=[created_by],
        backref=db.backref('created_exams', lazy='dynamic')
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'term': self.term,
            'exam_type': self.exam_type,
            'section_id': self.section_id,
            'conducted_date': (
                self.conducted_date.isoformat() if self.conducted_date else None
            ),
            'academic_year_id': self.academic_year_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
        }

    def __repr__(self):
        return (
            f'<Exam id={self.id} name={self.name!r} '
            f'type={self.exam_type} section_id={self.section_id}>'
        )
