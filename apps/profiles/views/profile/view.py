from django import forms
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.http import JsonResponse
from rest_framework.status import HTTP_400_BAD_REQUEST
from bootstrap_modal_forms.forms import BSModalModelForm
from bootstrap_modal_forms.generic import BSModalUpdateView
from apps.common.utils.utils import get_errors_to_response
from apps.common.views.base_views import ProtectedView

User = get_user_model()

"""========================================================================="""
# region ........ Forms


class ProfileForm(BSModalModelForm):
    current_password = forms.CharField(
        label="Contraseña actual",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Contraseña actual",
                "autocomplete": "off",
            }
        ),
    )
    new_password = forms.CharField(
        label="Nueva contraseña",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Nueva contraseña",
                "autocomplete": "new-password",
            }
        ),
    )
    confirm_password = forms.CharField(
        label="Confirmar contraseña",
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Confirmar contraseña",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "username"]
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "Correo electrónico",
            "username": "Nombre de usuario",
        }
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nombre"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Apellido"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "Correo electrónico"}
            ),
            "username": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nombre de usuario"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        current_pw = cleaned_data.get("current_password")
        new_pw = cleaned_data.get("new_password")
        confirm_pw = cleaned_data.get("confirm_password")

        if new_pw or confirm_pw or current_pw:
            if not current_pw:
                self.add_error(
                    "current_password", "Debes ingresar tu contraseña actual."
                )
            elif not self.instance.check_password(current_pw):
                self.add_error(
                    "current_password", "La contraseña actual es incorrecta."
                )

            if not new_pw:
                self.add_error("new_password", "Debes ingresar la nueva contraseña.")
            if not confirm_pw:
                self.add_error(
                    "confirm_password", "Debes confirmar la nueva contraseña."
                )

            if new_pw and confirm_pw and new_pw != confirm_pw:
                self.add_error("confirm_password", "Las contraseñas no coinciden.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_pw = self.cleaned_data.get("new_password")
        if new_pw:
            user.set_password(new_pw)
        if commit:
            user.save()
        return user


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Views


class ProfileModalView(ProtectedView, BSModalUpdateView):
    template_name = "profiles/index.html"
    form_class = ProfileForm
    success_message = "Perfil actualizado exitosamente."

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["profile_full_name"] = self.get_full_name(self.request.user)
        return context

    @staticmethod
    def get_full_name(user):
        if user.first_name and user.last_name:
            return f"{user.first_name} {user.last_name}"
        return user.username

    def form_valid(self, form):
        user = form.save()
        if form.cleaned_data.get("new_password"):
            update_session_auth_hash(self.request, user)
        return JsonResponse({"message": self.success_message})

    def form_invalid(self, form):
        errors = get_errors_to_response(form.errors)
        return JsonResponse({"errors": errors}, status=HTTP_400_BAD_REQUEST)


# endregion
"""========================================================================="""
