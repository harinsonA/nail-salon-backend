from django.conf import settings

from apps.seguridad.access import status_of
from apps.seguridad.models import AccesoUsuario
from apps.seguridad.sessions import (
    CLOSED_ELSEWHERE_MESSAGE,
    close_session,
    is_current_session,
    locked_session_message,
)


class SessionGuardMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            self.guard(request, user)
        return self.get_response(request)

    def guard(self, request, user):
        access = AccesoUsuario.objects.filter(user=user).first()
        status = status_of(access)
        if status.is_locked:
            close_session(request, locked_session_message(status))
        elif settings.SECURITY_SINGLE_SESSION and not is_current_session(request, user, access):
            close_session(request, CLOSED_ELSEWHERE_MESSAGE)
