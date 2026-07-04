from marshmallow import Schema, fields, validate, validates, ValidationError


class FeeOptinBulkAddSchema(Schema):
    """Validate a bulk opt-in request: list of student IDs + optional override amount."""

    student_ids = fields.List(
        fields.Int(strict=True),
        required=True,
        validate=validate.Length(min=1, error="At least one student_id is required."),
    )
    # Per-student base amount. When provided, all students in this batch get the
    # same override. For mixed amounts (e.g. different hostel room types) the
    # admin should make separate calls per group.
    amount_override = fields.Decimal(
        load_default=None,
        places=2,
        as_string=False,
        allow_none=True,
        validate=validate.Range(min=0),
    )

    @validates("student_ids")
    def _no_duplicates(self, value):
        if len(value) != len(set(value)):
            raise ValidationError("student_ids must not contain duplicates.")


class FeeOptinBulkRemoveSchema(Schema):
    """Validate a bulk opt-out (soft-delete) request."""

    student_ids = fields.List(
        fields.Int(strict=True),
        required=True,
        validate=validate.Length(min=1, error="At least one student_id is required."),
    )

    @validates("student_ids")
    def _no_duplicates(self, value):
        if len(value) != len(set(value)):
            raise ValidationError("student_ids must not contain duplicates.")
