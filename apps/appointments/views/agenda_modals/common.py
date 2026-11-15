import json

from bootstrap_modal_forms.forms import BSModalForm
from django import forms
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.appointments.engine import AppointmentDraft, AppointmentRuleError
from apps.appointments.engine.messages import (
    ADVANCES_INVALID,
    MAX_QUANTITY,
    REFERENCE_MAX_LENGTH,
    RESERVATION_INVALID,
    SERVICES_INVALID,
)
from apps.appointments.panel import AppointmentPanel
from apps.clients.models import Cliente
from apps.common.form_classes import (
    FORM_CONTROL_CLASS,
    FORM_CONTROL_TEXTAREA_CLASS,
    FORM_SELECT2_CLASS,
)
from apps.common.form_fields import NoteField
from apps.common.utils.dates import (
    format_date_time,
    format_long_date,
    format_plain_date,
)
from apps.common.utils.text import user_display_name
from apps.common.utils.utils import get_errors_to_response
from apps.common.views.base_views import ProtectedView
from apps.payments.choices import MetodoPago
from apps.services.models import Categoria, Servicio

User = get_user_model()

"""========================================================================="""
# region ........ Constants


DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M"
NO_CATEGORY = "Sin categoría"


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Helpers


def client_name(client):
    return f"{client.nombre} {client.apellido or ''}".strip()


def category_name(service):
    return service.categoria.nombre if service and service.categoria else NO_CATEGORY


def service_data(service):
    return {
        "id": service.pk,
        "nombre": service.nombre,
        "precio": int(service.precio),
        "categoria": service.categoria_id,
        "categoriaNombre": category_name(service),
    }


def detail_line(detail):
    service = detail.servicio
    return {
        "detalle": detail.pk,
        "service": {
            "id": detail.servicio_id or f"detalle-{detail.pk}",
            "nombre": detail.nombre_servicio,
            "precio": int(detail.precio_servicio),
            "categoria": service.categoria_id if service else None,
            "categoriaNombre": category_name(service),
        },
        "quantity": detail.cantidad_servicios,
        "discount": int(detail.descuento),
    }


def initial_from(appointment):
    return {
        "client": appointment.cliente,
        "assigned_to": appointment.asignado_a,
        "date": appointment.fecha_agenda,
        "time": appointment.hora_agenda,
        "observations": appointment.observaciones or "",
    }


class StaffChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return user_display_name(obj)


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class AppointmentForm(BSModalForm):
    client = forms.ModelChoiceField(
        queryset=Cliente.objects.none(),
        label="Cliente",
        empty_label="Selecciona un cliente",
        widget=forms.Select(attrs={"class": FORM_SELECT2_CLASS}),
    )
    assigned_to = StaffChoiceField(
        queryset=User.objects.none(),
        label="Asignada a",
        empty_label=None,
        widget=forms.Select(attrs={"class": FORM_SELECT2_CLASS}),
    )
    date = forms.DateField(
        label="Fecha",
        input_formats=[DATE_FORMAT],
        widget=forms.DateInput(
            format=DATE_FORMAT,
            attrs={"type": "date", "class": FORM_CONTROL_CLASS},
        ),
    )
    time = forms.TimeField(
        label="Hora",
        input_formats=[TIME_FORMAT],
        widget=forms.TimeInput(
            format=TIME_FORMAT,
            attrs={"type": "time", "step": "60", "class": FORM_CONTROL_CLASS},
        ),
    )
    observations = NoteField(
        label="Observaciones",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "class": FORM_CONTROL_TEXTAREA_CLASS,
                "placeholder": "Alergias, preferencias, diseño que quiere…",
            }
        ),
    )
    services = forms.CharField(required=False, widget=forms.HiddenInput)
    advances = forms.CharField(required=False, widget=forms.HiddenInput)
    reservation = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        self.draft = AppointmentDraft(self.request.user, instance)
        if instance:
            self.initial = {**initial_from(instance), **self.initial}
        current_client = instance.cliente if instance else None
        current_staff = instance.asignado_a if instance else None
        assignment = self.draft.assignment
        self.fields["client"].queryset = assignment.clients(current_client)
        self.fields["assigned_to"].queryset = assignment.staff(current_staff)
        if assignment.collaborator:
            self.fields["assigned_to"].disabled = True
            self.fields["assigned_to"].initial = self.request.user

    @staticmethod
    def decode(raw, message):
        try:
            return json.loads(raw)
        except json.JSONDecodeError as error:
            raise forms.ValidationError(message) from error

    @staticmethod
    def apply(rule, value):
        try:
            return rule(value)
        except AppointmentRuleError as error:
            raise forms.ValidationError(error.message) from error

    def clean_services(self):
        lines = self.decode(self.cleaned_data.get("services") or "[]", SERVICES_INVALID)
        return self.apply(self.draft.services.clean, lines)

    def clean_assigned_to(self):
        return self.draft.assignment.resolve(self.cleaned_data["assigned_to"])

    def clean_advances(self):
        advances = self.decode(self.cleaned_data.get("advances") or "[]", ADVANCES_INVALID)
        return self.apply(self.draft.advances.clean, advances)

    def clean_reservation(self):
        raw = self.cleaned_data.get("reservation")
        if not self.draft.reservation.available or not raw:
            return {}
        data = self.decode(raw, RESERVATION_INVALID)
        return self.apply(self.draft.reservation_change.clean, data)

    def clean(self):
        cleaned_data = super().clean()
        lines = cleaned_data.get("services")
        if not lines or "advances" not in cleaned_data or "reservation" not in cleaned_data:
            return cleaned_data
        error = self.draft.limit.check(
            lines, cleaned_data["advances"], cleaned_data["reservation"]
        )
        if error:
            self.add_error(error.field, error.message)
        return cleaned_data


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Mixins


