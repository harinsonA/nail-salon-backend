from django import forms
from django.db.models import Count, Exists, F, OuterRef, Q, Subquery, Value
from django.db.models.functions import Concat, Trim
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView
from django_tenants.utils import get_public_schema_name

from apps.common.form_classes import FORM_SELECT_CLASS
from apps.panel.views.base import PanelListViewAjax, PanelView
from apps.tenancy.models import Dominio, Negocio, Rubro

"""========================================================================="""
# region ........ Constants


EMPTY = "—"
ALL = "all"


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Helpers


def businesses():
    return Negocio.objects.exclude(schema_name=get_public_schema_name())


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class BusinessesFilterForm(forms.Form):
    status = forms.ChoiceField(
        choices=[(ALL, "Todos"), *Negocio.Estado.choices],
        label="Estado",
        initial=ALL,
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    industry = forms.ModelChoiceField(
        queryset=Rubro.objects.all(),
        label="Rubro",
        empty_label="Todos",
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )

    def clean(self):
        cleaned_data = super().clean()
        filters = {}
        if cleaned_data.get("status") not in (None, "", ALL):
            filters["estado"] = cleaned_data["status"]
        if cleaned_data.get("industry"):
            filters["rubro"] = cleaned_data["industry"]
        return filters


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class BusinessListView(PanelView, TemplateView):
    template_name = "panel/businesses/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_add = self.request.user.is_superuser and self.model_admin.has_add_permission(self.request)
        context.update(
            {
                "filter_form": BusinessesFilterForm(),
                "list_url": reverse("admin:tenancy_negocio_list_ajax", current_app=self.admin_site.name),
                "add_url": reverse("admin:tenancy_negocio_alta", current_app=self.admin_site.name) if can_add else "",
            }
        )
        return context


class BusinessListAjaxView(PanelListViewAjax):
    model = Negocio
    filter_form_class = BusinessesFilterForm
    field_list = ["pk", "nombre", "domain", "estado", "owner_name", "industry_name", "created"]
    ordering_fields = {
        "0": "nombre",
        "1": "domain",
        "2": "estado",
        "3": "owner_name",
        "4": "industry_name",
        "5": "created",
    }

    def get_queryset(self):
        primary_domain = Dominio.objects.filter(tenant=OuterRef("pk"), is_primary=True).values("domain")[:1]
        return (
            businesses()
            .annotate(
                domain=Subquery(primary_domain),
                owner_name=Trim(Concat("titular__nombres", Value(" "), "titular__apellidos")),
                industry_name=F("rubro__nombre"),
            )
            .filter(**self.get_filters())
        )

    def get_filter_by_search(self):
        search_value = self.request.GET.get("search[value]", "")
        if not search_value:
            return Q()
        domains = Dominio.objects.filter(tenant=OuterRef("pk"), domain__icontains=search_value)
        return (
            Q(nombre__icontains=search_value)
            | Q(schema_name__icontains=search_value)
            | Q(titular__nombres__icontains=search_value)
            | Q(titular__apellidos__icontains=search_value)
            | Q(Exists(domains))
        )

    def get_values(self, queryset):
        labels = dict(Negocio.Estado.choices)
        values = super().get_values(queryset)
        for value in values:
            value["status_label"] = labels.get(value["estado"], value["estado"])
            value["domain"] = value["domain"] or EMPTY
            value["industry_name"] = value["industry_name"] or EMPTY
            value["created"] = timezone.localtime(value["created"]).strftime("%d/%m/%Y")
        return values

    def add_options_column(self, data):
        can_change = self.model_admin.has_change_permission(self.request)
        is_superuser = self.request.user.is_superuser
        for item in data:
            options = []
            if can_change:
                options.append(
                    {
                        "label": "Editar",
                        "link": reverse("admin:tenancy_negocio_change", args=[item["pk"]]),
                        "icon": "edit_document",
                    }
                )
            if is_superuser:
                if item["estado"] == Negocio.Estado.PREPARANDO:
                    options.append(
                        {"label": "Reparar alta", "link": reverse("admin:tenancy_negocio_reparar", args=[item["pk"]])}
                    )
                else:
                    options.append(
                        {
                            "label": "Restablecer clave del propietario",
                            "link": reverse("admin:tenancy_negocio_clave_propietario", args=[item["pk"]]),
                        }
                    )
                options.append(
                    {"label": "Cambiar estado", "link": reverse("admin:tenancy_negocio_estado", args=[item["pk"]])}
                )
            item["options"] = options
        return data

    @staticmethod
    def additional_data(queryset):
        return businesses().aggregate(
            total_businesses=Count("pk"),
            active_businesses=Count("pk", filter=Q(estado=Negocio.Estado.ACTIVO)),
            overdue_businesses=Count("pk", filter=Q(estado=Negocio.Estado.MOROSO)),
            preparing_businesses=Count("pk", filter=Q(estado=Negocio.Estado.PREPARANDO)),
        )


# endregion
"""========================================================================="""
