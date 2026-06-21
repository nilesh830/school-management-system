from marshmallow import Schema, fields, validate

VALID_FREQUENCIES = ('monthly', 'quarterly', 'annual', 'one_time')


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
        load_default='one_time',
        validate=validate.OneOf(VALID_FREQUENCIES),
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
