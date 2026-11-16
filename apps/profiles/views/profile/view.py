from bootstrap_modal_forms.forms import BSModalModelForm
from bootstrap_modal_forms.generic import BSModalUpdateView
from django import forms
from django.contrib.auth import update_session_auth_hash
from django.http import JsonResponse
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.common.forms import NATIONAL_ID_FIELDS
from apps.common.middleware import start_session_window
from apps.common.utils.utils import get_errors_to_response
from apps.common.views.base_views import ProtectedView
from apps.profiles.password import PasswordChange
from apps.profiles.profile import PERSONAL_FIELDS, PersonalDataForm, ProfileRules
from apps.settings.preferences import SESSION_IDLE_MINUTES, Category
from apps.settings.preferences.forms import PreferenceFieldsMixin

"""========================================================================="""
# region ........ Forms


class ProfileForm(PersonalDataForm, PreferenceFieldsMixin, BSModalModelForm):
    preference_category = Category.SEGURIDAD

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_preference_fields(self.instance)
        self.personal_data_locked = ProfileRules(self.instance).personal_data_locked
        if self.personal_data_locked:
            for name in PERSONAL_FIELDS:
                self.fields[name].disabled = True
            for name in NATIONAL_ID_FIELDS:
                del self.fields[name]

    def clean(self):
        cleaned_data = super().clean()
        errors = PasswordChange(self.instance).voluntary_errors(
            cleaned_data.get("current_password"),
            cleaned_data.get("new_password"),
            cleaned_data.get("confirm_password"),
        )
        for field, messages in errors.items():
            for message in messages:
                self.add_error(field, message)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_pw = self.cleaned_data.get("new_password")
        if new_pw:
            user.set_password(new_pw)
        if commit:
            user.save()
            if self.perfil and not self.personal_data_locked:
                self.save_national_id(self.perfil)
        return user


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Views


class ProfileModalView(ProtectedView, BSModalUpdateView):
    template_name = "profiles/index.html"
    form_class = ProfileForm
    success_message = ProfileRules.SAVED_MESSAGE

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rules = ProfileRules(self.request.user)
        context["profile_full_name"] = rules.full_name
        context["profile_initials"] = rules.initials
        return context

    def form_valid(self, form):
        user = form.save()
        form.save_preferences(user)
        if form.cleaned_data.get("new_password"):
            update_session_auth_hash(self.request, user)
        start_session_window(self.request.session, SESSION_IDLE_MINUTES.get(user) * 60)
        return JsonResponse({"message": self.success_message})

    def form_invalid(self, form):
        errors = get_errors_to_response(form.errors)
        return JsonResponse({"errors": errors}, status=HTTP_400_BAD_REQUEST)


# endregion
"""========================================================================="""
