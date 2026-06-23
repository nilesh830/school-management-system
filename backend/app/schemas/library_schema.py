from marshmallow import Schema, fields, validate, validates, ValidationError


class BookCreateSchema(Schema):
    isbn = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=20))
    title = fields.String(required=True, validate=validate.Length(min=1, max=255))
    author = fields.String(required=True, validate=validate.Length(min=1, max=255))
    publisher = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=255))
    category = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=100))
    total_copies = fields.Integer(required=True)

    @validates("total_copies")
    def validate_total_copies(self, value):
        if value < 1:
            raise ValidationError("total_copies must be at least 1")


class BookUpdateSchema(Schema):
    isbn = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=20))
    title = fields.String(load_default=None, validate=validate.Length(min=1, max=255))
    author = fields.String(load_default=None, validate=validate.Length(min=1, max=255))
    publisher = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=255))
    category = fields.String(load_default=None, allow_none=True, validate=validate.Length(max=100))
    total_copies = fields.Integer(load_default=None)
    is_active = fields.Boolean(load_default=None)

    @validates("total_copies")
    def validate_total_copies(self, value):
        if value is not None and value < 1:
            raise ValidationError("total_copies must be at least 1")


class BookIssueSchema(Schema):
    book_id = fields.Integer(required=True)
    student_id = fields.Integer(required=True)
    due_date = fields.Date(required=True)


class BookReturnSchema(Schema):
    returned_date = fields.Date(load_default=None, allow_none=True)
