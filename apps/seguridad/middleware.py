from django.conf import settings

from apps.seguridad.sessions import close_replaced_session, is_current_session


class SingleSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self.applies_to(request) and not is_current_session(request, request.user):
            close_replaced_session(request)
        return self.get_response(request)

    def applies_to(self, request):
        user = getattr(request, "user", None)
        return settings.SECURITY_SINGLE_SESSION and user is not None and user.is_authenticated
