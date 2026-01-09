import json

from datetime import date
from django import forms
from django.contrib import messages
from django.db.models import Count
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from rest_framework.status import HTTP_400_BAD_REQUEST
from bootstrap_modal_forms.forms import BSModalModelForm
from bootstrap_modal_forms.generic import BSModalUpdateView, BSModalReadView

from apps.appointments.models import DetalleCita
from apps.appointments.models.agenda import Cita
from apps.appointments.views.handler import HandlerAgendaList
from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.custom_time_fields import (
    CustomMonthField,
    CustomDateField,
    MONTH_NUMBER_TO_NAME,
)
from apps.common.utils.utils import get_errors_to_response
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


class AgendaFilterForm(forms.Form):
    months = CustomMonthField(
        label="Mes",
        required=False,
    )
    status = forms.ChoiceField(
        label="Estado",
        required=False,
        initial=Cita.EstadoChoices.PENDIENTE,
        choices=Cita.EstadoChoices.choices,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )

    def clean(self):
        cleaned_data = super().clean()
        agendaStatus = cleaned_data.get("status", Cita.EstadoChoices.PENDIENTE)
        first_day, last_day = cleaned_data.get("months", (None, None))
        return {
            "estado": agendaStatus,
            "fecha_agenda__gte": first_day,
            "fecha_agenda__lte": last_day,
        }


class AgendaModalForm(BSModalModelForm):
    service = forms.ModelChoiceField(
        queryset=Servicio.activos.all(),
        required=False,
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
        required=False,
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

    def clean_date_agenda(self):
        date_agenda = self.cleaned_data.get("date_agenda", "")
        if not date_agenda:
            raise forms.ValidationError("La fecha de la cita es obligatoria.")
        day, month, year = date_agenda.split("/")
        return date(year=int(year), month=int(month), day=int(day))

    class Meta:
        model = Cita
        fields = []

    def save(self, commit=False):
        return self.instance


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Views


class AppointmentsView(TemplateView):
    template_name = "appointments/list.html"

    @staticmethod
    def get_initial_month() -> str:
        today = date.today()
        return f"{today.strftime('%B %Y')}".capitalize()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "filter_form": AgendaFilterForm(
                    initial={"months": self.get_initial_month()}
                ),
                "url_agenda_list": reverse_lazy("agenda_list"),
                "url_agenda_create": reverse_lazy("agenda_create"),
            }
        )
        return context


class AgendaListView(BaseListViewAjax):
    model = Cita
    filter_form_class = AgendaFilterForm

    field_list = [
        "pk",
        "cliente__nombre",
        "cliente__apellido",
        "fecha_agenda",
        "hora_agenda",
        "estado",
        "cantidad_servicios",
    ]

    ordering_fields = {
        "0": "fecha_agenda",
    }

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("cliente")
            .prefetch_related("detalles")
            .annotate(cantidad_servicios=Count("detalles"))
        )

    def get_values(self, queryset):
        values = [
            *queryset.values(*self.field_list).order_by("fecha_agenda", "hora_agenda")
        ]
        return HandlerAgendaList().get_data(values)


