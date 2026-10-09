from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.shortcuts import redirect
from django.views.generic import FormView

from apps.common.views.base_views import ProtectedView
from apps.profiles.models import Perfil


class CambiarClaveView(ProtectedView, FormView):
    template_name = "login/cambiar_clave.html"
    form_class = SetPasswordForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        usuario = form.save()
        Perfil.objects.update_or_create(user=usuario, defaults={"debe_cambiar_clave": False})
        update_session_auth_hash(self.request, usuario)
        messages.success(self.request, "Tu clave quedó guardada.")
        return redirect("calendar")
