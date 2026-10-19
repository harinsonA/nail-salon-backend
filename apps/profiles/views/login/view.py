from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import LogoutView as DjangoLogoutView

from apps.profiles.models import Perfil
from apps.profiles.permisos import rol_de
from apps.seguridad.forms import LockAwareAuthenticationMixin

"""========================================================================="""
# region ........ Constants


UNLOCK_HINTS = {
    Perfil.Rol.PROPIETARIO: "pide ayuda al soporte de Hi Agenda",
    Perfil.Rol.ENCARGADO: "pide al propietario del negocio que te desbloquee",
}
DEFAULT_UNLOCK_HINT = "pide al propietario o a un encargado que te desbloquee"


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Forms


class CorreoAuthenticationForm(LockAwareAuthenticationMixin, AuthenticationForm):
    error_messages = {
        "invalid_login": "Correo o contraseña incorrectos.",
        "inactive": "Esta cuenta está desactivada.",
    }

    def get_unlock_hint(self, user):
        return UNLOCK_HINTS.get(rol_de(user) if user else None, DEFAULT_UNLOCK_HINT)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Correo"
        self.fields["username"].max_length = 254
        self.fields["username"].widget.attrs["maxlength"] = 254


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Views


class LoginView(DjangoLoginView):
    template_name = "login/index.html"
    authentication_form = CorreoAuthenticationForm


class LogoutView(DjangoLogoutView):
    pass


# endregion
"""========================================================================="""
