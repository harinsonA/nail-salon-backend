import re

from bootstrap_modal_forms.forms import BSModalForm
from django import forms
from django.db.models import Count, Q, TextChoices
from django.urls import reverse
from django.views.generic import TemplateView

from apps.common.form_classes import FORM_CONTROL_CLASS, FORM_SELECT_CLASS
from apps.common.form_fields import AlphabeticField
from apps.panel.views.base import (
    PanelCreateModalView,
    PanelDeleteModalView,
    PanelListViewAjax,
    PanelUpdateModalView,
    PanelView,
)
from apps.tenancy.models import Rubro

"""========================================================================="""
# region ........ Constants


NAME_MAX_LENGTH = 80
CODE_MIN_LENGTH = 3
CODE_MAX_LENGTH = 30
CODE_PATTERN = re.compile(r"^[a-z]+(_[a-z]+)*$")


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class IndustryForm(BSModalForm):
    nombre = AlphabeticField(
        label="Nombre",
        widget=forms.TextInput(
            attrs={"class": FORM_CONTROL_CLASS, "placeholder": "Barbería", "maxlength": NAME_MAX_LENGTH}
        ),
    )
    codigo = forms.CharField(
        label="Código",
        help_text="Entre 3 y 30 caracteres: minúsculas sin tilde, separadas con guion bajo (peluqueria_canina).",
        widget=forms.TextInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "barberia",
                "maxlength": CODE_MAX_LENGTH,
                "autocapitalize": "none",
                "autocomplete": "off",
                "spellcheck": "false",
            }
        ),
    )
    activo = forms.BooleanField(
        label="Activo",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "role": "switch"}),
    )

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)
        if instance is not None:
            self.initial.update({"nombre": instance.nombre, "codigo": instance.codigo, "activo": instance.activo})

    def other_industries(self):
        return Rubro.objects.exclude(pk=self.instance.pk) if self.instance else Rubro.objects.all()

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"]
        if len(nombre) > NAME_MAX_LENGTH:
            raise forms.ValidationError(f"El nombre no debe superar {NAME_MAX_LENGTH} caracteres.")
        if self.other_industries().filter(nombre__iexact=nombre).exists():
            raise forms.ValidationError("Ya existe un rubro con ese nombre.")
        return nombre

    def clean_codigo(self):
        codigo = self.cleaned_data["codigo"].strip()
        if any(character.isupper() for character in codigo):
            raise forms.ValidationError("El código debe ir en minúsculas.")
        if not CODE_MIN_LENGTH <= len(codigo) <= CODE_MAX_LENGTH:
            raise forms.ValidationError(f"El código debe tener entre {CODE_MIN_LENGTH} y {CODE_MAX_LENGTH} caracteres.")
        if not CODE_PATTERN.match(codigo):
            raise forms.ValidationError(
                "El código solo admite letras minúsculas sin tilde, separadas con un guion bajo "
                "(por ejemplo, peluqueria_canina)."
            )
        if self.other_industries().filter(codigo__iexact=codigo).exists():
            raise forms.ValidationError("Ya existe un rubro con ese código.")
        return codigo

    def save(self):
        industry = self.instance or Rubro()
        industry.nombre = self.cleaned_data["nombre"]
        industry.codigo = self.cleaned_data["codigo"]
        industry.activo = self.cleaned_data["activo"]
        industry.save()
        return industry


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
# region ........ Mixins


class IndustryModalMixin:
    template_name = "panel/industries/industry_modal.html"
    form_class = IndustryForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        industry = context.get("object")
        context["business_count"] = industry.negocios.count() if industry else 0
        return context


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
                "create_modal_url": (
                    reverse("admin:tenancy_rubro_add_modal", current_app=self.admin_site.name) if can_add else ""
                ),
            }
        )
        return context


class IndustryListAjaxView(PanelListViewAjax):
    model = Rubro
    filter_form_class = IndustriesFilterForm
    field_list = ["pk", "nombre", "codigo", "activo", "business_count"]
    ordering_fields = {
        "0": "nombre",
        "1": "codigo",
        "2": "activo",
        "3": "business_count",
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
                        "link": reverse("admin:tenancy_rubro_change_modal", args=[item["pk"]]),
                        "bsModal": True,
                        "icon": "edit_document",
                        "className": "bs-modal",
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


class IndustryCreateModalView(IndustryModalMixin, PanelCreateModalView):
    success_message = "Rubro %(name)s creado exitosamente."

    def create_object(self, form):
        return form.save()


class IndustryUpdateModalView(IndustryModalMixin, PanelUpdateModalView):
    success_message = "Rubro %(name)s actualizado exitosamente."

    def update_object(self, form):
        return form.save()


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
