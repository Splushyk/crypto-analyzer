from rest_framework.exceptions import APIException, ErrorDetail
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return Response(
            {"error": "Internal Server Error", "code": "internal_server_error"},
            status=500,
        )

    detail = response.data.get("detail") if isinstance(response.data, dict) else None

    if isinstance(detail, ErrorDetail):
        code = detail.code
    elif isinstance(exc, APIException):
        code = exc.default_code
    else:
        code = "error"

    if isinstance(exc, APIException):
        error_msg = str(exc.detail)
    else:
        error_msg = str(exc)

    response.data = {"error": error_msg, "code": code}
    return response
