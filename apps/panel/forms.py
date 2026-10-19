from django.contrib.admin.forms import AdminAuthenticationForm

from apps.seguridad.forms import LockAwareAuthenticationMixin


class PanelAuthenticationForm(LockAwareAuthenticationMixin, AdminAuthenticationForm):
    error_messages = {
        **AdminAuthenticationForm.error_messages,
        "invalid_login": "Usuario o contraseña incorrectos.",
    }
    unlock_hint = "pide a otro administrador del panel que la desbloquee"
