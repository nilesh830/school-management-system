from marshmallow import Schema, fields, validate


# ── Routes (SMS-061) ─────────────────────────────────────────────────────────

class RouteCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    description = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=255))
    stops = fields.List(fields.Str(validate=validate.Length(min=1, max=100)), load_default=None, allow_none=True)


class RouteUpdateSchema(Schema):
    name = fields.Str(load_default=None, validate=validate.Length(min=1, max=100))
    description = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=255))
    stops = fields.List(fields.Str(validate=validate.Length(min=1, max=100)), load_default=None, allow_none=True)
    is_active = fields.Bool(load_default=None)


# ── Vehicles (SMS-061) ───────────────────────────────────────────────────────

class VehicleCreateSchema(Schema):
    registration_no = fields.Str(required=True, validate=validate.Length(min=1, max=20))
    capacity = fields.Int(required=True, validate=validate.Range(min=1))
    driver_name = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=100))
    driver_phone = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=20))
    route_id = fields.Int(load_default=None, allow_none=True)


class VehicleUpdateSchema(Schema):
    registration_no = fields.Str(load_default=None, validate=validate.Length(min=1, max=20))
    capacity = fields.Int(load_default=None, validate=validate.Range(min=1))
    driver_name = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=100))
    driver_phone = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=20))
    route_id = fields.Int(load_default=None, allow_none=True)
    is_active = fields.Bool(load_default=None)


# ── Student assignments (SMS-062) ────────────────────────────────────────────

class AssignmentCreateSchema(Schema):
    student_id = fields.Int(required=True)
    route_id = fields.Int(required=True)
    pickup_stop = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=100))
    drop_stop = fields.Str(load_default=None, allow_none=True, validate=validate.Length(max=100))
    academic_year_id = fields.Int(required=True)
