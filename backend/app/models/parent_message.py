import uuid
from app import db
from datetime import datetime


class MessageThread(db.Model):
    __tablename__ = 'message_threads'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_id = db.Column(db.Integer, db.ForeignKey('parents.id'), nullable=False, index=True)
    # Points at users.id for Sprint 1-6; migrated to teachers.id in Sprint 3 when Teacher model is built
    teacher_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    teacher_user = db.relationship('User', foreign_keys=[teacher_user_id])
    messages = db.relationship('ParentMessage', backref='thread', lazy='dynamic',
                               order_by='ParentMessage.created_at')

    def to_dict(self):
        return {
            'id': self.id,
            'parent_id': self.parent_id,
            'teacher_user_id': self.teacher_user_id,
            'student_id': self.student_id,
            'subject': self.subject,
            'last_message_at': self.last_message_at.isoformat(),
            'message_count': self.messages.count(),
        }


class ParentMessage(db.Model):
    __tablename__ = 'parent_messages'

    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.String(36), db.ForeignKey('message_threads.id'), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    sender = db.relationship('User', foreign_keys=[sender_id])

    def to_dict(self):
        sender_name = 'Unknown'
        if self.sender:
            sender_name = f'{self.sender.first_name} {self.sender.last_name}'
        return {
            'id': self.id,
            'thread_id': self.thread_id,
            'sender_id': self.sender_id,
            'sender_name': sender_name,
            'body': self.body,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat(),
        }
