from app import db
from datetime import datetime


class StudentDocument(db.Model):
    """Stores uploaded document metadata for a student.

    The actual file is stored on disk (or object storage in production).
    file_path holds the relative path from the UPLOAD_FOLDER root.
    Soft-delete via is_active — never hard-delete document records.
    """

    __tablename__ = 'student_documents'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey('students.id'), nullable=False, index=True
    )
    document_type = db.Column(db.String(50), nullable=False)   # e.g. "birth_certificate"
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    uploaded_by = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=False, index=True
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    uploader = db.relationship('User', foreign_keys=[uploaded_by])

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'document_type': self.document_type,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'uploaded_by': self.uploaded_by,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

    def __repr__(self):
        return (
            f'<StudentDocument student_id={self.student_id} '
            f'type={self.document_type} file={self.file_name}>'
        )
