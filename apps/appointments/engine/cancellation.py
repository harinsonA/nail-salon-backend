from django.db import transaction

from apps.appointments.access import is_collaborator
from apps.appointments.engine.errors import AppointmentLockedError, AppointmentRuleError
from apps.appointments.engine.messages import (
    CANCEL_NOT_PENDING,
    REFERENCE_MAX_LENGTH,
    REFUNDS_INVALID,
)
from apps.appointments.engine.prepaid_card import PrepaidCard
from apps.appointments.engine.prepaid_snapshot import PrepaidSnapshot
from apps.appointments.models import Cita
from apps.payments.accounting import (
    AppointmentLedger,
    AppointmentPaymentService,
    PaymentLabels,
)


class AppointmentCancellation:
    def __init__(self, appointment, user):
        self.appointment = appointment
        self.user = user
        self.rows = AppointmentLedger.for_appointment(appointment).open_prepaid()
        self.locked = bool(self.rows) and is_collaborator(user)

    def check(self):
        if self.appointment.estado != Cita.EstadoChoices.PENDIENTE:
            raise AppointmentRuleError(CANCEL_NOT_PENDING)
        if self.locked:
            raise AppointmentLockedError(PrepaidCard(self.rows).cancel_locked())

    def clean_refunds(self, refunds):
        if not isinstance(refunds, list):
            raise AppointmentRuleError(REFUNDS_INVALID)
        rows = {row.pk for row in self.rows}
        cleaned = {}
        for refund in refunds:
            pk, values = self.clean_refund(refund, rows)
            if pk in cleaned:
                raise AppointmentRuleError(REFUNDS_INVALID)
            cleaned[pk] = values
        return cleaned

    @staticmethod
    def clean_refund(refund, rows):
        if not isinstance(refund, dict):
            raise AppointmentRuleError(REFUNDS_INVALID)
        try:
            pk = int(refund.get("id"))
        except (TypeError, ValueError) as error:
            raise AppointmentRuleError(REFUNDS_INVALID) from error
        method = refund.get("metodo")
        reference = refund.get("referencia") or ""
        if pk not in rows or method not in PaymentLabels.REFUND_METHODS:
            raise AppointmentRuleError(REFUNDS_INVALID)
        if not isinstance(reference, str) or len(reference.strip()) > REFERENCE_MAX_LENGTH:
            raise AppointmentRuleError(REFUNDS_INVALID)
        return pk, {"method": method, "reference": reference.strip()}

    def rows_changed(self, seen):
        return PrepaidSnapshot.changed(self.rows, seen)

    @transaction.atomic
    def cancel(self, refunds):
        self.check()
        self.appointment.estado = Cita.EstadoChoices.CANCELADA
        self.appointment.save()
        return AppointmentPaymentService(self.appointment, self.user).cancel(refunds)
