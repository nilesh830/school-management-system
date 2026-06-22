from flask import Blueprint, request

from app.services.transport_service import TransportService
from app.utils.response import success_response, error_response
from app.utils.decorators import roles_required
from app.schemas.transport_schema import (
    RouteCreateSchema,
    RouteUpdateSchema,
    VehicleCreateSchema,
    VehicleUpdateSchema,
    AssignmentCreateSchema,
)

transport_bp = Blueprint('transport', __name__, url_prefix='/api/v1/transport')
# Student-scoped endpoint lives under the students namespace per the API contract.
student_transport_bp = Blueprint('student_transport', __name__, url_prefix='/api/v1/students')

_route_create_schema = RouteCreateSchema()
_route_update_schema = RouteUpdateSchema()
_vehicle_create_schema = VehicleCreateSchema()
_vehicle_update_schema = VehicleUpdateSchema()
_assignment_create_schema = AssignmentCreateSchema()


def _validate(schema, payload):
    errors = schema.validate(payload or {})
    if errors:
        return None, error_response('Validation failed', errors=errors, status=422)
    return schema.load(payload), None


# ===========================================================================
# Routes (SMS-061)
# ===========================================================================

@transport_bp.route('/routes', methods=['POST'], strict_slashes=False)
@roles_required('admin')
def create_route():
    data, err = _validate(_route_create_schema, request.get_json())
    if err:
        return err
    result, svc_err = TransportService.create_route(data)
    if svc_err:
        return error_response(svc_err['message'], status=svc_err.get('status', 400))
    return success_response(data=result, message='Route created successfully', status=201)


@transport_bp.route('/routes', methods=['GET'], strict_slashes=False)
@roles_required('admin', 'teacher')
def list_routes():
    results = TransportService.get_routes()
    return success_response(data={'routes': results}, message='Routes retrieved')


@transport_bp.route('/routes/<int:route_id>', methods=['GET'], strict_slashes=False)
@roles_required('admin', 'teacher')
def get_route(route_id):
    result, svc_err = TransportService.get_route(route_id)
    if svc_err:
        return error_response(svc_err['message'], status=svc_err.get('status', 404))
    return success_response(data=result, message='Route retrieved')


@transport_bp.route('/routes/<int:route_id>', methods=['PUT'], strict_slashes=False)
@roles_required('admin')
def update_route(route_id):
    data, err = _validate(_route_update_schema, request.get_json())
    if err:
        return err
    result, svc_err = TransportService.update_route(route_id, data)
    if svc_err:
        return error_response(svc_err['message'], status=svc_err.get('status', 400))
    return success_response(data=result, message='Route updated successfully')


@transport_bp.route('/routes/<int:route_id>', methods=['DELETE'], strict_slashes=False)
@roles_required('admin')
def delete_route(route_id):
    result, svc_err = TransportService.delete_route(route_id)
    if svc_err:
        return error_response(svc_err['message'], status=svc_err.get('status', 400))
    return success_response(data=result, message='Route deleted successfully')


# ===========================================================================
# Vehicles (SMS-061)
# ===========================================================================

@transport_bp.route('/vehicles', methods=['POST'], strict_slashes=False)
@roles_required('admin')
def create_vehicle():
    data, err = _validate(_vehicle_create_schema, request.get_json())
    if err:
        return err
    result, svc_err = TransportService.create_vehicle(data)
    if svc_err:
        return error_response(svc_err['message'], status=svc_err.get('status', 400))
    return success_response(data=result, message='Vehicle created successfully', status=201)


@transport_bp.route('/vehicles', methods=['GET'], strict_slashes=False)
@roles_required('admin', 'teacher')
def list_vehicles():
    route_id = request.args.get('route_id', type=int)
    results = TransportService.get_vehicles(route_id=route_id)
    return success_response(data={'vehicles': results}, message='Vehicles retrieved')


@transport_bp.route('/vehicles/<int:vehicle_id>', methods=['GET'], strict_slashes=False)
@roles_required('admin', 'teacher')
def get_vehicle(vehicle_id):
    result, svc_err = TransportService.get_vehicle(vehicle_id)
    if svc_err:
        return error_response(svc_err['message'], status=svc_err.get('status', 404))
    return success_response(data=result, message='Vehicle retrieved')


@transport_bp.route('/vehicles/<int:vehicle_id>', methods=['PUT'], strict_slashes=False)
@roles_required('admin')
def update_vehicle(vehicle_id):
    data, err = _validate(_vehicle_update_schema, request.get_json())
    if err:
        return err
    result, svc_err = TransportService.update_vehicle(vehicle_id, data)
    if svc_err:
        return error_response(svc_err['message'], status=svc_err.get('status', 400))
    return success_response(data=result, message='Vehicle updated successfully')


# ===========================================================================
# Student assignments (SMS-062)
# ===========================================================================

@transport_bp.route('/assignments', methods=['POST'], strict_slashes=False)
@roles_required('admin')
def assign_student():
    data, err = _validate(_assignment_create_schema, request.get_json())
    if err:
        return err
    result, svc_err = TransportService.assign_student(data)
    if svc_err:
        return error_response(svc_err['message'], status=svc_err.get('status', 400))
    return success_response(data=result, message='Student assigned to transport', status=201)


@transport_bp.route('/assignments', methods=['GET'], strict_slashes=False)
@roles_required('admin', 'teacher')
def list_assignments():
    route_id = request.args.get('route_id', type=int)
    results = TransportService.get_assignments(route_id=route_id)
    return success_response(data={'assignments': results}, message='Assignments retrieved')


@transport_bp.route('/assignments/<int:assignment_id>', methods=['DELETE'], strict_slashes=False)
@roles_required('admin')
def unassign_student(assignment_id):
    result, svc_err = TransportService.unassign_student(assignment_id)
    if svc_err:
        return error_response(svc_err['message'], status=svc_err.get('status', 400))
    return success_response(data=result, message='Student unassigned from transport')


# ---------------------------------------------------------------------------
# GET /api/v1/students/<id>/transport — student's current transport (SMS-062)
# ---------------------------------------------------------------------------

@student_transport_bp.route('/<int:student_id>/transport', methods=['GET'], strict_slashes=False)
@roles_required('admin', 'teacher')
def get_student_transport(student_id):
    result, svc_err = TransportService.get_student_transport(student_id)
    if svc_err:
        return error_response(svc_err['message'], status=svc_err.get('status', 404))
    return success_response(data={'transport': result}, message='Student transport retrieved')
