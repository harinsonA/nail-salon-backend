import uuid

from django.contrib.auth import logout

from apps.seguridad.models import AccesoUsuario

SESSION_TOKEN_KEY = "single_session_token"
CLOSED_ELSEWHERE_KEY = "single_session_closed_elsewhere"
CLOSED_ELSEWHERE_ATTRIBUTE = "session_closed_elsewhere"
CLOSED_ELSEWHERE_MESSAGE = "Tu sesión se cerró porque se inició sesión con tu cuenta en otro dispositivo."


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


def current_token(user):
    token = AccesoUsuario.objects.filter(user=user).values_list("token_sesion", flat=True).first()
    return str(token) if token else None


def is_current_session(request, user):
    session_token = request.session.get(SESSION_TOKEN_KEY)
    stored_token = current_token(user)
    if session_token is None and stored_token is None:
        start_single_session(request, user)
        return True
    return session_token is not None and session_token == stored_token


def close_replaced_session(request):
    logout(request)
    request.session[CLOSED_ELSEWHERE_KEY] = True
    setattr(request, CLOSED_ELSEWHERE_ATTRIBUTE, True)


def pop_closed_elsewhere(request):
    return bool(request.session.pop(CLOSED_ELSEWHERE_KEY, False))
