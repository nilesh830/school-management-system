from datetime import datetime
from app import db


class SchoolEmailConfig(db.Model):
    """Per-school outbound SMTP configuration (master DB, public schema).

    Lives on the ``master`` bind so it is shared across the schema-per-school
    setup. Created automatically by ``db.create_all(bind_key=["master"])`` on
    app startup — the master schema is intentionally NOT under Flask-Migrate, so
    new master tables must be create_all-friendly (this one is).

    When a school has a row here, bulk-registration credential emails are sent
    through its own SMTP server, FROM its own address. When absent, the sender
    falls back to the global MAIL_* config (see app/utils/email.py).

    SECURITY: ``smtp_password`` is stored as-is. It is an app-password / relay
    secret, not a user password — encrypting it at rest (Fernet) is a tracked
    follow-up. Never expose it in to_dict().
    """

    __bind_key__ = "master"
    __tablename__ = "school_email_configs"

    id = db.Column(db.Integer, primary_key=True)
    school_slug = db.Column(db.String(50), unique=True, nullable=False, index=True)
    smtp_host = db.Column(db.String(255), nullable=False)
    smtp_port = db.Column(db.Integer, nullable=False, default=587)
    smtp_use_tls = db.Column(db.Boolean, nullable=False, default=True)
    smtp_username = db.Column(db.String(255), nullable=False)
    smtp_password = db.Column(db.String(500), nullable=False)
    from_email = db.Column(db.String(255), nullable=False)
    from_name = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def to_dict(self):
        """Safe representation — never includes smtp_password."""
        return {
            "id": self.id,
            "school_slug": self.school_slug,
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "smtp_use_tls": self.smtp_use_tls,
            "smtp_username": self.smtp_username,
            "smtp_password_set": bool(self.smtp_password),
            "from_email": self.from_email,
            "from_name": self.from_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<SchoolEmailConfig {self.school_slug} via {self.smtp_host}>"
