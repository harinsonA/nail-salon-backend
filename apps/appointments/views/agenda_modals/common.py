from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.appointments.editing import AppointmentForm, AppointmentSavedMessage
from apps.appointments.engine.messages import MAX_QUANTITY, REFERENCE_MAX_LENGTH
from apps.appointments.panel import AppointmentPanel
from apps.common.utils.dates import format_date_time, format_plain_date
from apps.common.utils.utils import get_errors_to_response
from apps.common.views.base_views import ProtectedView
from apps.payments.choices import MetodoPago
from apps.services.models import Categoria, Servicio

"""========================================================================="""
# region ........ Constants


NO_CATEGORY = "Sin categoría"


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Helpers


def client_name(client):
    return AppointmentSavedMessage.client_name(client)


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
        return AppointmentSavedMessage.text(self.success_prefix, appointment)

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
