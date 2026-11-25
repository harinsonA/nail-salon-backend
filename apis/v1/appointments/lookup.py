from rest_framework.exceptions import NotFound

from apis.common import messages
from apps.appointments.access import visible_appointments
from apps.appointments.models import Cita


class AppointmentLookup:
    @staticmethod
    def visible(user, pk, lock=False):
        appointments = visible_appointments(user)
        if lock:
            appointments = appointments.select_for_update(of=("self",))
        appointment = appointments.filter(pk=pk).first()
        if appointment is None:
            raise NotFound(AppointmentLookup.missing_message(pk))
        return appointment

    @staticmethod
    def missing_message(pk):
        if Cita.objects.filter(pk=pk).exists():
            return messages.APPOINTMENT_NOT_YOURS
        return messages.APPOINTMENT_NOT_FOUND
