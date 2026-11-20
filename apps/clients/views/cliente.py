from bootstrap_modal_forms.forms import BSModalForm
from bootstrap_modal_forms.generic import (
    BSModalDeleteView,
    BSModalFormView,
    BSModalReadView,
)
from django import forms
from django.db.models import Count, Q, TextChoices, Value
from django.db.models.functions import Concat
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.exports.columns import ExcelColumn
from apps.common.exports.excel_export_mixin import ExcelExportMixin
from apps.common.form_classes import FORM_CONTROL_TEXTAREA_CLASS, FORM_SELECT_CLASS
from apps.common.utils.utils import get_errors_to_response
from apps.common.utils.whatsapp import get_whatsapp_url
from apps.common.views.base_views import ProtectedView

from ..editing import ClientEditor, ClientInitial, ClientsForm
from ..models.cliente import Cliente

"""========================================================================="""
# region ........ Form


class ClientsFilterForm(BSModalForm):
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
        status = cleaned_data.get("status", "activo")
        if status == self.StatusChoices.ALL:
            return data_to_filter
        data_to_filter["estado"] = status
        return data_to_filter


class ClientWhatsappForm(forms.Form):
    message = forms.CharField(
        label="Mensaje",
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": FORM_CONTROL_TEXTAREA_CLASS,
                "rows": 4,
                "placeholder": "Escribe el mensaje para la clienta",
            }
        ),
    )


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class ClientsView(ProtectedView, TemplateView):
    template_name = "clients/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "filter_form": ClientsFilterForm(),
                "url_client_list": reverse_lazy("client_list"),
                "url_client_export": reverse_lazy("client_export"),
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
        "estado",
        "identificador_nacional",
        "full_name",
    ]

    ordering_fields = {
        "0": "full_name",
        "1": "identificador_nacional",
        "2": "estado",
        "3": "telefono",
        "4": "email",
    }

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(full_name=Concat("nombre", Value(" "), "apellido"))
        )

    def get_values(self, queryset):
        values = super().get_values(queryset)
        for value in values:
            value["status"] = value["estado"] == Cliente.EstadoChoices.ACTIVO
            value["whatsapp_modal_url"] = (
                reverse_lazy("client_whatsapp_modal", kwargs={"pk": value["pk"]})
                if value["telefono"]
                else ""
            )
        return values

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
                    "className": "bs-xl-modal",
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

    @staticmethod
    def additional_data(queryset) -> dict:
        _additional_data = Cliente.objects.aggregate(
            active_clients_total=Count(
                "pk", filter=Q(estado=Cliente.EstadoChoices.ACTIVO)
            ),
            inactive_clients_total=Count(
                "pk", filter=Q(estado=Cliente.EstadoChoices.INACTIVO)
            ),
        )
        return _additional_data


class ClientExportView(ExcelExportMixin, ClientListView):
    force_export = True
    include_options_column = False
    excel_filename = "clientes"
    excel_sheet_title = "Clientes"

    excel_columns = [
        ExcelColumn("Nombre completo", "full_name", width=30),
        ExcelColumn("Número de documento", "identificador_nacional", width=20),
        ExcelColumn("Teléfono", "telefono", width=18),
        ExcelColumn("Correo", "email", width=30),
        ExcelColumn(
            "Estado",
            "estado",
            width=14,
            align="center",
            formatter=lambda value: (
                "Activo" if value == Cliente.EstadoChoices.ACTIVO else "Inactivo"
            ),
        ),
    ]


class BaseClientModalView(ProtectedView, BSModalFormView):
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

    def form_valid(self, form):
        client = ClientEditor.create(form)
        return JsonResponse({"message": ClientEditor.created_message(client)})


class ClientDetailModalView(BaseClientModalView):
    modal_url = "client_detail_modal"
    pk_url_kwarg = "pk"
    base_object = None

    def get_object(self, queryset=None):
        if not hasattr(self, "_object"):
            client_id = self.kwargs.get(self.pk_url_kwarg)
            self._object = Cliente.objects.filter(pk=client_id).first()
        return self._object

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": self.get_object()}

    def get_initial(self):
        self.base_object = self.get_object()
        return ClientInitial.of(self.base_object)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["client_full_name"] = self.base_object.nombre_completo
        return context

    def form_valid(self, form):
        client = ClientEditor.update(self.get_object(), form)
        return JsonResponse({"message": ClientEditor.updated_message(client)})


class ClientWhatsappModalView(ProtectedView, BSModalReadView):
    template_name = "clients/client_whatsapp_modal.html"
    queryset = Cliente.all_objects.exclude(telefono="")
    default_message = "Hola %(client_name)s, ¿cómo estás?"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.object
        message = self.default_message % {"client_name": client.nombre.strip()}
        context.update(
            {
                "client_full_name": client.nombre_completo,
                "client_phone": client.telefono,
                "form": ClientWhatsappForm(initial={"message": message}),
                "whatsapp_url": get_whatsapp_url(client.telefono, message),
                "whatsapp_web_url": get_whatsapp_url(client.telefono),
                "whatsapp_app_url": get_whatsapp_url(client.telefono, app=True),
            }
        )
        return context


class ClientDeleteModalView(ProtectedView, BSModalDeleteView):
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
        fields = ["telefono", "email", "created"]
        icons = {
            "telefono": "mobile",
            "email": "mail",
            "created": "calendar_today",
        }
        additional_info = []
        for field in fields:
            value = getattr(client, field)
            if not value:
                continue
            text = (
                value
                if field != "created"
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
