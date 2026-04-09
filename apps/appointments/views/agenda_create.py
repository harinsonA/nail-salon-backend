import json

from datetime import date
from django import forms
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import TemplateView, FormView

from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.custom_time_fields import CustomDateField
from apps.common.views.base_views import ProtectedView, ProtectedAjaxView
from apps.appointments.models.agenda import Cita
from apps.appointments.views.handler import HandlerAgenda, HandlerAgendaList
from apps.clients.models import Cliente
from apps.services.models import Servicio

"""========================================================================="""
# region ........ Constants

FORM_CONTROL_CLASS = "form-control form-control--custom"
FORM_CONTROL_TEXTAREA_CLASS = f"{FORM_CONTROL_CLASS} form-control--textarea"
FORM_SELECT_CLASS = "form-select form-select--custom"

# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Form


class AgendaForm(forms.Form):
    """Formulario normal (no modal) para crear citas de agenda"""

    client = forms.ModelChoiceField(
        queryset=Cliente.activos.all(),
        required=True,
        label="Cliente",
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    service = forms.ModelChoiceField(
        queryset=Servicio.activos.all(),
        required=True,
        label="Servicio",
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    date_agenda = CustomDateField(
        required=True,
        label="Fecha de la cita",
    )
    time_agenda = forms.TimeField(
        required=True,
        label="Hora de la cita",
        widget=forms.TimeInput(
            attrs={
                "type": "time",
                "class": FORM_CONTROL_CLASS,
                "format": "%H:%M",
            }
        ),
    )
    observations = forms.CharField(
        required=False,
        label="Observaciones",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": FORM_CONTROL_TEXTAREA_CLASS,
            }
        ),
    )
    quantity = forms.IntegerField(
        label="Cantidad",
        initial=1,
        min_value=1,
        required=True,
        widget=forms.NumberInput(
            attrs={
                "class": "pricing-receipt-input",
                "min": "1",
                "placeholder": "1",
            }
        ),
    )
    discount_amount = forms.IntegerField(
        label="Descuento",
        initial=0,
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": "pricing-receipt-input",
                "min": "0",
                "placeholder": "1000",
            }
        ),
    )


class AvailableHoursFilterForm(forms.Form):
    date_agenda = CustomDateField(
        required=True,
        label="Fecha de la cita",
    )
    time_agenda = forms.TimeField(
        required=True,
        label="Hora de la cita",
        widget=forms.TimeInput(
            attrs={
                "type": "time",
                "class": FORM_CONTROL_CLASS,
                "format": "%H:%M",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        date_agenda = cleaned_data.get("date_agenda", None)
        if not date_agenda:
            return {}
        # CustomDateField.to_python() ya convirtió el string a objeto date
        return {
            "fecha_agenda": date_agenda,
        }


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Views


class AgendaCreateView(ProtectedView, FormView):
    template_name = "appointments/agenda_create.html"
    form_class = AgendaForm

    def get_initial(self):
        initial = super().get_initial()
        _date_selected = self.kwargs.get("date", date.today().strftime("%Y-%m-%d"))
        _year, _month, _day = _date_selected.split("-")
        initial.update(
            {
                "date_agenda": f"{_day}/{_month}/{_year}",
                "time_agenda": "09:00",
            }
        )
        return initial

    def get_success_url(self, **kwargs):
        _date_selected = kwargs.get("date", date.today().strftime("%Y-%m-%d"))
        return reverse_lazy("calendar_appointments", kwargs={"date": _date_selected})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        _date_selected = self.kwargs.get("date", date.today().strftime("%Y-%m-%d"))
        context.update(
            {
                "cancel_url": reverse_lazy(
                    "calendar_appointments", kwargs={"date": _date_selected}
                ),
                "agenda_create_url": reverse_lazy(
                    "create_appointment_from_calendar", kwargs={"date": _date_selected}
                ),
                "service_details_url": reverse_lazy("service_details_ajax"),
                "available_hours_url": reverse_lazy("available_hours_ajax"),
            }
        )
        return context

    @staticmethod
    def __get_clients_ids(agendas_data: list) -> list:
        clients_ids = set()
        for agenda in agendas_data:
            client_id = agenda.get("idCliente")
            if not client_id or client_id in clients_ids:
                continue
            clients_ids.add(client_id)
        return list(clients_ids)

    @staticmethod
    def __get_service_ids(agendas_data: list) -> list:
        services_ids = set()
        for agenda in agendas_data:
            _services = agenda.get("servicios")
            if not _services:
                continue
            for service in _services:
                service_id = service.get("id")
                if not service_id or service_id in services_ids:
                    continue
                services_ids.add(service_id)
        return list(services_ids)

    def post(self, request, *args, **kwargs):
        agendas = request.POST.get("agenda", None)
        if not agendas:
            return JsonResponse(
                {"message": "No se recibieron datos de agenda."},
                status=HTTP_400_BAD_REQUEST,
            )
        agendas = json.loads(agendas)
        clients_ids = self.__get_clients_ids(agendas)
        services_ids = self.__get_service_ids(agendas)
        handler = HandlerAgenda(clients_ids, services_ids)
        result = handler.create(agendas)
        if result.is_err():
            return JsonResponse(
                {"message": result.err()},
                status=HTTP_400_BAD_REQUEST,
            )
        messages.success(request, result.ok())
        return JsonResponse({"success_url": self.get_success_url(**kwargs)})


class ServiceDetailsAjax(ProtectedAjaxView, TemplateView):
    def get(self, request, *args, **kwargs):
        service_id = request.GET.get("service_id", None)
        if not service_id:
            return JsonResponse(
                {"message": "El ID del servicio es requerido."},
                status=HTTP_400_BAD_REQUEST,
            )
        service = Servicio.activos.filter(pk=service_id).first()
        if not service:
            return JsonResponse(
                {"error": "Servicios no encontrados"},
                status=HTTP_400_BAD_REQUEST,
            )
        data = {
            "id": service.id,
            "nombre": service.nombre,
            "precio": int(service.precio),
            "duracion_estimada": service.duracion_estimada.total_seconds() // 60,
        }
        return JsonResponse(data)


class AvailableHoursAjax(BaseListViewAjax):
    model = Cita
    filter_form_class = AvailableHoursFilterForm
    _filters = {"estado": Cita.EstadoChoices.PENDIENTE}

    field_list = [
        "pk",
        "hora_agenda",
        "cliente__nombre",
        "cliente__apellido",
    ]
    ordering_fields = {
        "0": "hora_agenda",
    }

    def get_values(self, queryset):
        values = super().get_values(queryset)
        for value in values:
            value["hora_agenda"] = value["hora_agenda"].strftime("%H:%M")
            value["client_full_name"] = HandlerAgendaList.get_client_full_name(**value)
        return values


# endregion
"""========================================================================="""
