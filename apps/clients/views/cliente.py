from django import forms
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.db.models import Value, TextChoices
from django.db.models.functions import Concat
from rest_framework.status import HTTP_400_BAD_REQUEST
from bootstrap_modal_forms.forms import BSModalForm
from bootstrap_modal_forms.generic import BSModalFormView, BSModalDeleteView
from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.utils.utils import CommonCleaner, get_errors_to_response
from apps.common.utils.phones import CountryPhonePrefix
from ..models.cliente import Cliente

"""========================================================================="""
# region ........ Constants

FORM_CONTROL_CLASS = "form-control form-control--custom"
FORM_SELECT_CLASS = "form-select form-select--custom"

# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Form


class ClientsFilterForm(BSModalForm):
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


class ClientsForm(BSModalForm):
    name = forms.CharField(
        label="Nombres",
        max_length=50,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "Jose Jose",
            },
        ),
    )
    last_name = forms.CharField(
        label="Apellidos",
        required=False,
        max_length=50,
        widget=forms.TextInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "Garcia Vazquez",
            },
        ),
    )
    country_phone_prefix = forms.ChoiceField(
        label="Prefijo País",
        choices=CountryPhonePrefix.choices,
        initial=CountryPhonePrefix.CHILE,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    phone = forms.CharField(
        label="Teléfono",
        required=False,
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "9 1234 5678",
            },
        ),
    )
    email = forms.EmailField(
        label="Correo electrónico",
        max_length=100,
        required=False,
        widget=forms.EmailInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "cliente@ejemplo.com",
            },
        ),
    )
    status = forms.BooleanField(
        label="Estado",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    notes = forms.CharField(
        label="Notas",
        required=False,
        help_text="Notas del cliente",
        widget=forms.Textarea(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "Cliente alergico a...",
                "rows": 3,
            }
        ),
    )

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Este campo es obligatorio.")
        result = CommonCleaner.clean_alphabetic_field("nombres", name)
        if result.is_err():
            raise forms.ValidationError(result.value)
        return name

    def clean_last_name(self):
        last_name = self.cleaned_data.get("last_name", "").strip()
        if not last_name:
            return last_name
        result = CommonCleaner.clean_alphabetic_field("apellidos", last_name)
        if result.is_err():
            raise forms.ValidationError(result.value)
        return last_name

    def clean_phone(self):
        phone_prefix = self.cleaned_data.get("country_phone_prefix", "").strip()
        phone = self.cleaned_data.get("phone", "").strip()
        if not phone:
            return ""
        result = CommonCleaner.clean_phone_field(phone_prefix, phone)
        if result.is_err():
            raise forms.ValidationError(result.value)
        return result.value

    def clean_notes(self):
        notes = self.cleaned_data.get("notes", "")
        if not notes:
            return ""
        result = CommonCleaner.clean_250_characters_field("notas", notes)
        if result.is_err():
            raise forms.ValidationError(result.value)
        return result.value

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
            ("last_name", "apellido"),
            ("phone", "telefono"),
            ("email", "email"),
            ("status", "activo"),
            ("notes", "notas"),
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


class ClientsView(TemplateView):
    template_name = "clients/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "filter_form": ClientsFilterForm(),
                "url_client_list": reverse_lazy("client_list"),
            }
        )
        return context


class ClientListView(BaseListViewAjax):
    model = Cliente
    filter_form_class = ClientsFilterForm

    field_list = [
        "pk",
        "nombre",
        "apellido",
        "telefono",
        "email",
        "activo",
        "full_name",
    ]

    ordering_fields = {
        "0": "full_name",
        "1": "activo",
        "2": "telefono",
        "3": "email",
    }

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(full_name=Concat("nombre", Value(" "), "apellido"))
        )

    @staticmethod
    def add_options_column(data: list) -> list:
        for item in data:
            item["options"] = [
                {
                    "label": "Ver detalles",
                    "link": reverse_lazy(
                        "client_detail_modal", kwargs={"pk": item["pk"]}
                    ),
                    "bsModal": True,
                    "icon": "edit_document",
                    "className": "bs-modal",
                },
                {
                    "label": "Eliminar",
                    "link": reverse_lazy(
                        "client_delete_modal", kwargs={"pk": item["pk"]}
                    ),
                    "bsModal": True,
                    "icon": "delete",
                    "className": "bs-modal text-color-destructive",
                },
            ]
        return data


