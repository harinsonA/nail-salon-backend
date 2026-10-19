from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.seguridad.access import LockState

LOCK_STATUS_ATTRIBUTE = "lock_status"
LOCKED_USER_ATTRIBUTE = "lock_status_user"


def locked_message(status, unlock_hint):
    if status.state is LockState.TEMPORARY:
        hour = timezone.localtime(status.until).strftime("%H:%M")
        return (
            f"Esta cuenta quedó bloqueada por intentos fallidos. Podrás volver a intentarlo a las {hour}. "
            f"Si no quieres esperar, {unlock_hint}."
        )
    return f"Esta cuenta está bloqueada por intentos fallidos. Para volver a entrar, {unlock_hint}."


def last_attempt_warning(status):
    if status.remaining_attempts != 1:
        return ""
    if status.next_lock_is_permanent:
        return "Te queda 1 intento antes de que la cuenta se bloquee hasta que alguien la desbloquee."
    return "Te queda 1 intento antes de que la cuenta se bloquee por un rato."


class LockAwareAuthenticationMixin:
    unlock_hint = ""

    def get_unlock_hint(self, user):
        return self.unlock_hint

    def get_invalid_login_error(self):
        status = getattr(self.request, LOCK_STATUS_ATTRIBUTE, None)
        if status is not None and status.is_locked:
            hint = self.get_unlock_hint(getattr(self.request, LOCKED_USER_ATTRIBUTE, None))
            return ValidationError(locked_message(status, hint), code="locked")
        message = str(self.error_messages["invalid_login"])
        warning = last_attempt_warning(status) if status is not None else ""
        return ValidationError(f"{message} {warning}".strip(), code="invalid_login")
