from app import db
from datetime import datetime


class Section(db.Model):
    __tablename__ = "sections"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(10), nullable=False)  # e.g. "A"
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False, index=True)
    capacity = db.Column(db.Integer, default=40, nullable=False)
    class_teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # class_ backref is set on Class.sections
    class_teacher = db.relationship("Teacher", backref=db.backref("sections_as_class_teacher", lazy="dynamic"))

    def to_dict(self, include_class=True):
        data = {
            "id": self.id,
            "name": self.name,
            "class_id": self.class_id,
            "capacity": self.capacity,
            "class_teacher_id": self.class_teacher_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_class and self.class_:
            data["class_name"] = self.class_.name
            data["grade_level"] = self.class_.grade_level
        else:
            data["class_name"] = None
            data["grade_level"] = None
        if self.class_teacher:
            data["class_teacher_name"] = f"{self.class_teacher.first_name} {self.class_teacher.last_name}"
        else:
            data["class_teacher_name"] = None
        return data

    def __repr__(self):
        return f"<Section {self.name} class_id={self.class_id}>"
