from datetime import datetime
from app import db


class School(db.Model):
    __bind_key__ = 'master'
    __tablename__ = 'schools'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False, index=True)
    db_url = db.Column(db.String(500), nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(255))
    logo_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    academic_year_start_month = db.Column(db.Integer, default=6)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'address': self.address,
            'phone': self.phone,
            'email': self.email,
            'logo_url': self.logo_url,
            'is_active': self.is_active,
            'academic_year_start_month': self.academic_year_start_month,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<School {self.slug}: {self.name}>'
