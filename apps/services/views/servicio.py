from django import forms
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.db.models import TextChoices
from rest_framework.status import HTTP_400_BAD_REQUEST
from bootstrap_modal_forms.forms import BSModalForm
from bootstrap_modal_forms.generic import BSModalFormView, BSModalDeleteView
from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.custom_time_fields import DurationInMinutesField
from apps.common.utils.utils import CommonCleaner, get_errors_to_response
from ..models.servicio import Servicio

"""========================================================================="""
# region ........ Constants

FORM_CONTROL_CLASS = "form-control form-control--custom"
FORM_SELECT_CLASS = "form-select form-select--custom"

# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Form


class ServicesFilterForm(BSModalForm):
    class StatusChoices(TextChoices):
        ALL = "all", "Todos"
        ACTIVE = "active", "Activos"
        DEACTIVE = "deactive", "Inactivos"

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
        status = cleaned_data.get("status", "active")
        if status == self.StatusChoices.ALL:
            return data_to_filter
        data_to_filter["activo"] = status == self.StatusChoices.ACTIVE
        return data_to_filter


class ServicesForm(BSModalForm):
    name = forms.CharField(
        label="Nombre del Servicio",
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "Manicure Clásica",
            },
        ),
    )
    description = forms.CharField(
        label="Descripción",
        required=False,
        max_length=500,
        widget=forms.Textarea(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "Descripción del servicio...",
                "rows": 3,
            },
        ),
    )
    price = forms.DecimalField(
        label="Precio",
        max_digits=10,
        decimal_places=2,
        initial=0,
        required=True,
        widget=forms.NumberInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "15000",
                "step": "0.01",
            },
        ),
    )
    duration = DurationInMinutesField(
        label="Duración (minutos)",
        required=True,
        initial=30,
        widget=forms.NumberInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "60",
                "min": "1",
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
        result = CommonCleaner.clean_alphabetic_field("nombre del servicio", name)
        if result.is_err():
            raise forms.ValidationError(result.value)
        return name

    def clean_description(self):
        description = self.cleaned_data.get("description", "").strip()
        if not description:
            return description
        result = CommonCleaner.clean_250_characters_field("descripción", description)
        if result.is_err():
            raise forms.ValidationError(result.value)
        return description

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is not None and price <= 0:
            raise forms.ValidationError("El precio debe ser mayor a cero.")
        return price

    def clean_duration(self):
        duration = self.cleaned_data.get("duration")
        print(
            "\n Duration cleaned:",
            duration,
            type(duration),
            duration.total_seconds(),
            int(duration.total_seconds()),
            "\n",
        )
        if not int(duration.total_seconds()):
            raise forms.ValidationError("La duración debe ser mayor a cero.")
        return duration

    def clean(self):
        cleaned_data = super().clean()
        return self.normaliza_data(cleaned_data)

    @staticmethod
    def normaliza_data(data: dict) -> dict:
        """
        Normalizes form data before saving to the database.
        """
        normalized_data = {}
        fields = [
            ("name", "nombre"),
            ("description", "descripcion"),
            ("price", "precio"),
            ("duration", "duracion_estimada"),
            ("status", "activo"),
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


class ServicesView(TemplateView):
    template_name = "services/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "filter_form": ServicesFilterForm(),
                "url_service_list": reverse_lazy("service_list"),
            }
        )
        return context


class ServiceListView(BaseListViewAjax):
    model = Servicio
    filter_form_class = ServicesFilterForm

    field_list = [
        "pk",
        "nombre",
        "descripcion",
        "precio",
        "duracion_estimada",
        "activo",
    ]

    ordering_fields = {
        "0": "nombre",
        "1": "activo",
        "2": "precio",
        "3": "duracion_estimada",
    }

    @staticmethod
    def add_options_column(data: list) -> list:
        for item in data:
            item["options"] = [
                {
                    "label": "Ver detalles",
                    "link": reverse_lazy(
                        "service_detail_modal", kwargs={"pk": item["pk"]}
                    ),
                    "bsModal": True,
                    "icon": "edit_document",
                    "className": "bs-modal",
                },
                {
                    "label": "Eliminar",
                    "link": reverse_lazy(
                        "service_delete_modal", kwargs={"pk": item["pk"]}
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
                    "estimated_duration_display": self.get_estimated_duration_display(
                        estimated_duration=item.get("duracion_estimada")
                    ),
                    "price_formatted": f"$ {item.get('precio', 0):,.0f}",
                }
            )
        return values

    @staticmethod
    def get_estimated_duration_display(estimated_duration):
        if not estimated_duration:
            return "-- --"
        total_seconds = estimated_duration.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"


class BaseServiceModalView(BSModalFormView):
    template_name = "services/service_modal.html"
    form_class = ServicesForm
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


class ServiceCreateModalView(BaseServiceModalView):
    modal_url = "service_create_modal"
    success_message = "Servicio %(service_name)s creado exitosamente."

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        service_new = Servicio.objects.create(**cleaned_data)
        service_name = service_new.nombre
        return JsonResponse(
            {"message": self.success_message % {"service_name": service_name}}
        )


class ServiceDetailModalView(BaseServiceModalView):
    modal_url = "service_detail_modal"
    pk_url_kwarg = "pk"
    success_message = "Servicio %(service_name)s actualizado exitosamente."
    base_object = None

    def get_object(self, queryset=None):
        service_id = self.kwargs.get(self.pk_url_kwarg)
        return Servicio.objects.filter(pk=service_id).first()

    @staticmethod
    def get_duration_init(duration) -> int:
        if not duration:
            return 0
        return int(duration.total_seconds() // 60)

    def get_initial(self):
        self.base_object = self.get_object()
        initial = {
            "name": self.base_object.nombre,
            "description": self.base_object.descripcion,
            "price": self.base_object.precio,
            "duration": self.get_duration_init(self.base_object.duracion_estimada),
            "status": self.base_object.activo,
        }
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["service_name"] = self.base_object.nombre
        return context

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        service = self.get_object()
        for field, value in cleaned_data.items():
            setattr(service, field, value)
        service.save(update_fields=cleaned_data.keys())
        service_name = service.nombre
        return JsonResponse(
            {"message": self.success_message % {"service_name": service_name}}
        )


class ServiceDeleteModalView(BSModalDeleteView):
    template_name = "common/delete_modal.html"
    success_message = "Servicio %(service_name)s eliminado exitosamente."

    def get_object(self, queryset=None):
        service_id = self.kwargs.get("pk")
        return Servicio.objects.filter(pk=service_id).first()

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
    def get_aditional_information(service: Servicio) -> list:
        fields = ["precio", "duracion_estimada", "fecha_creacion"]
        icons = {
            "precio": "attach_money",
            "duracion_estimada": "schedule",
            "fecha_creacion": "calendar_today",
        }
        additional_info = []
        for field in fields:
            value = getattr(service, field)
            if not value:
                continue
            if field == "precio":
                text = f"Precio: ${value:,.0f}"
            elif field == "duracion_estimada":
                text = f"Duración: {value} minutos"
            elif field == "fecha_creacion":
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
        service = self.get_object()
        service_name = service.nombre
        service.delete()
        return JsonResponse(
            {"message": self.success_message % {"service_name": service_name}},
        )


# endregion
"""========================================================================="""
