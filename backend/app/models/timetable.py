from app import db
from datetime import datetime
from sqlalchemy import UniqueConstraint


class Timetable(db.Model):
    __tablename__ = 'timetables'

    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(
        db.Integer, db.ForeignKey('sections.id'), nullable=False, index=True
    )
    subject_id = db.Column(
        db.Integer, db.ForeignKey('subjects.id'), nullable=False
    )
    teacher_id = db.Column(
        db.Integer, db.ForeignKey('teachers.id'), nullable=False
    )
    # 0=Monday, 1=Tuesday, ..., 5=Saturday
    day_of_week = db.Column(db.Integer, nullable=False)
    period_no = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    section = db.relationship('Section', backref=db.backref('timetable_entries', lazy='dynamic'))
    subject = db.relationship('Subject', backref=db.backref('timetable_entries', lazy='dynamic'))
    teacher = db.relationship('Teacher', backref=db.backref('timetable_entries', lazy='dynamic'))

    __table_args__ = (
        # One subject per section slot
        UniqueConstraint(
            'section_id', 'day_of_week', 'period_no',
            name='uq_section_day_period'
        ),
        # No teacher double-booking
        UniqueConstraint(
            'teacher_id', 'day_of_week', 'period_no',
            name='uq_teacher_day_period'
        ),
    )

    _DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    def to_dict(self):
        return {
            'id': self.id,
            'section_id': self.section_id,
            'section_name': self.section.name if self.section else None,
            'subject_id': self.subject_id,
            'subject_name': self.subject.name if self.subject else None,
            'subject_code': self.subject.code if self.subject else None,
            'teacher_id': self.teacher_id,
            'teacher_name': (
                f'{self.teacher.first_name} {self.teacher.last_name}'
                if self.teacher else None
            ),
            'day_of_week': self.day_of_week,
            'day_name': self._DAY_NAMES[self.day_of_week] if 0 <= self.day_of_week <= 5 else None,
            'period_no': self.period_no,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return (
            f'<Timetable section_id={self.section_id} '
            f'day={self.day_of_week} period={self.period_no}>'
        )
