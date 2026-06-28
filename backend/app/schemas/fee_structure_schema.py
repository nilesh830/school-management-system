from marshmallow import Schema, fields, validate, validates_schema, ValidationError

VALID_FREQUENCIES = ("monthly", "quarterly", "annual", "one_time")


class FeeStructureCreateSchema(Schema):
    class_id = fields.Int(required=True)
    academic_year_id = fields.Int(required=True)
    fee_type = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    amount = fields.Decimal(
        required=True,
        places=2,
        as_string=False,
        validate=validate.Range(min=0),
    )
    due_date = fields.Date(load_default=None, allow_none=True)
    is_recurring = fields.Bool(load_default=False)
    frequency = fields.Str(
        load_default="one_time",
        validate=validate.OneOf(VALID_FREQUENCIES),
    )

    @validates_schema
    def _due_date_required_for_one_time(self, data, **kwargs):
        # One-time fees need an explicit due date (it becomes the record's due
        # date). Recurring fees derive a due date per period (end of month), so
        # the structure-level due_date is optional there.
        if data.get("frequency", "one_time") == "one_time" and not data.get("due_date"):
            raise ValidationError(
                "Due date is required for one-time fees.", field_name="due_date"
            )


class FeeStructureUpdateSchema(Schema):
    fee_type = fields.Str(load_default=None, validate=validate.Length(min=1, max=100))
    amount = fields.Decimal(
        load_default=None,
        places=2,
        as_string=False,
        validate=validate.Range(min=0),
    )
    due_date = fields.Date(load_default=None, allow_none=True)
    is_recurring = fields.Bool(load_default=None)
    frequency = fields.Str(
        load_default=None,
        validate=validate.OneOf(VALID_FREQUENCIES),
    )
    is_active = fields.Bool(load_default=None)
