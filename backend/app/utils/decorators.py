from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("role") not in roles:
                return (
                    jsonify({"success": False, "message": "Insufficient permissions", "data": None, "errors": None}),
                    403,
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def validate_schema(schema_class):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            from flask import request

            schema = schema_class()
            errors = schema.validate(request.get_json() or {})
            if errors:
                return jsonify({"success": False, "message": "Validation failed", "data": None, "errors": errors}), 422
            validated_data = schema.load(request.get_json())
            return fn(validated_data, *args, **kwargs)

        return wrapper

    return decorator
