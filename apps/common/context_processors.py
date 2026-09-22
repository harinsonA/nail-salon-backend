from apps.common.middleware import SESSION_IDLE_SECONDS_KEY


def session_expiry(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {"session_idle_seconds": request.session.get(SESSION_IDLE_SECONDS_KEY) or 0}
