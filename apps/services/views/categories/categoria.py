from django import forms
from django.db import transaction
from django.db.models import Count, Q, TextChoices
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from rest_framework.status import HTTP_400_BAD_REQUEST
from bootstrap_modal_forms.forms import BSModalForm
from bootstrap_modal_forms.generic import BSModalDeleteView, BSModalFormView

from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.form_classes import FORM_CONTROL_CLASS, FORM_SELECT_CLASS
from apps.common.utils.utils import CommonCleaner, get_errors_to_response
from apps.common.views.base_views import ProtectedView
from ...models.servicio import Servicio
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


class CategoriesForm(BSModalForm):
    name = forms.CharField(
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
    description = forms.CharField(
        label="Descripcion",
        required=False,
        max_length=500,
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

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Este campo es obligatorio.")
        result = CommonCleaner.clean_alphabetic_field("nombre de la categoria", name)
        if result.is_err():
            raise forms.ValidationError(result.value)
        return name

    def clean_description(self):
        description = self.cleaned_data.get("description", "").strip()
        if not description:
            return description
        result = CommonCleaner.clean_250_characters_field("descripcion", description)
        if result.is_err():
            raise forms.ValidationError(result.value)
        return description

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
        "0": "nombre",
        "1": "estado",
        "2": "descripcion",
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
    success_message = "Categoria %(category_name)s creada exitosamente."

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        category_new = Categoria.objects.create(**cleaned_data)
        category_name = category_new.nombre
        return JsonResponse(
            {"message": self.success_message % {"category_name": category_name}}
        )


class CategoryDetailModalView(BaseCategoryModalView):
    modal_url = "category_detail_modal"
    pk_url_kwarg = "pk"
    success_message = "Categoria %(category_name)s actualizada exitosamente."
    base_object = None

    def get_object(self, queryset=None):
        category_id = self.kwargs.get(self.pk_url_kwarg)
        return Categoria.objects.filter(pk=category_id).first()

    def get_initial(self):
        self.base_object = self.get_object()
        return {
            "name": self.base_object.nombre,
            "description": self.base_object.descripcion,
            "status": self.base_object.estado == Categoria.EstadoChoices.ACTIVO,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["category_name"] = self.base_object.nombre
        return context

    @staticmethod
    def set_services_to_inactive_when_category_is_inactivated(
        category: Categoria,
        previous_status: str,
        new_status: str,
    ):
        is_transition_to_inactive = (
            previous_status == Categoria.EstadoChoices.ACTIVO
            and new_status == Categoria.EstadoChoices.INACTIVO
        )
        if not is_transition_to_inactive:
            return

        category.servicios.filter(is_removed=False).exclude(
            estado=Servicio.EstadoChoices.INACTIVO
        ).update(estado=Servicio.EstadoChoices.INACTIVO)

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        category = self.get_object()
        previous_status = category.estado
        new_status = cleaned_data.get("estado", previous_status)

        with transaction.atomic():
            for field, value in cleaned_data.items():
                setattr(category, field, value)
            category.save(update_fields=cleaned_data.keys())
            self.set_services_to_inactive_when_category_is_inactivated(
                category=category,
                previous_status=previous_status,
                new_status=new_status,
            )

        category_name = category.nombre
        return JsonResponse(
            {"message": self.success_message % {"category_name": category_name}}
        )


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
