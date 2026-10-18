from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseFormSet, BaseInlineFormSet, inlineformset_factory

from apps.common.form_classes import FORM_SELECT_CLASS
from apps.common.form_fields import AlphabeticField, AlphanumericField, NumericField
from apps.common.widgets import switch_input, text_input

"""========================================================================="""
# region ........ Constants


DEFAULT_COUNTRY = "CL"
ADDRESS_COUNTRIES = [
    ("CL", "Chile"),
    ("AR", "Argentina"),
    ("CO", "Colombia"),
    ("EC", "Ecuador"),
    ("MX", "México"),
    ("PE", "Perú"),
    ("DO", "República Dominicana"),
    ("UY", "Uruguay"),
    ("VE", "Venezuela"),
]
INVALID_CLASS = "is-invalid"
OPTIONAL_FORM_OPTIONS = {"empty_permitted": True, "use_required_attribute": False}
MAIN_ITEM_FIELD = "es_principal"


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Functions


def mark_invalid_fields(*forms_to_mark):
    for form in forms_to_mark:
        if isinstance(form, BaseFormSet):
            mark_invalid_fields(*form.forms)
            continue
        for name in form.errors:
            if name not in form.fields:
                continue
            widget = form.fields[name].widget
            classes = widget.attrs.get("class", "").split()
            if INVALID_CLASS not in classes:
                widget.attrs["class"] = " ".join([*classes, INVALID_CLASS])


def main_item_formset(parent_model, form, formset):
    return inlineformset_factory(
        parent_model,
        form._meta.model,
        form=form,
        formset=formset,
        fields=[*form._meta.fields, MAIN_ITEM_FIELD],
        labels={MAIN_ITEM_FIELD: "Principal"},
        widgets={MAIN_ITEM_FIELD: switch_input()},
        extra=0,
        can_delete=True,
    )


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class AddressForm(forms.ModelForm):
    calle = AlphabeticField(
        label="Calle",
        max_length=150,
        allow_dots=True,
        error_messages={"required": "Escribe la calle para guardar la dirección."},
        widget=text_input("Av. Providencia"),
    )
    numero = NumericField(
        label="Número", max_length=15, required=False, widget=text_input("1234")
    )
    complemento = AlphanumericField(
        label="Depto, oficina o local",
        max_length=60,
        required=False,
        allow_dots=True,
        widget=text_input("Depto. 502"),
    )
    codigo_postal = NumericField(
        label="Código postal",
        max_length=12,
        required=False,
        widget=text_input("7500000"),
    )
    comuna = AlphabeticField(
        label="Comuna", max_length=80, required=False, widget=text_input("Providencia")
    )
    ciudad = AlphabeticField(
        label="Ciudad", max_length=80, required=False, widget=text_input("Santiago")
    )
    region = AlphabeticField(
        label="Región",
        max_length=80,
        required=False,
        widget=text_input("Metropolitana"),
    )
    pais = forms.ChoiceField(
        label="País",
        choices=ADDRESS_COUNTRIES,
        initial=DEFAULT_COUNTRY,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    referencia = AlphanumericField(
        label="Referencia",
        max_length=150,
        required=False,
        widget=text_input("Frente a la plaza"),
    )

    class Meta:
        fields = [
            "calle",
            "numero",
            "complemento",
            "codigo_postal",
            "comuna",
            "ciudad",
            "region",
            "pais",
            "referencia",
        ]


class MainItemFormSet(BaseInlineFormSet):
    item_name = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = self.queryset.order_by(f"-{MAIN_ITEM_FIELD}", "pk")

    def kept_forms(self):
        return [
            form
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
        ]

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        kept = self.kept_forms()
        main = [form for form in kept if form.cleaned_data.get(MAIN_ITEM_FIELD)]
        if len(main) > 1:
            raise ValidationError(f"Solo puede haber {self.item_name} principal.")
        if kept and not main:
            raise ValidationError(f"Marca {self.item_name} como principal.")


# endregion
"""========================================================================="""
