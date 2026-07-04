from marshmallow import Schema, fields, validate

VALID_STATUSES = ["present", "absent", "late", "leave", "holiday"]


class AttendanceRecordSchema(Schema):
    student_id = fields.Int(required=True)
    status = fields.Str(required=True, validate=validate.OneOf(VALID_STATUSES))


class AttendanceMarkSchema(Schema):
    section_id = fields.Int(required=True)
    date = fields.Date(required=True)
    records = fields.List(fields.Nested(AttendanceRecordSchema), required=True, validate=validate.Length(min=1))


class AttendanceDateEntrySchema(Schema):
    date = fields.Date(required=True)
    status = fields.Str(required=True, validate=validate.OneOf(VALID_STATUSES))


class AttendanceStudentRangeSchema(Schema):
    """Bulk/weekly attendance for a single student across multiple dates (admin only)."""

    student_id = fields.Int(required=True)
    entries = fields.List(
        fields.Nested(AttendanceDateEntrySchema),
        required=True,
        validate=validate.Length(min=1),
    )
