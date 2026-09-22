from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import logout
from django.utils import timezone

SESSION_IDLE_SECONDS_KEY = "session_idle_seconds"
SESSION_LAST_ACTIVITY_KEY = "session_last_activity"
SESSION_DEADLINE_KEY = "session_deadline"

ACTIVITY_REFRESH_SECONDS = 60


def get_daily_deadline(moment: datetime = None) -> datetime:
    moment = moment or timezone.localtime()
    deadline = moment.replace(
        hour=settings.SESSION_DAILY_CUTOFF_HOUR,
        minute=0,
        second=0,
        microsecond=0,
    )
    if deadline <= moment:
        deadline += timedelta(days=1)
    return deadline


def start_session_window(session, idle_seconds: int) -> None:
    session[SESSION_IDLE_SECONDS_KEY] = idle_seconds
    session[SESSION_LAST_ACTIVITY_KEY] = timezone.now().timestamp()
    session[SESSION_DEADLINE_KEY] = get_daily_deadline().timestamp()


class SessionExpiryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and self.is_expired(request):
            logout(request)
            request.session_expired = True
        return self.get_response(request)

    def is_expired(self, request) -> bool:
        session = request.session
        deadline = session.get(SESSION_DEADLINE_KEY)
        last_activity = session.get(SESSION_LAST_ACTIVITY_KEY)
        if not deadline or not last_activity:
            return True

        now = timezone.now().timestamp()
        if now >= deadline:
            return True

        idle_seconds = session.get(SESSION_IDLE_SECONDS_KEY) or 0
        if idle_seconds and now - last_activity >= idle_seconds:
            return True

        if now - last_activity >= ACTIVITY_REFRESH_SECONDS:
            session[SESSION_LAST_ACTIVITY_KEY] = now
        return False
