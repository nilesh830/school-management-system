from app.utils.tenant import get_db
from app.models.transport_route import TransportRoute
from app.models.transport_vehicle import TransportVehicle
from app.models.student_transport import StudentTransport
from app.models.student import Student
from app.models.academic_year import AcademicYear


class TransportService:

    # ── Routes (SMS-061) ─────────────────────────────────────────────────────

    @classmethod
    def create_route(cls, data: dict):
        db = get_db()
        route = TransportRoute(
            name=data['name'],
            description=data.get('description'),
            stops_json=data.get('stops') or [],
        )
        db.add(route)
        db.commit()
        return route.to_dict(), None

    @classmethod
    def get_routes(cls, active_only=True):
        db = get_db()
        query = db.query(TransportRoute)
        if active_only:
            query = query.filter_by(is_active=True)
        results = query.order_by(TransportRoute.name.asc()).all()
        return [r.to_dict() for r in results]

    @classmethod
    def get_route(cls, route_id: int):
        db = get_db()
        route = db.query(TransportRoute).filter_by(id=route_id).first()
        if not route:
            return None, {'message': f'TransportRoute {route_id} not found', 'status': 404}
        return route.to_dict(), None

    @classmethod
    def update_route(cls, route_id: int, data: dict):
        db = get_db()
        route = db.query(TransportRoute).filter_by(id=route_id).first()
        if not route:
            return None, {'message': f'TransportRoute {route_id} not found', 'status': 404}

        if data.get('name') is not None:
            route.name = data['name']
        if 'description' in data:
            route.description = data['description']
        if data.get('stops') is not None:
            route.stops_json = data['stops']
        if data.get('is_active') is not None:
            route.is_active = data['is_active']

        db.commit()
        return route.to_dict(), None

    @classmethod
    def delete_route(cls, route_id: int):
        db = get_db()
        route = db.query(TransportRoute).filter_by(id=route_id).first()
        if not route:
            return None, {'message': f'TransportRoute {route_id} not found', 'status': 404}

        route.is_active = False
        db.commit()
        return {'id': route_id, 'deleted': True}, None

    # ── Vehicles (SMS-061) ───────────────────────────────────────────────────

    @classmethod
    def create_vehicle(cls, data: dict):
        db = get_db()

        existing = db.query(TransportVehicle).filter_by(
            registration_no=data['registration_no']
        ).first()
        if existing:
            return None, {
                'message': f"Vehicle with registration_no {data['registration_no']} already exists",
                'status': 409,
            }

        route_id = data.get('route_id')
        if route_id is not None:
            route = db.query(TransportRoute).filter_by(id=route_id).first()
            if not route:
                return None, {'message': f'TransportRoute {route_id} not found', 'status': 404}

        vehicle = TransportVehicle(
            registration_no=data['registration_no'],
            capacity=data['capacity'],
            driver_name=data.get('driver_name'),
            driver_phone=data.get('driver_phone'),
            route_id=route_id,
        )
        db.add(vehicle)
        db.commit()
        return vehicle.to_dict(), None

    @classmethod
    def get_vehicles(cls, route_id=None, active_only=True):
        db = get_db()
        query = db.query(TransportVehicle)
        if active_only:
            query = query.filter_by(is_active=True)
        if route_id is not None:
            query = query.filter_by(route_id=route_id)
        results = query.order_by(TransportVehicle.registration_no.asc()).all()
        return [v.to_dict() for v in results]

    @classmethod
    def get_vehicle(cls, vehicle_id: int):
        db = get_db()
        vehicle = db.query(TransportVehicle).filter_by(id=vehicle_id).first()
        if not vehicle:
            return None, {'message': f'TransportVehicle {vehicle_id} not found', 'status': 404}
        return vehicle.to_dict(), None

    @classmethod
    def update_vehicle(cls, vehicle_id: int, data: dict):
        db = get_db()
        vehicle = db.query(TransportVehicle).filter_by(id=vehicle_id).first()
        if not vehicle:
            return None, {'message': f'TransportVehicle {vehicle_id} not found', 'status': 404}

        if data.get('registration_no') is not None and data['registration_no'] != vehicle.registration_no:
            clash = db.query(TransportVehicle).filter_by(
                registration_no=data['registration_no']
            ).first()
            if clash:
                return None, {
                    'message': f"Vehicle with registration_no {data['registration_no']} already exists",
                    'status': 409,
                }
            vehicle.registration_no = data['registration_no']
        if data.get('capacity') is not None:
            vehicle.capacity = data['capacity']
        if 'driver_name' in data:
            vehicle.driver_name = data['driver_name']
        if 'driver_phone' in data:
            vehicle.driver_phone = data['driver_phone']
        if 'route_id' in data and data['route_id'] is not None:
            route = db.query(TransportRoute).filter_by(id=data['route_id']).first()
            if not route:
                return None, {'message': f"TransportRoute {data['route_id']} not found", 'status': 404}
            vehicle.route_id = data['route_id']
        elif 'route_id' in data:
            vehicle.route_id = None
        if data.get('is_active') is not None:
            vehicle.is_active = data['is_active']

        db.commit()
        return vehicle.to_dict(), None

    # ── Student assignments (SMS-062) ─────────────────────────────────────────

    @classmethod
    def assign_student(cls, data: dict):
        """
        Assign a student to a transport route for an academic year.

        Reassignment is an in-place upsert keyed on (student_id, academic_year_id):
        an existing assignment for that student+year is updated to the new route
        (closing the old association) rather than creating a duplicate, honoring
        the UniqueConstraint.
        """
        db = get_db()

        student = db.query(Student).filter_by(id=data['student_id']).first()
        if not student:
            return None, {'message': f"Student {data['student_id']} not found", 'status': 404}

        route = db.query(TransportRoute).filter_by(id=data['route_id']).first()
        if not route:
            return None, {'message': f"TransportRoute {data['route_id']} not found", 'status': 404}

        ay = db.query(AcademicYear).filter_by(id=data['academic_year_id']).first()
        if not ay:
            return None, {'message': f"AcademicYear {data['academic_year_id']} not found", 'status': 404}

        existing = db.query(StudentTransport).filter_by(
            student_id=data['student_id'],
            academic_year_id=data['academic_year_id'],
        ).first()

        if existing:
            existing.route_id = data['route_id']
            existing.pickup_stop = data.get('pickup_stop')
            existing.drop_stop = data.get('drop_stop')
            existing.is_active = True
            db.commit()
            return existing.to_dict(), None

        assignment = StudentTransport(
            student_id=data['student_id'],
            route_id=data['route_id'],
            pickup_stop=data.get('pickup_stop'),
            drop_stop=data.get('drop_stop'),
            academic_year_id=data['academic_year_id'],
        )
        db.add(assignment)
        db.commit()
        return assignment.to_dict(), None

    @classmethod
    def unassign_student(cls, assignment_id: int):
        db = get_db()
        assignment = db.query(StudentTransport).filter_by(id=assignment_id).first()
        if not assignment:
            return None, {'message': f'StudentTransport {assignment_id} not found', 'status': 404}

        assignment.is_active = False
        db.commit()
        return {'id': assignment_id, 'unassigned': True}, None

    @classmethod
    def get_assignments(cls, route_id=None, active_only=True):
        db = get_db()
        query = db.query(StudentTransport)
        if active_only:
            query = query.filter_by(is_active=True)
        if route_id is not None:
            query = query.filter_by(route_id=route_id)
        results = query.order_by(StudentTransport.id.asc()).all()
        return [a.to_dict() for a in results]

    @classmethod
    def get_student_transport(cls, student_id: int):
        """Return a student's current (active) transport assignment, or None."""
        db = get_db()
        student = db.query(Student).filter_by(id=student_id).first()
        if not student:
            return None, {'message': f'Student {student_id} not found', 'status': 404}

        assignment = db.query(StudentTransport).filter_by(
            student_id=student_id, is_active=True
        ).order_by(StudentTransport.id.desc()).first()
        return (assignment.to_dict() if assignment else None), None
