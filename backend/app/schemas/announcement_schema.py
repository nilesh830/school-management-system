from marshmallow import Schema, fields, validate

_VALID_ROLES = ['admin', 'teacher', 'student', 'parent']


class AnnouncementCreateSchema(Schema):
    title = fields.String(required=True, validate=validate.Length(min=1, max=200))
    content = fields.String(required=True, validate=validate.Length(min=1))
    target_roles = fields.List(
        fields.String(validate=validate.OneOf(_VALID_ROLES)),
        load_default=None,
        allow_none=True,
    )
    target_class_ids = fields.List(
        fields.Integer(),
        load_default=None,
        allow_none=True,
    )
    publish_at = fields.DateTime(load_default=None, allow_none=True)
    expires_at = fields.DateTime(load_default=None, allow_none=True)


class AnnouncementUpdateSchema(Schema):
    title = fields.String(load_default=None, validate=validate.Length(min=1, max=200))
    content = fields.String(load_default=None, validate=validate.Length(min=1))
    target_roles = fields.List(
        fields.String(validate=validate.OneOf(_VALID_ROLES)),
        load_default=None,
        allow_none=True,
    )
    target_class_ids = fields.List(
        fields.Integer(),
        load_default=None,
        allow_none=True,
    )
    publish_at = fields.DateTime(load_default=None, allow_none=True)
    expires_at = fields.DateTime(load_default=None, allow_none=True)
    status = fields.String(
        load_default=None,
        validate=validate.OneOf(['draft', 'published', 'archived']),
    )
