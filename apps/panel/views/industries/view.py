from django import forms
from django.db.models import Count, Q, TextChoices
from django.urls import reverse
from django.views.generic import TemplateView

from apps.common.form_classes import FORM_SELECT_CLASS
from apps.panel.views.base import PanelDeleteModalView, PanelListViewAjax, PanelView
from apps.tenancy.models import Rubro

"""========================================================================="""
# region ........ Forms


class IndustriesFilterForm(forms.Form):
    class StatusChoices(TextChoices):
        ALL = "all", "Todos"
        ACTIVE = "active", "Activos"
        INACTIVE = "inactive", "Inactivos"

    status = forms.ChoiceField(
        choices=StatusChoices.choices,
        label="Estado",
        initial=StatusChoices.ALL,
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )

    def clean(self):
        status = super().clean().get("status")
        if status == self.StatusChoices.ACTIVE:
            return {"activo": True}
        if status == self.StatusChoices.INACTIVE:
            return {"activo": False}
        return {}


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class IndustryListView(PanelView, TemplateView):
    template_name = "panel/industries/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_add = self.model_admin.has_add_permission(self.request)
        context.update(
            {
                "filter_form": IndustriesFilterForm(),
                "list_url": reverse("admin:tenancy_rubro_list_ajax", current_app=self.admin_site.name),
                "add_url": reverse("admin:tenancy_rubro_add", current_app=self.admin_site.name) if can_add else "",
            }
        )
        return context


class IndustryListAjaxView(PanelListViewAjax):
    model = Rubro
    filter_form_class = IndustriesFilterForm
    field_list = ["pk", "nombre", "codigo", "activo", "orden", "business_count"]
    ordering_fields = {
        "0": "nombre",
        "1": "codigo",
        "2": "activo",
        "3": "orden",
        "4": "business_count",
    }

    def get_queryset(self):
        return Rubro.objects.annotate(business_count=Count("negocios", distinct=True)).filter(**self.get_filters())

    def get_filter_by_search(self):
        search_value = self.request.GET.get("search[value]", "")
        if not search_value:
            return Q()
        return Q(nombre__icontains=search_value) | Q(codigo__icontains=search_value)

    def add_options_column(self, data):
        can_change = self.model_admin.has_change_permission(self.request)
        can_delete = self.model_admin.has_delete_permission(self.request)
        for item in data:
            options = []
            if can_change:
                options.append(
                    {
                        "label": "Editar",
                        "link": reverse("admin:tenancy_rubro_change", args=[item["pk"]]),
                        "icon": "edit_document",
                    }
                )
            if can_delete:
                options.append(
                    {
                        "label": "Eliminar",
                        "link": reverse("admin:tenancy_rubro_delete_modal", args=[item["pk"]]),
                        "bsModal": True,
                        "icon": "delete",
                        "className": "bs-modal text-color-destructive",
                    }
                )
            item["options"] = options
        return data

    @staticmethod
    def additional_data(queryset):
        return Rubro.objects.aggregate(
            total_industries=Count("pk"),
            active_industries=Count("pk", filter=Q(activo=True)),
        )


class IndustryDeleteModalView(PanelDeleteModalView):
    success_message = "Rubro %(name)s eliminado exitosamente."
    blocked_message = "No se puede eliminar el rubro «%(name)s»: tiene negocios asociados."

    def get_additional_information(self, industry):
        return [
            {"text": f"Código: {industry.codigo}", "icon": "tag"},
            {"text": f"Negocios asociados: {industry.negocios.count()}", "icon": "storefront"},
        ]


# endregion
"""========================================================================="""
