from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import LogoutView as DjangoLogoutView


"""========================================================================="""
# region ........ Views


class LoginView(DjangoLoginView):
    template_name = "login/index.html"


class LogoutView(DjangoLogoutView):
    pass


# endregion
"""========================================================================="""
