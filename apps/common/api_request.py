from django.http import JsonResponse

ERROR_CODES = {
    400: "bad_request",
    401: "session_required",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    415: "unsupported_media_type",
    429: "too_many_requests",
    500: "server_error",
}


class ApiRequest:
    PREFIX = "/api/"

    @classmethod
    def matches(cls, request) -> bool:
        return request.path_info.startswith(cls.PREFIX)

    @staticmethod
    def error_body(code, message, fields=None) -> dict:
        body = {"code": code, "message": message}
        if fields:
            body["fields"] = fields
        return body

    @classmethod
    def error_response(cls, status, message, code=None) -> JsonResponse:
        return JsonResponse(cls.error_body(code or ERROR_CODES.get(status, "error"), message), status=status)
