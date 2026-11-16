from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apis.common import errors
from apis.common.authentication import DEVICE_HEADER, SessionErrors
from apis.common.guards import APP_VERSION_HEADER
from apis.common.views import ApiView
from apis.v1.session.serializers import (
    DeviceKeySerializer,
    LoginSerializer,
    RefreshSerializer,
    SessionKeySerializer,
)
from apps.profiles.middleware import debe_cambiar_clave
from apps.seguridad.mobile import MobileSession, MobileSessionError, PasswordLogin
from apps.tenancy.user_limit import UserLimit
from apps.tenancy.user_limit.messages import OVER_LIMIT_LOGIN

"""========================================================================="""
# region ........ Mixins


class OpenSessionMixin:
    authentication_classes = []
    requires_session = False
    throttle_classes = [ScopedRateThrottle]
    http_method_names = ["post"]

    def open_session(self, start):
        try:
            session = start()
        except MobileSessionError as error:
            raise SessionErrors.to_api(error)
        return Response(
            SessionKeySerializer(
                {
                    "session_key": session.session_key.key,
                    "expires_at": session.session_key.expires_at,
                    "temporary_password": debe_cambiar_clave(session.user),
                    "biometric": session.has_device_key,
                }
            ).data
        )

    def admit(self, user):
        if not UserLimit.for_request(self.request).lets_in(user):
            raise errors.UserLimitReached(OVER_LIMIT_LOGIN)

    @staticmethod
    def valid_data(serializer_class, request):
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    @staticmethod
    def app_version(request):
        return request.headers.get(APP_VERSION_HEADER, "")


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class LoginView(OpenSessionMixin, ApiView):
    throttle_scope = "session_login"

    @extend_schema(
        summary="Entrar",
        description="Correo y clave. Entrega la llave de sesión, que vence en el próximo corte de las 4:00.",
        request=LoginSerializer,
        responses=SessionKeySerializer,
    )
    def post(self, request, *args, **kwargs):
        data = self.valid_data(LoginSerializer, request)

        def start():
            user = PasswordLogin(request._request).user_for(data["email"], data["password"])
            self.admit(user)
            return MobileSession.log_in(user, request.headers.get(DEVICE_HEADER, ""), self.app_version(request))

        return self.open_session(start)


class RefreshView(OpenSessionMixin, ApiView):
    throttle_scope = "session_refresh"

    @extend_schema(
        summary="Renovar",
        description="Con la llave del teléfono entrega una llave de sesión nueva y alarga la del teléfono 30 días.",
        request=RefreshSerializer,
        responses=SessionKeySerializer,
    )
    def post(self, request, *args, **kwargs):
        data = self.valid_data(RefreshSerializer, request)
        return self.open_session(lambda: MobileSession.refresh(data["device_key"], self.app_version(request), self.admit))


class BiometricView(ApiView):
    http_method_names = ["post", "delete"]

    @extend_schema(
        summary="Activar huella",
        description="Entrega la llave del teléfono (30 días sin uso), que la app guarda bajo la huella.",
        request=None,
        responses=DeviceKeySerializer,
    )
    def post(self, request, *args, **kwargs):
        issued = request.auth.enable_biometric()
        return Response(DeviceKeySerializer({"device_key": issued.key, "expires_at": issued.expires_at}).data)

    @extend_schema(summary="Desactivar huella", description="Anula la llave del teléfono.", responses={204: None})
    def delete(self, request, *args, **kwargs):
        request.auth.disable_biometric()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LogoutView(ApiView):
    allows_temporary_password = True
    http_method_names = ["post"]

    @extend_schema(summary="Salir", description="Anula las dos llaves.", request=None, responses={204: None})
    def post(self, request, *args, **kwargs):
        request.auth.log_out()
        return Response(status=status.HTTP_204_NO_CONTENT)


# endregion
"""========================================================================="""
