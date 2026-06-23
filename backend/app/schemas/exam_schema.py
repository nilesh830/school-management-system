from marshmallow import Schema, fields, validate

VALID_EXAM_TYPES = ["midterm", "final", "unit_test", "practical"]


class ExamCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    term = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    exam_type = fields.Str(
        required=True,
        validate=validate.OneOf(VALID_EXAM_TYPES),
    )
    section_id = fields.Int(required=True)
    academic_year_id = fields.Int(required=True)
    conducted_date = fields.Date(load_default=None)


class ExamUpdateSchema(Schema):
    name = fields.Str(load_default=None, validate=validate.Length(min=1, max=200))
    term = fields.Str(load_default=None, validate=validate.Length(min=1, max=50))
    exam_type = fields.Str(
        load_default=None,
        validate=validate.OneOf(VALID_EXAM_TYPES),
    )
    conducted_date = fields.Date(load_default=None)
    is_active = fields.Bool(load_default=None)


class MarkEntrySchema(Schema):
    student_id = fields.Int(required=True)
    marks_obtained = fields.Float(required=True, validate=validate.Range(min=0))


class ExamMarksSchema(Schema):
    subject_id = fields.Int(required=True)
    section_id = fields.Int(required=True)
    marks = fields.List(
        fields.Nested(MarkEntrySchema),
        required=True,
        validate=validate.Length(min=1),
    )


class UpdateMarkSchema(Schema):
    marks_obtained = fields.Float(required=True, validate=validate.Range(min=0))
