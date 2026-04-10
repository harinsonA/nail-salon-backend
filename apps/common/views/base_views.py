from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse


class ProtectedView(LoginRequiredMixin):
    pass


class ProtectedAjaxView(LoginRequiredMixin):
    error_message_unauthorized = "Usuario no autorizado"
    error_message_authentication_failed = (
        "Deber iniciar sesión para acceder a esta información"
    )

    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return JsonResponse(
                {
                    "message": self.error_message_authentication_failed
                    if not hasattr(request, "user")
                    else self.error_message_unauthorized
                },
                status=401,
            )
        return super().dispatch(request, *args, **kwargs)
