from bootstrap_modal_forms.forms import BSModalForm
from django import forms

from apps.common.custom_time_fields import DurationInMinutesField
from apps.common.form_classes import FORM_CONTROL_CLASS, FORM_SELECT_CLASS
from apps.common.form_fields import AlphabeticField, MoneyField, NoteField
from apps.common.utils.utils import CommonCleaner
from apps.common.widgets import MoneyInput
from apps.services.models import Categoria, Servicio


class ServicesForm(BSModalForm):
    category = forms.ModelChoiceField(
        label="Categoria",
        required=True,
        queryset=Categoria.objects.filter(is_removed=False),
        widget=forms.Select(
            attrs={
                "class": FORM_SELECT_CLASS,
            },
        ),
        empty_label="Selecciona una categoria",
    )
    name = AlphabeticField(
        label="Nombre del Servicio",
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "Manicure Clásica",
            },
        ),
    )
    description = NoteField(
        label="Descripción",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "Descripción del servicio...",
                "rows": 3,
            },
        ),
    )
    price = MoneyField(
        label="Precio",
        initial=0,
        max_value=99_999_999,
        required=False,
        widget=MoneyInput(attrs={"placeholder": "15.000"}),
    )
    duration = DurationInMinutesField(
        label="Duración (minutos)",
        required=True,
        initial=30,
        widget=forms.NumberInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "60",
                "min": "1",
            },
        ),
    )
    status = forms.BooleanField(
        label="Estado",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def clean_category(self):
        category = self.cleaned_data.get("category")
        if not category:
            raise forms.ValidationError("Debes seleccionar una categoria.")
        return category

    def clean_price(self):
        result = CommonCleaner.clean_amount_field("precio", self.cleaned_data.get("price"))
        if result.is_err():
            raise forms.ValidationError(result.err_value)
        return result.ok_value

    def clean_duration(self):
        duration = self.cleaned_data.get("duration")
        if not int(duration.total_seconds()):
            raise forms.ValidationError("La duración debe ser mayor a cero.")
        return duration

    def clean_status(self):
        status = self.cleaned_data.get("status")
        if not status:
            return Servicio.EstadoChoices.INACTIVO
        return Servicio.EstadoChoices.ACTIVO

    def clean(self):
        cleaned_data = super().clean()
        return self.normaliza_data(cleaned_data)

    @staticmethod
    def normaliza_data(data: dict) -> dict:
        normalized_data = {}
        fields = [
            ("category", "categoria"),
            ("name", "nombre"),
            ("description", "descripcion"),
            ("price", "precio"),
            ("duration", "duracion_estimada"),
            ("status", "estado"),
        ]
        for form_field, model_field in fields:
            value = data.get(form_field)
            if not value and form_field not in ("status", "price"):
                continue
            normalized_data[model_field] = value
        return normalized_data
