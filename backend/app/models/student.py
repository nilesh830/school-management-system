from app import db
from datetime import datetime


class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    admission_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.Enum('Male', 'Female', 'Other', name='gender_types'), nullable=False)
    admission_date = db.Column(db.Date, nullable=False)
    blood_group = db.Column(db.String(5))
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship('User', backref=db.backref('student', uselist=False))

    def to_dict(self):
        return {
            'id': self.id,
            'admission_no': self.admission_no,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': f'{self.first_name} {self.last_name}',
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'gender': self.gender,
            'admission_date': self.admission_date.isoformat() if self.admission_date else None,
            'blood_group': self.blood_group,
            'address': self.address,
            'phone': self.phone,
            'is_active': self.is_active,
        }

    def __repr__(self):
        return f'<Student {self.admission_no}: {self.first_name} {self.last_name}>'
