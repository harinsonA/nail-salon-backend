from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from apps.common.middleware import start_session_window
from apps.settings.preferences import SESSION_IDLE_MINUTES


@receiver(user_logged_in)
def start_user_session_window(sender, request, user, **kwargs):
    start_session_window(request.session, SESSION_IDLE_MINUTES.get(user) * 60)