class BaseClientModalView(BSModalFormView):
    template_name = "clients/client_modal.html"
    form_class = ClientsForm
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


class ClientCreateModalView(BaseClientModalView):
    modal_url = "client_create_modal"
    success_message = "Cliente %(client_full_name)s creado exitosamente."

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        client_new = Cliente.objects.create(**cleaned_data)
        full_name = client_new.nombre_completo
        return JsonResponse(
            {"message": self.success_message % {"client_full_name": full_name}}
        )


class ClientDetailModalView(BaseClientModalView):
    modal_url = "client_detail_modal"
    pk_url_kwarg = "pk"
    success_message = "Cliente %(client_full_name)s actualizado exitosamente."
    base_object = None

    def get_object(self, queryset=None):
        client_id = self.kwargs.get(self.pk_url_kwarg)
        return Cliente.objects.filter(pk=client_id).first()

    @staticmethod
    def get_phone_and_prefix(client: Cliente) -> tuple:
        if not client.telefono:
            return "", ""
        prefixes = dict(CountryPhonePrefix.choices)
        phone_without_prefix = ""
        prefix = ""
        for _prefix in prefixes:
            if not client.telefono.startswith(_prefix):
                continue
            phone_without_prefix = client.telefono[len(_prefix) :]
            prefix = _prefix
            break
        return prefix, phone_without_prefix

    def get_initial(self):
        self.base_object = self.get_object()
        prefix, phone = self.get_phone_and_prefix(self.base_object)
        initial = {
            "name": self.base_object.nombre,
            "last_name": self.base_object.apellido,
            "country_phone_prefix": prefix,
            "phone": phone,
            "email": self.base_object.email,
            "status": self.base_object.activo,
            "notes": self.base_object.notas,
        }
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["client_full_name"] = self.base_object.nombre_completo
        return context

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        client = self.get_object()
        for field, value in cleaned_data.items():
            setattr(client, field, value)
        client.save(update_fields=cleaned_data.keys())
        full_name = client.nombre_completo
        return JsonResponse(
            {"message": self.success_message % {"client_full_name": full_name}}
        )


class ClientDeleteModalView(BSModalDeleteView):
    template_name = "common/delete_modal.html"
    success_message = "Cliente %(client_full_name)s eliminado exitosamente."

    def get_object(self, queryset=None):
        client_id = self.kwargs.get("pk")
        return Cliente.objects.filter(pk=client_id).first()

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        kwargs.update(
            {
                "view": self,
                "object": self.object,
                "id_register": self.object.pk,
                "name_register": self.object.nombre_completo,
                "aditional_information": self.get_aditional_information(self.object),
            }
        )
        context_object_name = self.get_context_object_name(self.object)
        if context_object_name:
            kwargs[context_object_name] = self.object
        return kwargs

    @staticmethod
    def get_aditional_information(client: Cliente) -> list:
        fields = ["telefono", "email", "fecha_registro"]
        icons = {
            "telefono": "mobile",
            "email": "mail",
            "fecha_registro": "calendar_today",
        }
        additional_info = []
        for field in fields:
            value = getattr(client, field)
            if not value:
                continue
            text = (
                value
                if field != "fecha_registro"
                else f"Registrado: {value.strftime('%d de %B de %Y')}"
            )
            additional_info.append(
                {
                    "text": text,
                    "icon": icons.get(field, "info"),
                }
            )
        return additional_info

    def post(self, request, *args, **kwargs):
        client = self.get_object()
        client_full_name = client.nombre_completo
        client.delete()
        return JsonResponse(
            {"message": self.success_message % {"client_full_name": client_full_name}},
        )


# endregion
"""========================================================================="""
