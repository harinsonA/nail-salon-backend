from django import forms
from django.db.models import Count, Exists, OuterRef, Q, Subquery, TextChoices, Value
from django.db.models.functions import Concat, Trim
from django.urls import reverse
from django.views.generic import TemplateView

from apps.common.form_classes import FORM_SELECT_CLASS
from apps.panel.views.base import PanelDeleteModalView, PanelListViewAjax, PanelView
from apps.tenancy.models import Persona, PersonaCorreo, PersonaTelefono

EMPTY = "—"


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


class PersonListView(PanelView, TemplateView):
    template_name = "panel/people/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_add = self.model_admin.has_add_permission(self.request)
        context.update(
            {
                "filter_form": PeopleFilterForm(),
                "list_url": reverse("admin:tenancy_persona_list_ajax", current_app=self.admin_site.name),
                "add_url": reverse("admin:tenancy_persona_add", current_app=self.admin_site.name) if can_add else "",
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
        main_email = PersonaCorreo.objects.filter(persona=OuterRef("pk"), es_principal=True).values("correo")[:1]
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
        emails = PersonaCorreo.objects.filter(persona=OuterRef("pk"), correo__icontains=search_value)
        phones = PersonaTelefono.objects.filter(persona=OuterRef("pk"), numero__icontains=search_value)
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
                        "link": reverse("admin:tenancy_persona_change", args=[item["pk"]]),
                        "icon": "edit_document",
                    }
                )
            if can_delete:
                options.append(
                    {
                        "label": "Eliminar",
                        "link": reverse("admin:tenancy_persona_delete_modal", args=[item["pk"]]),
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
            business_owners=Count("pk", filter=Q(negocios_como_titular__isnull=False), distinct=True),
        )


class PersonDeleteModalView(PanelDeleteModalView):
    success_message = "Persona %(name)s eliminada exitosamente."
    blocked_message = "No se puede eliminar a «%(name)s»: es titular de un negocio. Primero cambia el titular."

    def get_additional_information(self, person):
        return [
            {"text": f"Correos: {person.correos.count()}", "icon": "mail"},
            {"text": f"Teléfonos: {person.telefonos.count()}", "icon": "call"},
            {"text": f"Negocios como titular: {person.negocios_como_titular.count()}", "icon": "storefront"},
        ]
