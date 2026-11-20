from bootstrap_modal_forms.forms import BSModalForm
from django import forms

from apps.clients.models import Cliente
from apps.common.form_classes import FORM_CONTROL_CLASS, FORM_SELECT_CLASS
from apps.common.form_fields import NoteField
from apps.common.forms import NationalIdentifierForm, SplitNamesForm
from apps.common.utils.countries.constants import CountryPhonePrefix
from apps.common.utils.utils import CommonCleaner


class ClientsForm(NationalIdentifierForm, SplitNamesForm, BSModalForm):
    national_id_holder = "otro cliente"

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)

    def other_clients(self):
        clients = Cliente.objects.all()
        return clients.exclude(pk=self.instance.pk) if self.instance else clients

    def national_id_queryset(self):
        return self.other_clients()

    country_phone_prefix = forms.ChoiceField(
        label="Prefijo País",
        choices=CountryPhonePrefix.choices,
        initial=CountryPhonePrefix.CHILE,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    phone = forms.CharField(
        label="Teléfono",
        required=False,
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "9 1234 5678",
            },
        ),
    )
    email = forms.EmailField(
        label="Correo electrónico",
        max_length=100,
        required=False,
        widget=forms.EmailInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "cliente@ejemplo.com",
            },
        ),
    )
    status = forms.BooleanField(
        label="Estado",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    notes = NoteField(
        label="Notas",
        required=False,
        help_text="Notas del cliente",
        widget=forms.Textarea(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "Cliente alergico a...",
                "rows": 3,
            }
        ),
    )

    def clean_phone(self):
        phone_prefix = self.cleaned_data.get("country_phone_prefix", "").strip()
        phone = self.cleaned_data.get("phone", "").strip()
        if not phone:
            return ""
        result = CommonCleaner.clean_phone_field(phone_prefix, phone)
        if result.is_err():
            raise forms.ValidationError(result.value)
        available = CommonCleaner.check_phone_available(
            self.other_clients(), self.national_id_holder, telefono=result.value
        )
        if available.is_err():
            raise forms.ValidationError(available.err_value)
        return result.value

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            return ""
        result = CommonCleaner.check_email_available(
            self.other_clients(), self.national_id_holder, email
        )
        if result.is_err():
            raise forms.ValidationError(result.err_value)
        return email

    def clean_status(self):
        status = self.cleaned_data.get("status")
        if not status:
            return Cliente.EstadoChoices.INACTIVO
        return Cliente.EstadoChoices.ACTIVO

    def clean(self):
        cleaned_data = super().clean()
        return {
            **self.normaliza_data(cleaned_data),
            "nombre": self.full_names(),
            "apellido": self.full_surnames(),
            **self.national_id_data(),
        }

    @staticmethod
    def normaliza_data(data: dict) -> dict:
        """
        Normalizes form data before saving to the database.
        """
        normalized_data = {}
        fields = [
            ("phone", "telefono"),
            ("email", "email"),
            ("status", "estado"),
            ("notes", "notas"),
        ]
        for form_field, model_field in fields:
            value = data.get(form_field)
            if not value and form_field != "status":
                continue
            normalized_data[model_field] = value
        return normalized_data
