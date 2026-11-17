from django import forms
from django.contrib.auth import get_user_model

from apps.common.forms import NationalIdentifierForm
from apps.common.utils.utils import CommonCleaner
from apps.profiles.models import Perfil
from apps.profiles.profile.rules import ProfileRules

User = get_user_model()

PERSONAL_FIELDS = ("first_name", "last_name", "email")
EMAIL_REQUIRED = "El correo es obligatorio: es con lo que inicias sesión."


class PersonalDataForm(NationalIdentifierForm, forms.ModelForm):
    national_id_required = True
    national_id_holder = "otra persona de este negocio"

    def __init__(self, *args, **kwargs):
        self.perfil = ProfileRules(kwargs.get("instance")).perfil
        kwargs["initial"] = {
            **self.national_id_initial(self.perfil),
            **kwargs.get("initial", {}),
        }
        super().__init__(*args, **kwargs)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "Correo electrónico",
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
        }

    def national_id_queryset(self):
        return Perfil.objects.exclude(user=self.instance)

    def clean_email(self):
        correo = (self.cleaned_data.get("email") or "").strip().lower()
        if not correo:
            raise forms.ValidationError(EMAIL_REQUIRED)
        result = CommonCleaner.check_email_available(
            User.objects.exclude(pk=self.instance.pk), self.national_id_holder, correo
        )
        if result.is_err():
            raise forms.ValidationError(result.err_value)
        return correo

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit and self.perfil:
            self.save_national_id(self.perfil)
        return user
