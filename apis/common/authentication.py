from django.utils import timezone
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.plumbing import build_bearer_security_scheme_object
from rest_framework.authentication import BaseAuthentication, get_authorization_header

from apis.common import errors
from apis.common.guards import APP_VERSION_HEADER
from apps.seguridad.mobile import MobileSession, MobileSessionError

DEVICE_HEADER = "X-Dispositivo"
KEYWORD = b"bearer"


class SessionErrors:
    @staticmethod
    def minutes_left(lock):
        if lock is None or lock.until is None:
            return None
        return max(1, -(-int((lock.until - timezone.now()).total_seconds()) // 60))

    @classmethod
    def to_api(cls, error: MobileSessionError):
        if error.code == "account_locked":
            return errors.AccountLocked(error.message, extra={"minutes_left": cls.minutes_left(error.lock)})
        if error.code == "invalid_credentials":
            return errors.InvalidCredentials(error.message)
        return errors.SessionEnded(error.message, code=error.code)


class BearerKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if not parts or parts[0].lower() != KEYWORD:
            return None
        if len(parts) != 2:
            raise errors.SessionEnded()
        try:
            key = parts[1].decode()
            session = MobileSession.authenticate(
                key, request.headers.get(DEVICE_HEADER, ""), request.headers.get(APP_VERSION_HEADER, "")
            )
        except UnicodeDecodeError:
            raise errors.SessionEnded()
        except MobileSessionError as error:
            raise SessionErrors.to_api(error)
        return session.user, session

    def authenticate_header(self, request):
        return "Bearer"


class BearerKeyScheme(OpenApiAuthenticationExtension):
    target_class = BearerKeyAuthentication
    name = "BearerKey"

    def get_security_definition(self, auto_schema):
        return build_bearer_security_scheme_object(header_name="AUTHORIZATION", token_prefix="Bearer")
