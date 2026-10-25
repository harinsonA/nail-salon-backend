from bootstrap_modal_forms.forms import BSModalForm
from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q, Subquery, TextChoices, Value
from django.db.models.functions import Concat, Trim
from django.urls import reverse
from django.views.generic import TemplateView

from apps.common.form_classes import FORM_CONTROL_CLASS, FORM_SELECT_CLASS
from apps.common.form_fields import NoteField, NumericField
from apps.common.forms import (
    OPTIONAL_FORM_OPTIONS,
    AddressForm,
    MainItemFormSet,
    NationalIdentifierForm,
    SplitNamesForm,
    main_item_formset,
)
from apps.common.utils.countries.constants import CountryPhonePrefix
from apps.common.utils.search import contains_ignoring_accents, search_ignoring_accents
from apps.common.widgets import switch_input, text_input
from apps.panel.views.base import (
    PanelCreateModalView,
    PanelDeleteModalView,
    PanelListViewAjax,
    PanelUpdateModalView,
    PanelView,
    RelatedFormsMixin,
)
from apps.tenancy.models import (
    Persona,
    PersonaCorreo,
    PersonaDireccion,
    PersonaTelefono,
)
from apps.tenancy.propietario import sync_owner_data

"""========================================================================="""
# region ........ Constants


EMPTY = "—"
PHONE_MAX_DIGITS = 15
ACCESS_EMAIL_LABEL = "acceso"


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class PeopleFilterForm(forms.Form):
    class OwnershipChoices(TextChoices):
        ALL = "all", "Todos"
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


class PersonNamesForm(NationalIdentifierForm, SplitNamesForm, BSModalForm):
    national_id_required = True

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

    def person_data(self):
        return {
            "nombres": self.full_names(),
            "apellidos": self.full_surnames(),
            "notas": self.cleaned_data["notes"] or None,
            **self.national_id_data(),
        }


class PersonCreateForm(PersonNamesForm):
    def save(self):
        person = Persona(**self.person_data())
        person._change_reason = "Alta desde el panel"
        person.save()
        return person


class PersonUpdateForm(PersonNamesForm):
    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        kwargs["initial"] = {
            **self.split_names_initial(instance.nombres, instance.apellidos),
            **self.national_id_initial(instance),
            "notes": instance.notas or "",
            **kwargs.get("initial", {}),
        }
        super().__init__(*args, **kwargs)

    def save(self):
        for field, value in self.person_data().items():
            setattr(self.instance, field, value)
        self.instance._change_reason = "Edición desde el panel"
        self.instance.save()
        return self.instance


