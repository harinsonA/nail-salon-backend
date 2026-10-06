from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import LogoutView as DjangoLogoutView

"""========================================================================="""
# region ........ Forms


class CorreoAuthenticationForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Correo o contraseña incorrectos.",
        "inactive": "Esta cuenta está desactivada.",
    }

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