class AgendaUpdateModalView(BSModalUpdateView):
    template_name = "appointments/agenda_detail_modal.html"
    model = Cita
    form_class = AgendaModalForm

    def get_initial(self):
        initial = super().get_initial()
        initial.update(
            {
                "date_agenda": self.object.fecha_agenda.strftime("%d/%m/%Y"),
                "time_agenda": self.object.hora_agenda.strftime("%H:%M"),
            }
        )
        return initial

    def get_success_url(self):
        return reverse_lazy("agenda_list")

    @staticmethod
    def __get_client_full_name(object_base) -> str:
        first_name = object_base.cliente.nombre or ""
        last_name = object_base.cliente.apellido or ""
        return f"{first_name} {last_name}".strip()

    @staticmethod
    def __get_date_formatted(object_base) -> str:
        return object_base.fecha_agenda.strftime("%d/%m/%Y")

    @staticmethod
    def __get_time_formatted(object_base) -> str:
        return object_base.hora_agenda.strftime("%H:%M")

    @staticmethod
    def __get_duration_in_minutes(detail) -> int:
        return int(detail.servicio.duracion_estimada.total_seconds() / 60)

    def __get_service_data(self, object_base) -> list:
        agenda_details = list(object_base.detalles.all().select_related("servicio"))
        if not agenda_details:
            return []
        return [
            {
                "detalle_id": detail.pk,
                "total": float(detail.precio_acordado),
                "cantidad": detail.cantidad_servicios,
                "descuento": float(detail.descuento),
                "id": detail.servicio.pk,
                "nombre": detail.servicio.nombre,
                "precio": float(detail.servicio.precio),
                "duracion_estimada": self.__get_duration_in_minutes(detail),
            }
            for detail in agenda_details
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object_base = context["object"]
        self.__get_service_data(object_base)
        context.update(
            {
                "client_full_name": self.__get_client_full_name(object_base),
                "date_formatted": self.__get_date_formatted(object_base),
                "time_formatted": self.__get_time_formatted(object_base),
                "service_data": json.dumps(self.__get_service_data(object_base)),
            }
        )
        return context

    def form_invalid(self, form):
        errors = get_errors_to_response(form.errors)
        return JsonResponse({"errors": errors}, status=HTTP_400_BAD_REQUEST)

    @staticmethod
    def __get_json(data):
        try:
            return json.loads(data)
        except Exception:
            return None

    @staticmethod
    def __delete_detail_agenda(agenda_id, detail_ids):
        DetalleCita.objects.filter(cita_id=agenda_id, pk__in=detail_ids).delete()

    def save_detail_agenda(self, service_data):
        new_services = []
        for service in service_data:
            detail_id = service.get("detalle_id", None)
            is_service_ready = (
                not detail_id
                or not isinstance(detail_id, str)
                or not detail_id.startswith("000_")
            )

            if is_service_ready:
                continue
            new_services.append(
                DetalleCita(
                    cita=self.object,
                    cantidad_servicios=service.get("cantidad", 1),
                    servicio_id=service.get("id"),
                    precio_acordado=service.get("total", 0),
                    descuento=service.get("descuento", 0),
                    notas_detalle=service.get("observaciones", ""),
                )
            )
        if not new_services:
            return
        DetalleCita.objects.bulk_create(new_services)

    def form_valid(self, form):
        if self.object.estado != Cita.EstadoChoices.PENDIENTE:
            message = "Solo se pueden modificar las agendas en estado Pendiente."
            return JsonResponse(
                {"message": message},
                status=HTTP_400_BAD_REQUEST,
            )
        services_selected = self.__get_json(
            self.request.POST.get("servicesSelected", "")
        )
        if not services_selected:
            message = "No se seleccionaron servicios para la agenda."
            return JsonResponse(
                {"message": message},
                status=HTTP_400_BAD_REQUEST,
            )

        services_to_delete_selected = self.__get_json(
            self.request.POST.get("servicesToDeleteSelected", "")
        )
        if services_to_delete_selected:
            self.__delete_detail_agenda(
                agenda_id=self.object.pk,
                detail_ids=services_to_delete_selected,
            )
        cleaned_data = form.cleaned_data
        self.object.fecha_agenda = cleaned_data.get("date_agenda")
        self.object.hora_agenda = cleaned_data.get("time_agenda")
        self.object.save()
        self.save_detail_agenda(services_selected)
        message = (
            "Agenda de %(client_name)s fue actualizada para el día %(date)s a las %(time)s."
        ) % {
            "client_name": self.__get_client_full_name(self.object),
            "date": self.__get_date_formatted(self.object),
            "time": self.__get_time_formatted(self.object),
        }
        messages.success(self.request, message)
        return JsonResponse(
            {"detail": message},
            status=200,
        )


class AgendaCancelModalView(BSModalReadView):
    template_name = "appointments/agenda_cancel_modal.html"
    model = Cita

    @staticmethod
    def __get_client_full_name(object_base) -> str:
        first_name = object_base.cliente.nombre or ""
        last_name = object_base.cliente.apellido or ""
        return f"{first_name} {last_name}".strip()

    @staticmethod
    def __get_date_formatted(object_base) -> str:
        day = object_base.fecha_agenda.day
        month = MONTH_NUMBER_TO_NAME[object_base.fecha_agenda.month]
        year = object_base.fecha_agenda.year
        return f"{day} de {month} del {year}"

    @staticmethod
    def __get_time_formatted(object_base) -> str:
        return object_base.hora_agenda.strftime("%H:%M")

    @staticmethod
    def __get_phone_number(object_base) -> str:
        return object_base.cliente.telefono or "Sin teléfono"

    @staticmethod
    def __get_services_count(object_base) -> int:
        return object_base.detalles.count()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object_base = context["object"]

        context.update(
            {
                "appointment_id": object_base.pk,
                "client_full_name": self.__get_client_full_name(object_base),
                "date_formatted": self.__get_date_formatted(object_base),
                "time_formatted": self.__get_time_formatted(object_base),
                "phone_number": self.__get_phone_number(object_base),
                "services_count": self.__get_services_count(object_base),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.estado != Cita.EstadoChoices.PENDIENTE:
            message = "Solo se pueden cancelar las agendas en estado Pendiente."
            return JsonResponse(
                {"message": message},
                status=HTTP_400_BAD_REQUEST,
            )
        self.object.estado = Cita.EstadoChoices.CANCELADA
        self.object.save()
        message = (
            "La agenda de %(client_name)s para el día %(date)s a las %(time)s fue cancelada."
        ) % {
            "client_name": self.__get_client_full_name(self.object),
            "date": self.__get_date_formatted(self.object),
            "time": self.__get_time_formatted(self.object),
        }
        return JsonResponse(
            {"message": message},
            status=200,
        )


class AgendaDeleteModalView(BSModalReadView):
    template_name = "common/delete_modal.html"
    model = Cita
    success_message = "Cita de %(client_full_name)s eliminada exitosamente."

    def get_object(self, queryset=None):
        agenda_id = self.kwargs.get("pk")
        return Cita.objects.filter(pk=agenda_id).first()

    @staticmethod
    def __get_client_full_name(object_base) -> str:
        first_name = object_base.cliente.nombre or ""
        last_name = object_base.cliente.apellido or ""
        return f"{first_name} {last_name}".strip()

    @staticmethod
    def __get_date_time_formatted(object_base) -> str:
        day = object_base.fecha_agenda.day
        month = MONTH_NUMBER_TO_NAME[object_base.fecha_agenda.month]
        year = object_base.fecha_agenda.year
        time = object_base.hora_agenda.strftime("%H:%M")
        return f"{day} de {month} de {year} a las {time}"

    def get_aditional_information(self, cita: Cita) -> list:
        date_time = self.__get_date_time_formatted(cita)
        additional_info = [
            {"text": f"Fecha cita: {date_time}", "icon": "event"},
        ]

        if cita.cliente.telefono:
            additional_info.append(
                {"text": f"Teléfono: {cita.cliente.telefono}", "icon": "phone"}
            )

        additional_info.extend(
            [
                {"text": f"Estado: {cita.get_estado_display()}", "icon": "info"},
                {"text": f"Servicios: {cita.detalles.count()}", "icon": "hand_meal"},
            ]
        )
        return additional_info

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        kwargs.update(
            {
                "view": self,
                "object": self.object,
                "id_register": self.object.pk,
                "name_register": self.__get_client_full_name(self.object),
                "aditional_information": self.get_aditional_information(self.object),
            }
        )
        context_object_name = self.get_context_object_name(self.object)
        if context_object_name:
            kwargs[context_object_name] = self.object
        return kwargs

    def post(self, request, *args, **kwargs):
        cita = self.get_object()
        client_full_name = self.__get_client_full_name(cita)
        date_formatted = self.__get_date_time_formatted(cita)
        cita.delete()
        message = (
            "La cita de %(client_full_name)s para el día %(date)s fue eliminada exitosamente."
        ) % {
            "client_full_name": client_full_name,
            "date": date_formatted,
        }
        return JsonResponse(
            {"message": message},
            status=200,
        )


class AgendaConfirmationModal(BSModalUpdateView):
    template_name = "appointments/agenda_confirmation_modal.html"
    model = Cita
    form_class = AgendaModalForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object_base = context["object"]
        context.update(
            {
                "client_full_name": f"{object_base.cliente.nombre} {object_base.cliente.apellido}",
                "date_formatted": object_base.fecha_agenda.strftime("%d/%m/%Y"),
                "time_formatted": object_base.hora_agenda.strftime("%H:%M"),
            }
        )
        return context


# endregion
"""========================================================================="""
