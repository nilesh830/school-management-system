from app import db
from datetime import datetime
from sqlalchemy import CheckConstraint


class TransportRoute(db.Model):
    __tablename__ = "transport_routes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    stops_json = db.Column(db.JSON, nullable=True)
    # Per-student fare for this route. NULL until an admin configures it; a route
    # with no fare cannot back a transport fee structure (generation skips such
    # students and reports them rather than silently billing 0).
    fare = db.Column(db.Numeric(10, 2), nullable=True)
    # Recurrence of the fare; overrides the fee structure's own frequency for
    # transport-sourced fees. Same vocabulary as FeeStructure.frequency.
    fare_frequency = db.Column(db.String(20), nullable=False, default="monthly")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint("fare IS NULL OR fare >= 0", name="ck_transport_routes_fare_nonneg"),
        CheckConstraint(
            "fare_frequency IN ('monthly','quarterly','annual','one_time')",
            name="ck_transport_routes_fare_frequency",
        ),
    )

    # Relationships
    vehicles = db.relationship("TransportVehicle", backref="route", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "stops": self.stops_json or [],
            "fare": float(self.fare) if self.fare is not None else None,
            "fare_frequency": self.fare_frequency,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<TransportRoute id={self.id} name={self.name!r}>"
