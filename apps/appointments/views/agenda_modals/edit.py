from bootstrap_modal_forms.generic import BSModalUpdateView

from apps.appointments.access import AppointmentAccessMixin
from apps.appointments.engine import AppointmentWriter
from apps.appointments.models import Cita
from apps.appointments.views.agenda_modals.common import (
    AppointmentFormMixin,
    client_name,
    detail_line,
)
from apps.common.views.base_views import ProtectedView

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

    def save_appointment(self, data):
        return AppointmentWriter(self.request.user).update(self.object, data)


# endregion
"""========================================================================="""
