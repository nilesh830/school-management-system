import re

from marshmallow import Schema, ValidationError, fields, validate, validates

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$")


class SchoolCreateSchema(Schema):
    # Required
    name = fields.Str(required=True, validate=validate.Length(min=2, max=200))
    slug = fields.Str(required=True, validate=validate.Length(min=2, max=50))
    admin_email = fields.Email(required=True)
    admin_password = fields.Str(required=True, validate=validate.Length(min=8))

    # Optional
    address = fields.Str(load_default=None)
    phone = fields.Str(load_default=None, validate=validate.Length(max=20))
    email = fields.Email(load_default=None)
    logo_url = fields.Str(load_default=None, validate=validate.Length(max=500))
    academic_year_start_month = fields.Int(load_default=6, validate=validate.Range(min=1, max=12))
    admin_first_name = fields.Str(load_default="School", validate=validate.Length(max=100))
    admin_last_name = fields.Str(load_default="Admin", validate=validate.Length(max=100))

    @validates("slug")
    def validate_slug(self, value):
        if not _SLUG_RE.match(value):
            raise ValidationError(
                "Slug must be lowercase alphanumeric with hyphens, 3-50 chars, " "no leading/trailing hyphens."
            )


class SchoolUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=2, max=200))
    address = fields.Str(allow_none=True)
    phone = fields.Str(validate=validate.Length(max=20), allow_none=True)
    email = fields.Email(allow_none=True)
    logo_url = fields.Str(validate=validate.Length(max=500), allow_none=True)
    is_active = fields.Bool()
    academic_year_start_month = fields.Int(validate=validate.Range(min=1, max=12))
