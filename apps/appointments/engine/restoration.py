from django.db import transaction

from apps.appointments.access import is_collaborator
from apps.appointments.engine.errors import AppointmentLockedError, AppointmentRuleError
from apps.appointments.engine.messages import RESTORE_NOT_CANCELLED, RESTORED_INVALID
from apps.appointments.engine.prepaid_card import PrepaidCard
from apps.appointments.engine.prepaid_snapshot import PrepaidSnapshot
from apps.appointments.models import Cita
from apps.payments.accounting import AppointmentLedger, AppointmentPaymentService


class AppointmentRestoration:
    def __init__(self, appointment, user):
        self.appointment = appointment
        self.user = user
        self.rows = AppointmentLedger.for_appointment(appointment).retained_prepaid()
        self.locked = bool(self.rows) and is_collaborator(user)

    def check(self):
        if self.appointment.estado != Cita.EstadoChoices.CANCELADA:
            raise AppointmentRuleError(RESTORE_NOT_CANCELLED)
        if self.locked:
            raise AppointmentLockedError(PrepaidCard(self.rows).restore_locked())

    def clean_restored(self, restored):
        if not isinstance(restored, list):
            raise AppointmentRuleError(RESTORED_INVALID)
        if any(isinstance(pk, bool) or not isinstance(pk, int) for pk in restored):
            raise AppointmentRuleError(RESTORED_INVALID)
        rows = {row.pk for row in self.rows}
        if len(restored) != len(set(restored)) or not set(restored) <= rows:
            raise AppointmentRuleError(RESTORED_INVALID)
        return set(restored)

    def rows_changed(self, seen):
        return PrepaidSnapshot.changed(self.rows, seen)

    @transaction.atomic
    def restore(self, restored):
        self.check()
        self.appointment.estado = Cita.EstadoChoices.PENDIENTE
        self.appointment.save()
        return AppointmentPaymentService(self.appointment, self.user).restore(restored)
