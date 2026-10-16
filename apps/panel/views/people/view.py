from bootstrap_modal_forms.forms import BSModalForm
from django import forms
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q, Subquery, TextChoices, Value
from django.db.models.functions import Concat, Trim
from django.urls import reverse
from django.views.generic import TemplateView

from apps.common.form_classes import FORM_CONTROL_CLASS, FORM_SELECT_CLASS
from apps.common.form_fields import (
    AlphabeticField,
    AlphanumericField,
    NoteField,
    NumericField,
)
from apps.common.utils.phones import CountryPhonePrefix
from apps.common.utils.text import join_name_parts
from apps.common.utils.utils import CommonCleaner
from apps.common.widgets import switch_input, text_input
from apps.panel.views.base import (
    PanelCreateModalView,
    PanelDeleteModalView,
    PanelListViewAjax,
    PanelView,
)
from apps.tenancy.models import (
    Persona,
    PersonaCorreo,
    PersonaDireccion,
    PersonaTelefono,
)

"""========================================================================="""
# region ........ Constants


EMPTY = "—"
NAME_PART_MAX_LENGTH = 50
FULL_NAME_MAX_LENGTH = 100
PHONE_MAX_DIGITS = 15
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
ADDRESS_FIELDS = (
    "street",
    "number",
    "complement",
    "commune",
    "city",
    "region",
    "postal_code",
    "reference",
)


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class PeopleFilterForm(forms.Form):
    class OwnershipChoices(TextChoices):
        ALL = "all", "Todas"
        OWNERS = "owners", "Titulares de algún negocio"
        WITHOUT_BUSINESS = "without_business", "Sin negocio"

    ownership = forms.ChoiceField(
        choices=OwnershipChoices.choices,
        label="Titularidad",
        initial=OwnershipChoices.ALL,
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )

    def clean(self):
        ownership = super().clean().get("ownership")
        if ownership == self.OwnershipChoices.OWNERS:
            return {"business_count__gt": 0}
        if ownership == self.OwnershipChoices.WITHOUT_BUSINESS:
            return {"business_count": 0}
        return {}


