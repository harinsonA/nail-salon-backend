from apps.appointments.engine.advances import AdvanceChanges
from apps.appointments.engine.errors import AppointmentRuleError
from apps.appointments.engine.messages import ADVANCES_TOO_HIGH, RESERVATION_TOO_HIGH
from apps.appointments.engine.reservation_change import ReservationChange
from apps.appointments.engine.services import AppointmentServices
from apps.common.utils.currency import Money
from apps.payments.accounting import PaymentAccount
from apps.payments.accounting.constants import ReservationAction
from apps.payments.choices import TipoDetallePago


class PrepaidLimit:
    def __init__(self, payment, saved_advances, offer):
        self.payment = payment
        self.saved_advances = saved_advances
        self.offer = offer

    def paid_after(self, changes):
        touched = {change["row"].pk for change in changes if change["row"]}
        paid = PaymentAccount(self.payment).credit() if self.payment else 0
        paid -= sum(row.monto_pago for row in self.saved_advances if row.pk in touched)
        return paid + sum(change["amount"] for change in changes if not change["remove"])

    def saved_discounts(self):
        saved = self.offer.saved
        return bool(saved) and saved.tipo_detalle == TipoDetallePago.RESERVA_DESCONTABLE

    def reservation_delta(self, reservation):
        action = reservation.get("action")
        if action == ReservationAction.CREATE and self.offer.discounts():
            return reservation["amount"]
        if action == ReservationAction.REMOVE and self.saved_discounts():
            return -self.offer.saved.monto_pago
        return 0

    def reservation_counts(self, reservation):
        action = reservation.get("action")
        if action == ReservationAction.CREATE:
            return self.offer.discounts()
        return self.saved_discounts() and action != ReservationAction.REMOVE

    def keeps_advances(self, changes):
        removed = {change["row"].pk for change in changes if change["remove"]}
        kept = [row for row in self.saved_advances if row.pk not in removed]
        return bool(kept) or any(change["row"] is None for change in changes)

    def check(self, lines, advances, reservation):
        paid = self.paid_after(advances) + self.reservation_delta(reservation)
        total = AppointmentServices.total(lines)
        if paid <= total:
            return None
        amounts = {"paid": Money.format(paid), "total": Money.format(total)}
        if not self.reservation_counts(reservation):
            return AppointmentRuleError(
                ADVANCES_TOO_HIGH.format(**amounts), AdvanceChanges.FIELD
            )
        if self.keeps_advances(advances):
            return AppointmentRuleError(
                RESERVATION_TOO_HIGH.format(**amounts), AdvanceChanges.FIELD
            )
        return AppointmentRuleError(
            RESERVATION_TOO_HIGH.format(**amounts), ReservationChange.FIELD
        )
