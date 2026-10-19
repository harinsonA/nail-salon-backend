from django.conf import settings

from apps.seguridad.access import register_login
from apps.seguridad.sessions import end_single_session, start_single_session


def reset_failures_on_login(sender, request, user, **kwargs):
    register_login(user)


def start_session_on_login(sender, request, user, **kwargs):
    if settings.SECURITY_SINGLE_SESSION and request is not None:
        start_single_session(request, user)


def end_session_on_logout(sender, request, user, **kwargs):
    if request is not None:
        end_single_session(request, user)