class PersonCreateForm(BSModalForm):
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
    email = forms.EmailField(
        label="Correo",
        max_length=254,
        required=False,
        widget=forms.EmailInput(
            attrs={"class": FORM_CONTROL_CLASS, "placeholder": "ana.rojas@ejemplo.com"}
        ),
    )
    country_phone_prefix = forms.ChoiceField(
        label="Prefijo país",
        choices=CountryPhonePrefix.choices,
        initial=CountryPhonePrefix.CHILE,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    phone = NumericField(
        label="Teléfono",
        max_length=PHONE_MAX_DIGITS,
        required=False,
        widget=text_input("912345678"),
    )
    phone_type = forms.ChoiceField(
        label="Tipo de teléfono",
        choices=PersonaTelefono.Tipo.choices,
        initial=PersonaTelefono.Tipo.MOVIL,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    has_whatsapp = forms.BooleanField(
        label="Tiene WhatsApp", required=False, widget=switch_input()
    )
    notes = NoteField(
        label="Nota",
        required=False,
        help_text="Hasta 250 caracteres.",
        widget=forms.Textarea(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "Prefiere que la contacten por WhatsApp.",
                "rows": 3,
            }
        ),
    )
    street = AlphabeticField(
        label="Calle",
        max_length=150,
        required=False,
        allow_dots=True,
        widget=text_input("Av. Providencia"),
    )
    number = NumericField(
        label="Número", max_length=15, required=False, widget=text_input("1234")
    )
    complement = AlphanumericField(
        label="Depto, oficina o local",
        max_length=60,
        required=False,
        allow_dots=True,
        widget=text_input("Depto. 502"),
    )
    postal_code = NumericField(
        label="Código postal",
        max_length=12,
        required=False,
        widget=text_input("7500000"),
    )
    commune = AlphabeticField(
        label="Comuna", max_length=80, required=False, widget=text_input("Providencia")
    )
    city = AlphabeticField(
        label="Ciudad", max_length=80, required=False, widget=text_input("Santiago")
    )
    region = AlphabeticField(
        label="Región",
        max_length=80,
        required=False,
        widget=text_input("Metropolitana"),
    )
    country = forms.ChoiceField(
        label="País",
        choices=ADDRESS_COUNTRIES,
        initial=DEFAULT_COUNTRY,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    reference = AlphanumericField(
        label="Referencia",
        max_length=150,
        required=False,
        widget=text_input("Frente a la plaza"),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean(self):
        cleaned_data = super().clean()
        self.validate_full_names(cleaned_data)
        self.validate_mobile_phone(cleaned_data)
        self.validate_address(cleaned_data)
        return cleaned_data

    def validate_full_names(self, cleaned_data):
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

    def validate_mobile_phone(self, cleaned_data):
        phone = cleaned_data.get("phone")
        prefix = cleaned_data.get("country_phone_prefix")
        if (
            not phone
            or not prefix
            or cleaned_data.get("phone_type") != PersonaTelefono.Tipo.MOVIL
        ):
            return
        result = CommonCleaner.clean_phone_field(prefix, phone)
        if result.is_err():
            self.add_error("phone", result.value)

    def validate_address(self, cleaned_data):
        has_address = any(cleaned_data.get(field) for field in ADDRESS_FIELDS)
        if has_address and not cleaned_data.get("street"):
            self.add_error("street", "Escribe la calle para guardar la dirección.")

    def full_names(self):
        return join_name_parts(
            self.cleaned_data.get("first_name"), self.cleaned_data.get("second_name")
        )

    def full_surnames(self):
        return join_name_parts(
            self.cleaned_data.get("first_surname"),
            self.cleaned_data.get("second_surname"),
        )

    def save(self):
        data = self.cleaned_data
        with transaction.atomic():
            person = Persona(
                nombres=self.full_names(),
                apellidos=self.full_surnames(),
                notas=data["notes"] or None,
            )
            person._change_reason = "Alta desde el panel"
            person.save()
            if data["email"]:
                PersonaCorreo.objects.create(
                    persona=person, correo=data["email"], es_principal=True
                )
            if data["phone"]:
                PersonaTelefono.objects.create(
                    persona=person,
                    codigo_pais=data["country_phone_prefix"],
                    numero=data["phone"],
                    tipo=data["phone_type"],
                    tiene_whatsapp=data["has_whatsapp"],
                    es_principal=True,
                )
            if data["street"]:
                PersonaDireccion.objects.create(
                    persona=person,
                    calle=data["street"],
                    numero=data["number"],
                    complemento=data["complement"],
                    comuna=data["commune"],
                    ciudad=data["city"],
                    region=data["region"],
                    pais=data["country"],
                    codigo_postal=data["postal_code"],
                    referencia=data["reference"],
                    es_principal=True,
                )
        return person


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class PersonListView(PanelView, TemplateView):
    template_name = "panel/people/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_add = self.model_admin.has_add_permission(self.request)
        context.update(
            {
                "filter_form": PeopleFilterForm(),
                "list_url": reverse(
                    "admin:tenancy_persona_list_ajax", current_app=self.admin_site.name
                ),
                "create_modal_url": (
                    reverse(
                        "admin:tenancy_persona_add_modal",
                        current_app=self.admin_site.name,
                    )
                    if can_add
                    else ""
                ),
            }
        )
        return context


class PersonListAjaxView(PanelListViewAjax):
    model = Persona
    filter_form_class = PeopleFilterForm
    field_list = ["pk", "full_name", "main_email", "main_phone", "business_count"]
    ordering_fields = {
        "0": "full_name",
        "1": "main_email",
        "2": "main_phone",
        "3": "business_count",
    }

    def get_queryset(self):
        main_email = PersonaCorreo.objects.filter(
            persona=OuterRef("pk"), es_principal=True
        ).values("correo")[:1]
        main_phone = (
            PersonaTelefono.objects.filter(persona=OuterRef("pk"), es_principal=True)
            .annotate(full_number=Concat("codigo_pais", Value(" "), "numero"))
            .values("full_number")[:1]
        )
        return Persona.objects.annotate(
            full_name=Trim(Concat("nombres", Value(" "), "apellidos")),
            main_email=Subquery(main_email),
            main_phone=Subquery(main_phone),
            business_count=Count("negocios_como_titular", distinct=True),
        ).filter(**self.get_filters())

    def get_filter_by_search(self):
        search_value = self.request.GET.get("search[value]", "")
        if not search_value:
            return Q()
        emails = PersonaCorreo.objects.filter(
            persona=OuterRef("pk"), correo__icontains=search_value
        )
        phones = PersonaTelefono.objects.filter(
            persona=OuterRef("pk"), numero__icontains=search_value
        )
        return (
            Q(nombres__icontains=search_value)
            | Q(apellidos__icontains=search_value)
            | Q(Exists(emails))
            | Q(Exists(phones))
        )

    def get_values(self, queryset):
        values = super().get_values(queryset)
        for value in values:
            value["main_email"] = value["main_email"] or EMPTY
            value["main_phone"] = value["main_phone"] or EMPTY
        return values

    def add_options_column(self, data):
        can_change = self.model_admin.has_change_permission(self.request)
        can_delete = self.model_admin.has_delete_permission(self.request)
        for item in data:
            options = []
            if can_change:
                options.append(
                    {
                        "label": "Editar",
                        "link": reverse(
                            "admin:tenancy_persona_change", args=[item["pk"]]
                        ),
                        "icon": "edit_document",
                    }
                )
            if can_delete:
                options.append(
                    {
                        "label": "Eliminar",
                        "link": reverse(
                            "admin:tenancy_persona_delete_modal", args=[item["pk"]]
                        ),
                        "bsModal": True,
                        "icon": "delete",
                        "className": "bs-modal text-color-destructive",
                    }
                )
            item["options"] = options
        return data

    @staticmethod
    def additional_data(queryset):
        return Persona.objects.aggregate(
            total_people=Count("pk", distinct=True),
            business_owners=Count(
                "pk", filter=Q(negocios_como_titular__isnull=False), distinct=True
            ),
        )


class PersonCreateModalView(PanelCreateModalView):
    template_name = "panel/people/person_modal.html"
    form_class = PersonCreateForm
    success_message = "Persona %(name)s creada exitosamente."

    def create_object(self, form):
        return form.save()


class PersonDeleteModalView(PanelDeleteModalView):
    success_message = "Persona %(name)s eliminada exitosamente."
    blocked_message = "No se puede eliminar a «%(name)s»: es titular de un negocio. Primero cambia el titular."

    def get_additional_information(self, person):
        return [
            {"text": f"Correos: {person.correos.count()}", "icon": "mail"},
            {"text": f"Teléfonos: {person.telefonos.count()}", "icon": "call"},
            {
                "text": f"Negocios como titular: {person.negocios_como_titular.count()}",
                "icon": "storefront",
            },
        ]


# endregion
"""========================================================================="""
