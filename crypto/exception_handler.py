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
    code = getattr(detail, "code", None) or getattr(exc, "default_code", "error")
    response.data = {
        "error": str(exc.detail) if hasattr(exc, "detail") else str(exc),
        "code": code,
    }
    return response