class AppointmentFormMixin:
    template_name = "appointments/agenda_create_modal.html"
    form_class = AppointmentForm
    save_label = "Agendar cita"
    success_prefix = "Cita agendada"

    def get(self, request, *args, **kwargs):
        if request.headers.get("x-requested-with") != "XMLHttpRequest":
            return redirect("calendar")
        return super().get(request, *args, **kwargs)

    def form_title(self):
        return "Nueva cita"

    def initial_lines(self):
        return []

    @staticmethod
    def advance_rows(form):
        return [
            {
                "id": row.pk,
                "amount": int(row.monto_pago),
                "method": row.metodo_pago,
                "reference": row.referencia_pago or "",
                "date": format_date_time(row.fecha_pago),
            }
            for row in form.draft.advances.saved
        ]

    def get_context_data(self, **kwargs):
        appointment = getattr(self, "object", None)
        context = super().get_context_data(**kwargs)
        form = context["form"]
        draft = form.draft
        reservation = draft.reservation.config(draft.can_change_saved)
        services = Servicio.activos.select_related("categoria").order_by("nombre")
        categories = Categoria.activos.order_by("nombre").values("pk", "nombre")
        return {
            **context,
            "modal_url": self.request.path,
            "form_title": self.form_title(),
            "save_label": self.save_label,
            "appointment_form_config": {
                "services": [service_data(service) for service in services],
                "categories": [
                    {"id": category["pk"], "nombre": category["nombre"]}
                    for category in categories
                ],
                "lines": self.initial_lines(),
                "appointmentId": appointment.pk if appointment else None,
                "busyUrl": reverse("available_hours_ajax"),
                "currentUser": self.request.user.pk,
                "maxQuantity": MAX_QUANTITY,
                "advances": {
                    "rows": self.advance_rows(form),
                    "canChangeSaved": draft.can_change_saved,
                    "methods": MetodoPago.CHOICES,
                    "cash": MetodoPago.EFECTIVO,
                    "referenceMaxLength": REFERENCE_MAX_LENGTH,
                },
                "reservation": reservation,
            },
            "reservation": reservation,
            "payment_methods": MetodoPago.CHOICES,
            "reference_max_length": REFERENCE_MAX_LENGTH,
        }

    def success_message(self, appointment):
        day = format_long_date(appointment.fecha_agenda).lower()
        hour = appointment.hora_agenda.strftime(TIME_FORMAT)
        return f"{self.success_prefix}: {client_name(appointment.cliente)}, {day}, {hour}."

    def form_valid(self, form):
        appointment = self.save_appointment(form.cleaned_data)
        return JsonResponse(
            {
                "message": self.success_message(appointment),
                "fecha": appointment.fecha_agenda.isoformat(),
            }
        )

    def form_invalid(self, form):
        errors = get_errors_to_response(form.errors)
        return JsonResponse({"errors": errors}, status=HTTP_400_BAD_REQUEST)


class AppointmentPanelMixin:
    template_name = "appointments/agenda_panel.html"
    panel_mode = "detail"

    def get_context_data(self, **kwargs):
        panel = AppointmentPanel(self.object, self.request.user, self.panel_mode)
        return {
            **super().get_context_data(**kwargs),
            **panel.context(),
            "modal_url": self.request.path,
        }


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class AgendaBaseModalView(ProtectedView):
    """Base class for agenda modal views that provides common context data"""

    @staticmethod
    def _get_client_full_name(object_base) -> str:
        first_name = object_base.cliente.nombre or ""
        last_name = object_base.cliente.apellido or ""
        return f"{first_name} {last_name}".strip()

    @staticmethod
    def _get_date_formatted(object_base) -> str:
        return format_plain_date(object_base.fecha_agenda)

    @staticmethod
    def _get_time_formatted(object_base) -> str:
        return object_base.hora_agenda.strftime("%H:%M")

    @staticmethod
    def _get_phone_number(object_base) -> str:
        return object_base.cliente.telefono or "Sin teléfono"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object_base = context["object"]

        context.update(
            {
                "appointment_id": object_base.pk,
                "client_full_name": self._get_client_full_name(object_base),
                "date_formatted": self._get_date_formatted(object_base),
                "time_formatted": self._get_time_formatted(object_base),
                "phone_number": self._get_phone_number(object_base),
            }
        )
        return context


# endregion
"""========================================================================="""
