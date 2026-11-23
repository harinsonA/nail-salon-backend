from apps.appointments.engine import AppointmentRestoration, PrepaidCard
from apps.payments.accounting import AppointmentLedger, PaymentAccount, ServiceLines

from .prepaid_rows import PrepaidRows

"""========================================================================="""
# region ........ Builders


class AppointmentRestorationCard:
    def __init__(self, appointment, viewer):
        self.appointment = appointment
        self.engine = AppointmentRestoration(appointment, viewer)

    def prepaid(self):
        payment = AppointmentLedger.for_appointment(self.appointment).payment
        return int(PaymentAccount(payment).credit()) if payment else 0

    def build(self):
        rows = self.engine.rows
        card = PrepaidCard(rows) if rows else None
        return {
            "id": self.appointment.pk,
            "title": card.restore_title() if card else None,
            "hint": card.restore_hint() if card else None,
            "locked": self.engine.locked,
            "locked_message": card.restore_locked() if self.engine.locked else None,
            "back_label": card.back_label() if card else None,
            "rows": PrepaidRows.build(rows),
            "services_total": int(ServiceLines.amounts(self.appointment)[2]),
            "prepaid": self.prepaid(),
        }


# endregion
"""========================================================================="""
