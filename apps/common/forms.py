import json

from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseFormSet, BaseInlineFormSet, inlineformset_factory

from apps.common.form_classes import FORM_SELECT_CLASS
from apps.common.form_fields import AlphabeticField, AlphanumericField, NumericField
from apps.common.utils.countries.constants import Country
from apps.common.utils.countries.dispatcher import CountryDispatcher
from apps.common.utils.text import join_name_parts, split_name
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
NAME_PART_MAX_LENGTH = 50
FULL_NAME_MAX_LENGTH = 100
NATIONAL_ID_MAX_LENGTH = 20
NATIONAL_ID_COUNTRY_MISSING = "Elige el país del identificador nacional."
NATIONAL_ID_TYPE_MISSING = "Elige el tipo de identificador nacional."
NATIONAL_ID_NUMBER_MISSING = "Escribe el identificador nacional del tipo elegido."
NATIONAL_ID_MISSING_MESSAGES = {
    "national_id_country": NATIONAL_ID_COUNTRY_MISSING,
    "national_id_type": NATIONAL_ID_TYPE_MISSING,
    "national_id": NATIONAL_ID_NUMBER_MISSING,
}
NATIONAL_ID_FIELDS = tuple(NATIONAL_ID_MISSING_MESSAGES)


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


def national_id_types_by_country():
    return {
        country: CountryDispatcher.identifier_types(country)
        for country in Country.values
    }


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


class SplitNamesForm(forms.Form):
    first_name = AlphabeticField(
        label="Primer nombre", max_length=NAME_PART_MAX_LENGTH, widget=text_input("Ana")
    )
    second_name = AlphabeticField(
        label="Segundo nombre",
        max_length=NAME_PART_MAX_LENGTH,
        required=False,
        widget=text_input("María"),
    )
    first_surname = AlphabeticField(
        label="Primer apellido",
        max_length=NAME_PART_MAX_LENGTH,
        required=False,
        widget=text_input("Rojas"),
    )
    second_surname = AlphabeticField(
        label="Segundo apellido",
        max_length=NAME_PART_MAX_LENGTH,
        required=False,
        widget=text_input("Pérez"),
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("second_surname") and not cleaned_data.get("first_surname"):
            self.add_error(
                "first_surname", "Escribe el primer apellido antes del segundo."
            )
        if len(self.full_names()) > FULL_NAME_MAX_LENGTH:
            self.add_error(
                "second_name",
                f"Los nombres juntos no deben superar {FULL_NAME_MAX_LENGTH} caracteres.",
            )
        if len(self.full_surnames()) > FULL_NAME_MAX_LENGTH:
            self.add_error(
                "second_surname",
                f"Los apellidos juntos no deben superar {FULL_NAME_MAX_LENGTH} caracteres.",
            )
        return cleaned_data

    def full_names(self):
        return join_name_parts(
            self.cleaned_data.get("first_name"), self.cleaned_data.get("second_name")
        )

    def full_surnames(self):
        return join_name_parts(
            self.cleaned_data.get("first_surname"),
            self.cleaned_data.get("second_surname"),
        )

    @staticmethod
    def split_names_initial(names, surnames):
        first_name, second_name = split_name(names)
        first_surname, second_surname = split_name(surnames)
        return {
            "first_name": first_name,
            "second_name": second_name,
            "first_surname": first_surname,
            "second_surname": second_surname,
        }


class NationalIdentifierForm(forms.Form):
    national_id_required = False

    national_id_country = forms.ChoiceField(
        label="País",
        required=False,
        choices=[("", "Selecciona un país"), *Country.choices],
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    national_id_type = forms.ChoiceField(
        label="Tipo de identificador nacional",
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    national_id = forms.CharField(
        label="Identificador nacional",
        max_length=NATIONAL_ID_MAX_LENGTH,
        required=False,
        widget=text_input("12.345.678-5"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.national_id_required:
            for name, message in NATIONAL_ID_MISSING_MESSAGES.items():
                self.fields[name].required = True
                self.fields[name].error_messages["required"] = message
        country_field = self.fields["national_id_country"]
        country_field.widget.attrs.update(
            {
                "data-national-id-types": json.dumps(national_id_types_by_country()),
                "data-national-id-type-field": f"#{self['national_id_type'].auto_id}",
            }
        )
        country = (
            self.data.get(self.add_prefix("national_id_country"))
            if self.is_bound
            else self.initial.get("national_id_country")
        )
        types = (
            CountryDispatcher.identifier_types(country)
            if country in Country.values
            else []
        )
        type_field = self.fields["national_id_type"]
        type_field.choices = [("", "Selecciona un tipo"), *types]
        if not types:
            type_field.widget.attrs["disabled"] = True

    def clean(self):
        cleaned_data = super().clean()
        country = cleaned_data.get("national_id_country")
        identifier_type = cleaned_data.get("national_id_type")
        number = cleaned_data.get("national_id")
        if not (identifier_type or number or "national_id_type" in self.errors):
            return cleaned_data
        if not country and "national_id_country" not in self.errors:
            self.add_error("national_id_country", NATIONAL_ID_COUNTRY_MISSING)
        if not identifier_type and "national_id_type" not in self.errors:
            self.add_error("national_id_type", NATIONAL_ID_TYPE_MISSING)
        if not number and "national_id" not in self.errors:
            self.add_error("national_id", NATIONAL_ID_NUMBER_MISSING)
        if country and identifier_type and number:
            result = CountryDispatcher.validate_identifier(
                country, identifier_type, number
            )
            if result.is_err():
                self.add_error("national_id", result.err_value)
            else:
                cleaned_data["national_id"] = result.ok_value
        return cleaned_data

    @property
    def national_id_optional(self):
        return not self.national_id_required

    @staticmethod
    def national_id_initial(holder):
        if holder is None:
            return {}
        return {
            "national_id_country": holder.pais or "",
            "national_id_type": holder.tipo_identificador_nacional or "",
            "national_id": holder.identificador_nacional or "",
        }

    def save_national_id(self, holder, **other_fields):
        changes = {**self.national_id_data(), **other_fields}
        if holder.pk and all(
            getattr(holder, field) == value for field, value in changes.items()
        ):
            return holder
        for field, value in changes.items():
            setattr(holder, field, value)
        holder.save()
        return holder

    def national_id_data(self):
        return {
            "pais": self.cleaned_data.get("national_id_country") or None,
            "tipo_identificador_nacional": self.cleaned_data.get("national_id_type")
            or None,
            "identificador_nacional": self.cleaned_data.get("national_id") or None,
        }


class MainItemFormSet(BaseInlineFormSet):
    item_name = ""
    requires_one = False

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
        if self.requires_one and not kept:
            raise ValidationError(f"Debe tener al menos {self.item_name}.")
        main = [form for form in kept if form.cleaned_data.get(MAIN_ITEM_FIELD)]
        if len(main) > 1:
            raise ValidationError(f"Solo puede haber {self.item_name} principal.")
        if kept and not main:
            raise ValidationError(f"Marca {self.item_name} como principal.")


# endregion
"""========================================================================="""
