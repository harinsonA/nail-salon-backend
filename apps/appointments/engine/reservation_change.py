from apps.appointments.engine.errors import AppointmentRuleError
from apps.appointments.engine.messages import (
    REFERENCE_MAX_LENGTH,
    RESERVATION_INVALID,
    RESERVATION_LOCKED_ROLE,
)
from apps.payments.accounting import PaymentLabels, PaymentRowFactory
from apps.payments.accounting.constants import ReservationAction


class ReservationChange:
    FIELD = "reservation"

    def __init__(self, offer, can_change_saved):
        self.offer = offer
        self.can_change_saved = can_change_saved

    @classmethod
    def error(cls, message):
        return AppointmentRuleError(message, cls.FIELD)

    def clean(self, data):
        offer = self.offer
        if not offer.available or data is None:
            return {}
        if not isinstance(data, dict) or not isinstance(data.get("activa"), bool):
            raise self.error(RESERVATION_INVALID)
        saved = offer.saved
        if not data["activa"]:
            return self.saved_change(ReservationAction.REMOVE) if saved else {}
        method = data.get("metodo")
        reference = data.get("referencia") or ""
        if method not in PaymentLabels.METHODS or not isinstance(reference, str):
            raise self.error(RESERVATION_INVALID)
        reference = reference.strip()
        if len(reference) > REFERENCE_MAX_LENGTH:
            raise self.error(RESERVATION_INVALID)
        change = {
            "row": saved,
            "amount": offer.amount(),
            "kind": offer.kind(),
            "method": method,
            "reference": reference,
        }
        if not saved:
            return {**change, "action": ReservationAction.CREATE}
        unchanged = saved.metodo_pago == method and (
            saved.referencia_pago or None
        ) == PaymentRowFactory.reference(method, reference)
        if unchanged:
            return {}
        return self.saved_change(ReservationAction.UPDATE, change)

    def saved_change(self, action, change=None):
        if not self.can_change_saved:
            raise self.error(RESERVATION_LOCKED_ROLE)
        return {**(change or {"row": self.offer.saved}), "action": action}
