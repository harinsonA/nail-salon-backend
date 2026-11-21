from bootstrap_modal_forms.forms import BSModalForm
from django import forms

from apps.common.form_classes import FORM_CONTROL_CLASS
from apps.common.form_fields import AlphabeticField, NoteField
from apps.services.models import Categoria


class CategoriesForm(BSModalForm):
    name = AlphabeticField(
        label="Nombre de la categoria",
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "Manicure",
            },
        ),
    )
    description = NoteField(
        label="Descripcion",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "Descripcion de la categoria...",
                "rows": 3,
            },
        ),
    )
    status = forms.BooleanField(
        label="Estado",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def clean_status(self):
        status = self.cleaned_data.get("status")
        if not status:
            return Categoria.EstadoChoices.INACTIVO
        return Categoria.EstadoChoices.ACTIVO

    def clean(self):
        cleaned_data = super().clean()
        return self.normalize_data(cleaned_data)

    @staticmethod
    def normalize_data(data: dict) -> dict:
        normalized_data = {}
        fields = [
            ("name", "nombre"),
            ("description", "descripcion"),
            ("status", "estado"),
        ]
        for form_field, model_field in fields:
            value = data.get(form_field)
            if not value and form_field != "status":
                continue
            normalized_data[model_field] = value
        return normalized_data
