from flask import jsonify


def success_response(data=None, message="Success", status=200):
    return jsonify({"success": True, "data": data, "message": message, "errors": None}), status


def error_response(message="An error occurred", errors=None, status=400):
    return jsonify({"success": False, "data": None, "message": message, "errors": errors}), status
