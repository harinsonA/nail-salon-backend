from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.views import View
from django.views.generic import FormView, TemplateView

from apps.common.claves import generar_clave_temporal
from apps.common.views.base_views import ProtectedView
from apps.profiles.models import Perfil
from apps.profiles.permisos import puede_gestionar, roles_que_puede_crear

User = get_user_model()

"""========================================================================="""
# region ........ Forms


class MiembroForm(forms.Form):
    first_name = forms.CharField(label="Nombre", max_length=150)
    last_name = forms.CharField(label="Apellido", max_length=150, required=False)
    email = forms.EmailField(label="Correo", help_text="Con este correo entra a la agenda.")
    rol = forms.ChoiceField(label="Rol")

    def __init__(self, roles, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rol"].choices = [(rol.value, rol.label) for rol in roles]
        for campo in self.fields.values():
            campo.widget.attrs["class"] = "form-select" if campo is self.fields["rol"] else "form-control"

    def clean_email(self):
        correo = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=correo).exists():
            raise forms.ValidationError("Ese correo ya lo usa otra persona de este negocio.")
        return correo


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Views


def respuesta_con_clave(request, usuario, clave, titulo):
    respuesta = TemplateResponse(
        request,
        "equipo/clave.html",
        {"titulo": titulo, "miembro": usuario, "clave": clave},
    )
    respuesta["Cache-Control"] = "no-store"
    return respuesta


def asignar_clave_temporal(usuario):
    clave = generar_clave_temporal()
    usuario.set_password(clave)
    usuario.save()
    Perfil.objects.filter(user=usuario).update(debe_cambiar_clave=True)
    return clave


class EquipoView(ProtectedView, TemplateView):
    template_name = "equipo/lista.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.request.user
        miembros = User.objects.select_related("perfil").order_by("-is_active", "first_name", "email")
        context["miembros"] = [(miembro, puede_gestionar(usuario, miembro)) for miembro in miembros]
        context["puede_crear"] = bool(roles_que_puede_crear(usuario))
        return context


class CrearMiembroView(ProtectedView, FormView):
    template_name = "equipo/crear.html"

    def get_form(self, form_class=None):
        return MiembroForm(roles_que_puede_crear(self.request.user), **self.get_form_kwargs())

    def form_valid(self, form):
        datos = form.cleaned_data
        usuario = User.objects.create_user(
            username=datos["email"][:150],
            email=datos["email"],
            first_name=datos["first_name"],
            last_name=datos["last_name"],
        )
        Perfil.objects.filter(user=usuario).update(rol=datos["rol"])
        clave = asignar_clave_temporal(usuario)
        return respuesta_con_clave(self.request, usuario, clave, "Usuario creado")


class MiembroGestionadoMixin:
    def obtener_miembro(self, pk):
        miembro = get_object_or_404(User.objects.select_related("perfil"), pk=pk)
        if not puede_gestionar(self.request.user, miembro):
            raise PermissionDenied
        return miembro


class CambiarActivoView(ProtectedView, MiembroGestionadoMixin, View):
    def post(self, request, pk):
        miembro = self.obtener_miembro(pk)
        miembro.is_active = not miembro.is_active
        miembro.save(update_fields=["is_active"])
        accion = "reactivado" if miembro.is_active else "desactivado"
        messages.success(request, f"{miembro.get_full_name() or miembro.email} quedó {accion}.")
        return redirect("equipo")


class RestablecerClaveView(ProtectedView, MiembroGestionadoMixin, View):
    def post(self, request, pk):
        miembro = self.obtener_miembro(pk)
        clave = asignar_clave_temporal(miembro)
        return respuesta_con_clave(request, miembro, clave, "Clave restablecida")


# endregion
"""========================================================================="""
