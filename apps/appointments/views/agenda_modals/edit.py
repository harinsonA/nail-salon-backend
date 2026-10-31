from bootstrap_modal_forms.generic import BSModalUpdateView
from django.db import transaction

from apps.appointments.access import AppointmentAccessMixin
from apps.appointments.models import Cita
from apps.appointments.views.agenda_modals.common import (
    AppointmentFormMixin,
    build_detail,
    client_name,
    detail_line,
)
from apps.common.views.base_views import ProtectedView
from apps.payments.accounting import AppointmentPaymentService

"""========================================================================="""
# region ........ Views


class AgendaUpdateModalView(
    AppointmentAccessMixin, AppointmentFormMixin, ProtectedView, BSModalUpdateView
):
    model = Cita
    save_label = "Guardar cambios"
    success_prefix = "Cita actualizada"

    def get_queryset(self):
        return super().get_queryset().filter(estado=Cita.EstadoChoices.PENDIENTE)

    def form_title(self):
        return f"Editar cita: {client_name(self.object.cliente)}"

    def initial_lines(self):
        details = self.object.detalles.select_related("servicio__categoria").order_by(
            "pk"
        )
        return [detail_line(detail) for detail in details]

    @transaction.atomic
    def save_appointment(self, data):
        appointment = self.object
        appointment.cliente = data["client"]
        appointment.fecha_agenda = data["date"]
        appointment.hora_agenda = data["time"]
        appointment.observaciones = data["observations"] or None
        appointment.asignado_a = data["assigned_to"]
        appointment.save()
        kept = [line["detail"].pk for line in data["services"] if line["detail"]]
        appointment.detalles.exclude(pk__in=kept).delete()
        for line in data["services"]:
            detail = line["detail"]
            if not detail:
                build_detail(appointment, line).save()
                continue
            detail.cantidad_servicios = line["quantity"]
            detail.descuento = line["discount"]
            detail.precio_acordado = line["total"]
            detail.save(
                update_fields=[
                    "cantidad_servicios",
                    "descuento",
                    "precio_acordado",
                    "modified",
                ]
            )
        AppointmentPaymentService(appointment, self.request.user).sync_advances(
            data["advances"]
        )
        return appointment


# endregion
"""========================================================================="""
