from marshmallow import Schema, fields, validate, validates, ValidationError


class FeePaymentCreateSchema(Schema):
    fee_record_id = fields.Integer(required=True)
    amount_paid = fields.Decimal(required=True, places=2, as_string=False)
    payment_method = fields.String(
        required=True,
        validate=validate.OneOf(['cash', 'bank_transfer', 'cheque', 'online']),
    )
    payment_date = fields.Date(required=True)
    transaction_reference = fields.String(load_default=None, allow_none=True)
    remarks = fields.String(load_default=None, allow_none=True)
    collected_by = fields.Integer(load_default=None, allow_none=True)

    @validates('amount_paid')
    def validate_amount(self, value):
        if value <= 0:
            raise ValidationError('amount_paid must be positive')


class DiscountSchema(Schema):
    discount_type = fields.String(
        required=True,
        validate=validate.OneOf(['scholarship', 'sibling', 'staff', 'custom']),
    )
    amount = fields.Decimal(required=True, places=2, as_string=False)
    reason = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=500))

    @validates('amount')
    def validate_amount(self, value):
        if value <= 0:
            raise ValidationError('amount must be positive')
