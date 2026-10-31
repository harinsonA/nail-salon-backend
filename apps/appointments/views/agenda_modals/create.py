from datetime import date

from bootstrap_modal_forms.generic import BSModalFormView
from django.db import transaction
from django.utils import timezone

from apps.appointments.models.agenda import Cita
from apps.appointments.models.detalle_cita import DetalleCita
from apps.appointments.views.agenda_modals.common import (
    AppointmentFormMixin,
    build_detail,
)
from apps.common.views.base_views import ProtectedView
from apps.payments.accounting import AppointmentPaymentService

"""========================================================================="""
# region ........ Views


class AgendaCreateView(AppointmentFormMixin, ProtectedView, BSModalFormView):
    def selected_date(self):
        today = timezone.localdate()
        try:
            selected = date.fromisoformat(self.kwargs.get("date", ""))
        except ValueError:
            return today
        return max(selected, today)

    def get_initial(self):
        return {
            **super().get_initial(),
            "date": self.selected_date(),
            "assigned_to": self.request.user,
        }

    @transaction.atomic
    def save_appointment(self, data):
        appointment = Cita.objects.create(
            cliente=data["client"],
            fecha_agenda=data["date"],
            hora_agenda=data["time"],
            estado=Cita.EstadoChoices.PENDIENTE,
            observaciones=data["observations"] or None,
            creado_por=self.request.user,
            asignado_a=data["assigned_to"],
        )
        DetalleCita.objects.bulk_create(
            build_detail(appointment, line) for line in data["services"]
        )
        AppointmentPaymentService(appointment, self.request.user).register_advances(
            data["advances"]
        )
        return appointment


# endregion
"""========================================================================="""
