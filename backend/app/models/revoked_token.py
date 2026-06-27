from app import db
from datetime import datetime


class RevokedToken(db.Model):
    __tablename__ = "revoked_tokens"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    revoked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @classmethod
    def is_jti_blocklisted(cls, jti):
        from app.utils.tenant import get_db

        return get_db().query(cls).filter_by(jti=jti).first() is not None

    def __repr__(self):
        return f"<RevokedToken {self.jti}>"
