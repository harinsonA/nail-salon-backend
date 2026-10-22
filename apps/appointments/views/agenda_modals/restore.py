from bootstrap_modal_forms.generic import BSModalReadView
from django.http import JsonResponse
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.appointments.access import AppointmentAccessMixin
from apps.appointments.models import Cita
from apps.appointments.views.agenda_modals.common import (
    AgendaBaseModalView,
    AppointmentPanelMixin,
)

"""========================================================================="""
# region ........ Views


class AgendaRestoreModalView(
    AppointmentAccessMixin, AppointmentPanelMixin, AgendaBaseModalView, BSModalReadView
):
    model = Cita
    panel_mode = "restore"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.estado != Cita.EstadoChoices.CANCELADA:
            message = "Solo se pueden restaurar las agendas en estado Cancelada."
            return JsonResponse(
                {"message": message},
                status=HTTP_400_BAD_REQUEST,
            )
        self.object.estado = Cita.EstadoChoices.PENDIENTE
        self.object.save()
        message = (
            "La agenda de %(client_name)s para el día %(date)s a las %(time)s fue restaurada a Pendiente."
        ) % {
            "client_name": self._get_client_full_name(self.object),
            "date": self._get_date_formatted(self.object),
            "time": self._get_time_formatted(self.object),
        }
        return JsonResponse(
            {"message": message},
            status=200,
        )


# endregion
"""========================================================================="""
