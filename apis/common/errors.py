from rest_framework import exceptions, status
from rest_framework.views import exception_handler

from apis.common import messages
from apps.common.api_request import ERROR_CODES, ApiRequest


class ApiError(exceptions.APIException):
    def __init__(self, message=None, code=None, extra=None):
        super().__init__(detail=message or self.default_detail, code=code or self.default_code)
        self.extra = extra or {}


class OutdatedVersion(ApiError):
    status_code = status.HTTP_426_UPGRADE_REQUIRED
    default_detail = messages.OUTDATED_VERSION
    default_code = "outdated_version"


class AppDisabled(ApiError):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = messages.APP_DISABLED
    default_code = "app_disabled"


class Maintenance(ApiError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = messages.MAINTENANCE
    default_code = "maintenance"


class BusinessUnavailable(ApiError):
    default_code = "business_unavailable"

    def __init__(self, status_code, message, code):
        self.status_code = status_code
        super().__init__(message, code)


class PaymentPending(ApiError):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_code = "payment_pending"


class SessionRequired(ApiError):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = messages.SESSION_REQUIRED
    default_code = "session_required"


class SessionEnded(ApiError):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = messages.SESSION_REQUIRED
    default_code = "session_required"


class InvalidCredentials(ApiError):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "invalid_credentials"


class AccountLocked(ApiError):
    status_code = status.HTTP_423_LOCKED
    default_code = "account_locked"


class TooManyRequests(ApiError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = messages.TOO_MANY_REQUESTS
    default_code = "too_many_requests"


class UserLimitReached(ApiError):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "user_limit_reached"


class TemporaryPassword(ApiError):
    status_code = status.HTTP_428_PRECONDITION_REQUIRED
    default_detail = messages.TEMPORARY_PASSWORD
    default_code = "temporary_password"


class Forbidden(ApiError):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = messages.ADMINISTRATION_ONLY
    default_code = "forbidden"


class TeamDisabled(Forbidden):
    default_code = "team_disabled"


class ApiErrorFormat:
    @staticmethod
    def first_message(detail):
        while isinstance(detail, (list, dict)):
            if not detail:
                return ""
            detail = detail[0] if isinstance(detail, list) else next(iter(detail.values()))
        return str(detail)

    @classmethod
    def fields_of(cls, detail):
        if not isinstance(detail, dict):
            return None
        return {
            field: [str(error) for error in (errors if isinstance(errors, list) else [errors])]
            for field, errors in detail.items()
        }

    @classmethod
    def body(cls, exc, status_code, detail):
        if isinstance(exc, exceptions.ValidationError):
            fields = cls.fields_of(exc.detail)
            general = (fields or {}).pop("non_field_errors", None)
            if general:
                message = general[0]
            elif fields is None:
                message = cls.first_message(exc.detail)
            else:
                message = messages.INVALID_DATA
            return ApiRequest.error_body("invalid_data", message, fields)
        if isinstance(exc, ApiError):
            return {**ApiRequest.error_body(exc.get_codes(), cls.first_message(exc.detail)), **exc.extra}
        return ApiRequest.error_body(ERROR_CODES.get(status_code, "error"), cls.first_message(detail))


def handle_exception(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data = ApiErrorFormat.body(exc, response.status_code, response.data)
    return response
