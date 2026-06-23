from datetime import datetime
from app import db


class SuperAdminRevokedToken(db.Model):
    __bind_key__ = "master"
    __tablename__ = "super_admin_revoked_tokens"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @classmethod
    def is_jti_blocklisted(cls, jti):
        return db.session.query(cls).filter_by(jti=jti).first() is not None

    def __repr__(self):
        return f"<SuperAdminRevokedToken {self.jti}>"
