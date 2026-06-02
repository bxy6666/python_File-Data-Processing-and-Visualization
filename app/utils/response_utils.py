"""统一 API JSON 响应格式。"""

from flask import jsonify


def success_payload(code, message, data=None):
    return {
        "status": "success",
        "code": code,
        "message": message,
        "data": data or {},
    }


def error_payload(code, message, data=None):
    return {
        "status": "error",
        "code": code,
        "message": message,
        "data": data or {},
    }


def json_response(payload, http_status=200):
    return jsonify(payload), http_status


def success_response(code, message, data=None, http_status=200):
    return json_response(success_payload(code, message, data), http_status)


def error_response(code, message, data=None, http_status=400):
    return json_response(error_payload(code, message, data), http_status)
