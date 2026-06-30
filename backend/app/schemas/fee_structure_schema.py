from marshmallow import Schema, fields, validate, validates_schema, ValidationError

VALID_FREQUENCIES = ("monthly", "quarterly", "annual", "one_time")
VALID_APPLICABILITY = ("mandatory", "optional")
VALID_SOURCE_KIND = ("flat", "transport")


class FeeStructureCreateSchema(Schema):
    class_id = fields.Int(required=True)
    academic_year_id = fields.Int(required=True)
    fee_type = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    amount = fields.Decimal(
        load_default=None,
        places=2,
        as_string=False,
        validate=validate.Range(min=0),
        allow_none=True,
    )
    due_date = fields.Date(load_default=None, allow_none=True)
    is_recurring = fields.Bool(load_default=False)
    frequency = fields.Str(
        load_default="one_time",
        validate=validate.OneOf(VALID_FREQUENCIES),
    )
    applicability = fields.Str(
        load_default="mandatory",
        validate=validate.OneOf(VALID_APPLICABILITY),
    )
    source_kind = fields.Str(
        load_default="flat",
        validate=validate.OneOf(VALID_SOURCE_KIND),
    )
    transport_route_id = fields.Int(load_default=None, allow_none=True)

    @validates_schema
    def _validate(self, data, **kwargs):
        source_kind = data.get("source_kind", "flat")

        if source_kind == "transport":
            # Transport fees are implicitly optional; their amount comes from the
            # route fare, so the structure amount is optional (defaults to 0).
            data["applicability"] = "optional"
            if data.get("amount") is None:
                data["amount"] = 0
            # transport_route_id is optional (None = any route the student is on).
            return

        # source_kind == 'flat'
        if data.get("transport_route_id") is not None:
            raise ValidationError(
                "transport_route_id is only allowed when source_kind='transport'.",
                field_name="transport_route_id",
            )
        if data.get("amount") is None:
            raise ValidationError(
                "amount is required for flat fee structures.", field_name="amount"
            )
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
    applicability = fields.Str(
        load_default=None,
        validate=validate.OneOf(VALID_APPLICABILITY),
    )
    source_kind = fields.Str(
        load_default=None,
        validate=validate.OneOf(VALID_SOURCE_KIND),
    )
    transport_route_id = fields.Int(load_default=None, allow_none=True)
    is_active = fields.Bool(load_default=None)

    @validates_schema
    def _validate(self, data, **kwargs):
        source_kind = data.get("source_kind")
        if source_kind == "transport":
            # Enforce transport ⇒ optional at the edge too (service also enforces).
            data["applicability"] = "optional"
        elif source_kind == "flat":
            if data.get("transport_route_id") is not None:
                raise ValidationError(
                    "transport_route_id is only allowed when source_kind='transport'.",
                    field_name="transport_route_id",
                )