class PersonEmailForm(forms.ModelForm):
    correo = forms.EmailField(
        label="Correo",
        max_length=254,
        error_messages={"required": "Escribe el correo del propietario."},
        widget=forms.EmailInput(
            attrs={"class": FORM_CONTROL_CLASS, "placeholder": "ana.rojas@ejemplo.com"}
        ),
    )

    class Meta:
        model = PersonaCorreo
        fields = ["correo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_locked():
            self.fields["correo"].disabled = True
            self.fields[
                "correo"
            ].help_text = "Es el correo de acceso de su negocio: no se cambia ni se quita desde aquí."

    def is_locked(self):
        return bool(self.instance.pk) and self.instance.etiqueta == ACCESS_EMAIL_LABEL

    def clean_correo(self):
        return self.cleaned_data["correo"].strip().lower()


class PersonPhoneForm(forms.ModelForm):
    non_field_errors_target = "numero"

    codigo_pais = forms.ChoiceField(
        label="Prefijo país",
        choices=CountryPhonePrefix.choices,
        initial=CountryPhonePrefix.CHILE,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    numero = NumericField(
        label="Teléfono", max_length=PHONE_MAX_DIGITS, widget=text_input("912345678")
    )
    tipo = forms.ChoiceField(
        label="Tipo de teléfono",
        choices=PersonaTelefono.Tipo.choices,
        initial=PersonaTelefono.Tipo.MOVIL,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    tiene_whatsapp = forms.BooleanField(
        label="Tiene WhatsApp", required=False, widget=switch_input()
    )

    class Meta:
        model = PersonaTelefono
        fields = ["codigo_pais", "numero", "tipo", "tiene_whatsapp"]


class PersonAddressForm(AddressForm):
    class Meta(AddressForm.Meta):
        model = PersonaDireccion


class PersonEmailFormSet(MainItemFormSet):
    item_name = "un correo"
    requires_one = True

    def clean(self):
        if any(
            form.cleaned_data.get("DELETE") and form.is_locked() for form in self.forms
        ):
            raise ValidationError(
                "El correo de acceso de su negocio no se puede quitar."
            )
        super().clean()


class PersonPhoneFormSet(MainItemFormSet):
    item_name = "un teléfono"


class PersonAddressFormSet(MainItemFormSet):
    item_name = "una dirección"


EmailFormSet = main_item_formset(Persona, PersonEmailForm, PersonEmailFormSet)
PhoneFormSet = main_item_formset(Persona, PersonPhoneForm, PersonPhoneFormSet)
AddressFormSet = main_item_formset(Persona, PersonAddressForm, PersonAddressFormSet)


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
            contains_ignoring_accents("correo", search_value), persona=OuterRef("pk")
        )
        phones = PersonaTelefono.objects.filter(
            contains_ignoring_accents("numero", search_value), persona=OuterRef("pk")
        )
        return (
            search_ignoring_accents(["nombres", "apellidos"], search_value)
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
                            "admin:tenancy_persona_change_modal", args=[item["pk"]]
                        ),
                        "bsModal": True,
                        "icon": "edit_document",
                        "className": "bs-xl-modal",
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


class PersonCreateModalView(RelatedFormsMixin, PanelCreateModalView):
    template_name = "panel/people/person_modal.html"
    form_class = PersonCreateForm
    success_message = "Propietario %(name)s creado exitosamente."

    def get_related_forms(self, data):
        return {
            "email_form": PersonEmailForm(data, prefix="email"),
            "phone_form": PersonPhoneForm(
                data, prefix="phone", **OPTIONAL_FORM_OPTIONS
            ),
            "address_form": PersonAddressForm(
                data, prefix="address", **OPTIONAL_FORM_OPTIONS
            ),
        }

    @transaction.atomic
    def create_object(self, form):
        person = form.save()
        for contact_form in self.related_forms().values():
            if contact_form.has_changed():
                contact = contact_form.save(commit=False)
                contact.persona = person
                contact.es_principal = True
                contact.save()
        return person


class PersonUpdateModalView(RelatedFormsMixin, PanelUpdateModalView):
    template_name = "panel/people/person_edit_modal.html"
    form_class = PersonUpdateForm
    success_message = "Propietario %(name)s actualizado exitosamente."
    section_labels = {
        "emails": "Correos",
        "phones": "Teléfonos",
        "addresses": "Direcciones",
    }

    def get_related_forms(self, data):
        person = self.get_object()
        return {
            "emails": EmailFormSet(data, instance=person, prefix="correos"),
            "phones": PhoneFormSet(data, instance=person, prefix="telefonos"),
            "addresses": AddressFormSet(data, instance=person, prefix="direcciones"),
        }

    def get_changed_fields(self, form):
        sections = [
            self.section_labels[name]
            for name, formset in self.related_forms().items()
            if formset.has_changed()
        ]
        return super().get_changed_fields(form) + sections

    @transaction.atomic
    def update_object(self, form):
        person = form.save()
        for formset in self.related_forms().values():
            formset.save()
        sync_owner_data(person)
        return person


class PersonDeleteModalView(PanelDeleteModalView):
    success_message = "Propietario %(name)s eliminado exitosamente."
    in_use_message = "No se puede eliminar a «%(name)s»: es titular de un negocio. Primero cambia el titular."

    def is_blocked(self, person):
        return person.negocios_como_titular.exists()

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
