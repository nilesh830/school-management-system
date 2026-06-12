from app import db
from datetime import datetime


class Teacher(db.Model):
    __tablename__ = 'teachers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    employee_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(
        db.Enum('Male', 'Female', 'Other', name='teacher_gender_types'), nullable=True
    )
    qualification = db.Column(db.String(200), nullable=True)
    specialization = db.Column(db.String(200), nullable=True)
    joining_date = db.Column(db.Date, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user = db.relationship('User', backref=db.backref('teacher', uselist=False))
    subjects = db.relationship('TeacherSubject', backref='teacher', lazy='dynamic')
    documents = db.relationship('TeacherDocument', backref='teacher', lazy='dynamic')

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def to_dict(self, include_subjects=False):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'employee_id': self.employee_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'gender': self.gender,
            'qualification': self.qualification,
            'specialization': self.specialization,
            'joining_date': self.joining_date.isoformat() if self.joining_date else None,
            'phone': self.phone,
            'address': self.address,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_subjects:
            data['subjects'] = [ts.to_dict() for ts in self.subjects.all()]
        return data

    def __repr__(self):
        return f'<Teacher {self.employee_id}: {self.first_name} {self.last_name}>'
