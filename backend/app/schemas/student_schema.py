from marshmallow import Schema, fields, validate, validates, ValidationError
from datetime import date


VALID_GENDERS = ["Male", "Female", "Other"]
VALID_BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
VALID_STATUSES = ["active", "alumni", "transferred", "expelled"]


class StudentCreateSchema(Schema):
    # Required fields
    first_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    last_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    date_of_birth = fields.Date(required=True)
    gender = fields.Str(required=True, validate=validate.OneOf(VALID_GENDERS))
    admission_date = fields.Date(required=True)
    admission_no = fields.Str(required=True, validate=validate.Length(min=1, max=20))

    # Optional fields
    blood_group = fields.Str(
        load_default=None,
        validate=validate.OneOf(VALID_BLOOD_GROUPS),
        allow_none=True,
    )
    address = fields.Str(load_default=None, allow_none=True)
    phone = fields.Str(
        load_default=None,
        validate=validate.Length(max=20),
        allow_none=True,
    )
    photo_url = fields.Str(
        load_default=None,
        validate=validate.Length(max=500),
        allow_none=True,
    )
    user_id = fields.Int(load_default=None, allow_none=True)

    @validates("date_of_birth")
    def validate_dob(self, value):
        if value > date.today():
            raise ValidationError("Date of birth cannot be in the future.")

    @validates("admission_date")
    def validate_admission_date(self, value):
        if value > date.today():
            raise ValidationError("Admission date cannot be in the future.")


class StudentUpdateSchema(Schema):
    """Full admin update — all fields optional."""

    first_name = fields.Str(validate=validate.Length(min=1, max=100))
    last_name = fields.Str(validate=validate.Length(min=1, max=100))
    date_of_birth = fields.Date()
    gender = fields.Str(validate=validate.OneOf(VALID_GENDERS))
    blood_group = fields.Str(
        validate=validate.OneOf(VALID_BLOOD_GROUPS),
        allow_none=True,
    )
    address = fields.Str(allow_none=True)
    phone = fields.Str(validate=validate.Length(max=20), allow_none=True)
    photo_url = fields.Str(validate=validate.Length(max=500), allow_none=True)

    @validates("date_of_birth")
    def validate_dob(self, value):
        if value > date.today():
            raise ValidationError("Date of birth cannot be in the future.")


class StudentSelfUpdateSchema(Schema):
    """Self-service update — students can only change phone and address."""

    phone = fields.Str(validate=validate.Length(max=20), allow_none=True)
    address = fields.Str(allow_none=True)


class StudentStatusSchema(Schema):
    status = fields.Str(required=True, validate=validate.OneOf(VALID_STATUSES))
    leaving_date = fields.Date(load_default=None, allow_none=True)


class StudentTransferSchema(Schema):
    new_section_id = fields.Int(required=True)
    effective_date = fields.Date(required=True)
    reason = fields.Str(
        load_default="",
        validate=validate.Length(max=500),
    )


class ParentLinkSchema(Schema):
    parent_id = fields.Int(required=True)
    is_primary_contact = fields.Bool(load_default=False)
