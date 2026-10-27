from bootstrap_modal_forms.generic import BSModalReadView
from django.http import JsonResponse

from apps.appointments.access import AppointmentAccessMixin
from apps.appointments.models import Cita
from apps.appointments.views.agenda_modals.common import (
    AgendaBaseModalView,
    AppointmentPanelMixin,
)

"""========================================================================="""
# region ........ Views


# TODO: antes de ofrecer esta vista en el menú del calendario, bloquear el borrado si la cita tiene
# pagos o movimientos en detalle_pago (reservas, anticipos, abonos o devoluciones): el CASCADE de
# pagos los eliminaría. Ver arquitecturas/anticipos/02-plan-implementacion.html.
class AgendaDeleteModalView(
    AppointmentAccessMixin, AppointmentPanelMixin, AgendaBaseModalView, BSModalReadView
):
    model = Cita
    panel_mode = "delete"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        message = (
            "La cita de %(client_name)s para el día %(date)s a las %(time)s fue eliminada."
        ) % {
            "client_name": self._get_client_full_name(self.object),
            "date": self._get_date_formatted(self.object),
            "time": self._get_time_formatted(self.object),
        }
        self.object.delete()
        return JsonResponse(
            {"message": message},
            status=200,
        )


# endregion
"""========================================================================="""
