from apps.appointments.engine import AppointmentCancellation, PrepaidCard
from apps.appointments.engine.messages import REFERENCE_MAX_LENGTH
from apps.payments.accounting import PaymentLabels
from apps.payments.choices import MetodoPago

from .prepaid_rows import PrepaidRows

"""========================================================================="""
# region ........ Builders


class AppointmentCancellationCard:
    def __init__(self, appointment, viewer):
        self.appointment = appointment
        self.engine = AppointmentCancellation(appointment, viewer)

    def build(self):
        rows = self.engine.rows
        card = PrepaidCard(rows) if rows else None
        return {
            "id": self.appointment.pk,
            "title": card.cancel_title() if card else None,
            "hint": card.cancel_hint() if card else None,
            "locked": self.engine.locked,
            "locked_message": card.cancel_locked() if self.engine.locked else None,
            "rows": PrepaidRows.build(rows),
            "refund_methods": [
                {"value": value, "label": label} for value, label in PaymentLabels.refund_choices()
            ],
            "cash": MetodoPago.EFECTIVO,
            "transfer": MetodoPago.TRANSFERENCIA,
            "reference_max_length": REFERENCE_MAX_LENGTH,
        }


# endregion
"""========================================================================="""
