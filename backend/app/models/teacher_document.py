from app import db
from datetime import datetime


class TeacherDocument(db.Model):
    __tablename__ = 'teacher_documents'

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(
        db.Integer, db.ForeignKey('teachers.id'), nullable=False, index=True
    )
    document_type = db.Column(db.String(50), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    uploaded_by = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=False
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    uploader = db.relationship('User', backref=db.backref('uploaded_teacher_documents', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'document_type': self.document_type,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'uploaded_by': self.uploaded_by,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<TeacherDocument teacher_id={self.teacher_id} type={self.document_type}>'
