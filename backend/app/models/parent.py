from app import db
from datetime import datetime

student_parent = db.Table(
    "student_parent",
    db.Column("student_id", db.Integer, db.ForeignKey("students.id"), primary_key=True),
    db.Column("parent_id", db.Integer, db.ForeignKey("parents.id"), primary_key=True),
    db.Column("is_primary_contact", db.Boolean, default=False),
    db.Column("created_at", db.DateTime, default=datetime.utcnow),
)


class Parent(db.Model):
    __tablename__ = "parents"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    relationship_type = db.Column(db.Enum("Father", "Mother", "Guardian", name="relationship_types"), nullable=False)
    phone_primary = db.Column(db.String(20), nullable=False)
    phone_secondary = db.Column(db.String(20))
    occupation = db.Column(db.String(100))
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = db.relationship("User", backref=db.backref("parent", uselist=False))
    students = db.relationship("Student", secondary=student_parent, backref="parents", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": f"{self.first_name} {self.last_name}",
            "relationship_type": self.relationship_type,
            "phone_primary": self.phone_primary,
            "phone_secondary": self.phone_secondary,
            "occupation": self.occupation,
            "address": self.address,
            "is_active": self.is_active,
        }

    def __repr__(self):
        return f"<Parent {self.first_name} {self.last_name} ({self.relationship_type})>"
