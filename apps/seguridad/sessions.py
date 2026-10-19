import uuid

from django.contrib.auth import logout
from django.utils import timezone

from apps.seguridad.access import LockState
from apps.seguridad.models import AccesoUsuario

SESSION_TOKEN_KEY = "single_session_token"
CLOSURE_MESSAGE_KEY = "session_closure_message"
CLOSURE_MESSAGE_ATTRIBUTE = "session_closure_message"
CLOSED_ELSEWHERE_MESSAGE = "Tu sesión se cerró porque se inició sesión con tu cuenta en otro dispositivo."
LOCKED_UNTIL_MESSAGE = "Tu sesión se cerró porque tu cuenta quedó bloqueada por intentos fallidos hasta las {hour}."
LOCKED_MESSAGE = (
    "Tu sesión se cerró porque tu cuenta quedó bloqueada por intentos fallidos. "
    "Podrás volver a entrar cuando alguien la desbloquee."
)


def start_single_session(request, user):
    token = uuid.uuid4()
    AccesoUsuario.objects.get_or_create(user=user)
    AccesoUsuario.objects.filter(user=user).update(token_sesion=token)
    request.session[SESSION_TOKEN_KEY] = str(token)


def end_single_session(request, user):
    if user is None:
        return
    token = request.session.get(SESSION_TOKEN_KEY)
    if token:
        AccesoUsuario.objects.filter(user=user, token_sesion=token).update(token_sesion=None)


def is_current_session(request, user, access):
    session_token = request.session.get(SESSION_TOKEN_KEY)
    stored_token = str(access.token_sesion) if access and access.token_sesion else None
    if session_token is None and stored_token is None:
        start_single_session(request, user)
        return True
    return session_token is not None and session_token == stored_token


def locked_session_message(status):
    if status.state is LockState.TEMPORARY:
        return LOCKED_UNTIL_MESSAGE.format(hour=timezone.localtime(status.until).strftime("%H:%M"))
    return LOCKED_MESSAGE


def close_session(request, message):
    logout(request)
    request.session[CLOSURE_MESSAGE_KEY] = message
    setattr(request, CLOSURE_MESSAGE_ATTRIBUTE, message)


def closure_message(request):
    return getattr(request, CLOSURE_MESSAGE_ATTRIBUTE, "")


def pop_closure_message(request):
    return request.session.pop(CLOSURE_MESSAGE_KEY, "")
