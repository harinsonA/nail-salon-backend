from django.contrib.auth import authenticate

from apps.profiles.login_messages import LoginMessages
from apps.seguridad.forms import LOCK_STATUS_ATTRIBUTE, LOCKED_USER_ATTRIBUTE, last_attempt_warning, locked_message
from apps.seguridad.mobile.session import MobileSessionError


class PasswordLogin:
    def __init__(self, request):
        self.request = request

    def user_for(self, email, password):
        user = authenticate(self.request, username=email, password=password)
        if user is not None:
            return user
        status = getattr(self.request, LOCK_STATUS_ATTRIBUTE, None)
        if status is not None and status.is_locked:
            hint = LoginMessages.unlock_hint(getattr(self.request, LOCKED_USER_ATTRIBUTE, None))
            raise MobileSessionError("account_locked", locked_message(status, hint), status)
        warning = last_attempt_warning(status) if status is not None else ""
        raise MobileSessionError("invalid_credentials", f"{LoginMessages.INVALID_LOGIN} {warning}".strip())
