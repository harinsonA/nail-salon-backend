from bootstrap_modal_forms.forms import BSModalForm
from bootstrap_modal_forms.generic import BSModalDeleteView, BSModalFormView
from django import forms
from django.db.models import Count, Q, TextChoices
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.exports.columns import ExcelColumn
from apps.common.exports.excel_export_mixin import ExcelExportMixin
from apps.common.form_classes import FORM_SELECT_CLASS
from apps.common.utils.utils import get_errors_to_response
from apps.common.views.base_views import ProtectedView

from ...editing import CategoriesForm, CategoryEditor, CategoryInitial
from ...models.categoria import Categoria

"""========================================================================="""
# region ........ Form


class CategoriesFilterForm(BSModalForm):
    class StatusChoices(TextChoices):
        ALL = "all", "Todos"
        ACTIVE = "activo", "Activos"
        INACTIVE = "inactivo", "Inactivos"

    status = forms.ChoiceField(
        choices=StatusChoices.choices,
        label="Estado",
        initial=StatusChoices.ACTIVE,
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )

    def clean(self):
        cleaned_data = super().clean()
        is_data_valid = all(cleaned_data.values())
        if not is_data_valid:
            return {}

        data_to_filter = {}
        status = cleaned_data.get("status", Categoria.EstadoChoices.ACTIVO)
        if status == self.StatusChoices.ALL:
            return data_to_filter
        data_to_filter["estado"] = status
        return data_to_filter


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class CategoriesView(ProtectedView, TemplateView):
    template_name = "categories/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "filter_form": CategoriesFilterForm(),
                "url_category_list": reverse_lazy("category_list"),
                "url_category_export": reverse_lazy("category_export"),
                "url_service_list": reverse_lazy("services"),
            }
        )
        return context


class CategoryListView(BaseListViewAjax):
    model = Categoria
    filter_form_class = CategoriesFilterForm

    field_list = [
        "pk",
        "nombre",
        "descripcion",
        "estado",
    ]

    ordering_fields = {
        "0": "pk",
        "1": "nombre",
        "2": "estado",
        "3": "descripcion",
    }

    @staticmethod
    def add_options_column(data: list) -> list:
        for item in data:
            item["options"] = [
                {
                    "label": "Ver detalles",
                    "link": reverse_lazy(
                        "category_detail_modal", kwargs={"pk": item["pk"]}
                    ),
                    "bsModal": True,
                    "icon": "edit_document",
                    "className": "bs-modal",
                },
                {
                    "label": "Eliminar",
                    "link": reverse_lazy(
                        "category_delete_modal", kwargs={"pk": item["pk"]}
                    ),
                    "bsModal": True,
                    "icon": "delete",
                    "className": "bs-modal text-color-destructive",
                },
            ]
        return data

    def get_values(self, queryset):
        values = super().get_values(queryset)
        for item in values:
            item.update(
                {
                    "status": item.get("estado") == Categoria.EstadoChoices.ACTIVO,
                }
            )
        return values

    @staticmethod
    def additional_data(queryset) -> dict:
        return Categoria.objects.aggregate(
            active_categories_total=Count(
                "pk", filter=Q(estado=Categoria.EstadoChoices.ACTIVO)
            ),
            inactive_categories_total=Count(
                "pk", filter=Q(estado=Categoria.EstadoChoices.INACTIVO)
            ),
        )


class CategoryExportView(ExcelExportMixin, CategoryListView):
    force_export = True
    include_options_column = False
    excel_filename = "categorias"
    excel_sheet_title = "Categorias"

    excel_columns = [
        ExcelColumn("ID", "pk", width=10, align="center"),
        ExcelColumn("Nombre", "nombre", width=30),
        ExcelColumn(
            "Estado",
            "estado",
            width=14,
            align="center",
            formatter=lambda value: (
                "Activo" if value == Categoria.EstadoChoices.ACTIVO else "Inactivo"
            ),
        ),
        ExcelColumn("Descripcion", "descripcion", width=50),
    ]


class BaseCategoryModalView(ProtectedView, BSModalFormView):
    template_name = "categories/category_modal.html"
    form_class = CategoriesForm
    modal_url = None
    pk_url_kwarg = None

    def get_modal_url(self):
        if not self.modal_url:
            return "#"
        argument = self.kwargs.get(self.pk_url_kwarg)
        if argument:
            return reverse_lazy(self.modal_url, kwargs={self.pk_url_kwarg: argument})
        return reverse_lazy(self.modal_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["modal_url"] = self.get_modal_url()
        return context

    def form_invalid(self, form):
        errors = get_errors_to_response(form.errors)
        return JsonResponse({"errors": errors}, status=HTTP_400_BAD_REQUEST)


class CategoryCreateModalView(BaseCategoryModalView):
    modal_url = "category_create_modal"

    def form_valid(self, form):
        category = CategoryEditor.create(form)
        return JsonResponse({"message": CategoryEditor.created_message(category)})


class CategoryDetailModalView(BaseCategoryModalView):
    modal_url = "category_detail_modal"
    pk_url_kwarg = "pk"
    base_object = None

    def get_object(self, queryset=None):
        category_id = self.kwargs.get(self.pk_url_kwarg)
        return Categoria.objects.filter(pk=category_id).first()

    def get_initial(self):
        self.base_object = self.get_object()
        return CategoryInitial.of(self.base_object)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category_name"] = self.base_object.nombre
        return context

    def form_valid(self, form):
        category = CategoryEditor.update(self.get_object(), form)
        return JsonResponse({"message": CategoryEditor.updated_message(category)})


class CategoryDeleteModalView(ProtectedView, BSModalDeleteView):
    template_name = "common/delete_modal.html"
    success_message = "Categoria %(category_name)s eliminada exitosamente."
    blocked_message = (
        "No se puede eliminar la categoria porque tiene "
        "%(services_count)s servicio(s) asociado(s)."
    )

    def get_object(self, queryset=None):
        category_id = self.kwargs.get("pk")
        return Categoria.objects.filter(pk=category_id).first()

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        kwargs.update(
            {
                "view": self,
                "object": self.object,
                "id_register": self.object.pk,
                "name_register": self.object.nombre,
                "aditional_information": self.get_aditional_information(self.object),
            }
        )
        context_object_name = self.get_context_object_name(self.object)
        if context_object_name:
            kwargs[context_object_name] = self.object
        return kwargs

    @staticmethod
    def get_aditional_information(category: Categoria) -> list:
        fields = ["services_count", "created"]
        icons = {
            "services_count": "linked_services",
            "created": "calendar_today",
        }
        additional_info = []
        services_count = category.servicios.filter(is_removed=False).count()
        values = {
            "services_count": services_count,
            "created": category.created,
        }
        for field in fields:
            value = values.get(field)
            if value is None:
                continue
            if field == "services_count":
                text = f"Servicios asociados: {value}"
            elif field == "created":
                text = f"Registrado: {value.strftime('%d de %B de %Y')}"
            else:
                text = str(value)
            additional_info.append(
                {
                    "text": text,
                    "icon": icons.get(field, "info"),
                }
            )
        return additional_info

    def post(self, request, *args, **kwargs):
        category = self.get_object()
        services_count = category.servicios.filter(is_removed=False).count()
        if services_count > 0:
            return JsonResponse(
                {"message": self.blocked_message % {"services_count": services_count}},
                status=HTTP_400_BAD_REQUEST,
            )

        category_name = category.nombre
        category.delete()
        return JsonResponse(
            {"message": self.success_message % {"category_name": category_name}},
        )


# endregion
"""========================================================================="""
