from app import db
from datetime import datetime


class TransportVehicle(db.Model):
    __tablename__ = "transport_vehicles"

    id = db.Column(db.Integer, primary_key=True)
    registration_no = db.Column(db.String(20), unique=True, nullable=False, index=True)
    capacity = db.Column(db.Integer, nullable=False)
    driver_name = db.Column(db.String(100), nullable=True)
    driver_phone = db.Column(db.String(20), nullable=True)
    route_id = db.Column(db.Integer, db.ForeignKey("transport_routes.id"), nullable=True, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "registration_no": self.registration_no,
            "capacity": self.capacity,
            "driver_name": self.driver_name,
            "driver_phone": self.driver_phone,
            "route_id": self.route_id,
            "route_name": self.route.name if self.route else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<TransportVehicle id={self.id} reg={self.registration_no!r}>"
