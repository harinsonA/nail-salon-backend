from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.core.exceptions import ValidationError
from django_tenants.utils import get_public_schema_name

from apps.profiles.models import Perfil
from apps.profiles.permisos import rol_de
from apps.seguridad.forms import LockAwareAuthenticationMixin
from apps.seguridad.sessions import pop_closure_message
from apps.tenancy.user_limit import UserLimit
from apps.tenancy.user_limit.messages import OVER_LIMIT_LOGIN

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

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        tenant = getattr(self.request, "tenant", None)
        if tenant is None or tenant.schema_name == get_public_schema_name():
            return
        if not UserLimit(tenant).lets_in(user):
            raise ValidationError(OVER_LIMIT_LOGIN, code="over_limit")

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

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "session_closed": pop_closure_message(self.request)}


class LogoutView(DjangoLogoutView):
    pass


# endregion
"""========================================================================="""
