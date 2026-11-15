from apps.appointments.engine.errors import AppointmentRuleError
from apps.appointments.engine.messages import (
    ADVANCE_AMOUNT_REQUIRED,
    ADVANCE_LOCKED_ROLE,
    ADVANCES_INVALID,
    REFERENCE_MAX_LENGTH,
)
from apps.payments.accounting import PaymentLabels


class AdvanceChanges:
    FIELD = "advances"

    def __init__(self, saved, can_change_saved):
        self.saved = saved
        self.can_change_saved = can_change_saved

    @classmethod
    def error(cls, message):
        return AppointmentRuleError(message, cls.FIELD)

    def clean(self, advances):
        if not isinstance(advances, list):
            raise self.error(ADVANCES_INVALID)
        saved = {row.pk: row for row in self.saved}
        changes = [self.clean_advance(advance, saved) for advance in advances]
        touched = [change["row"].pk for change in changes if change["row"]]
        if len(touched) != len(set(touched)):
            raise self.error(ADVANCES_INVALID)
        return changes

    def saved_row(self, advance, saved):
        if advance.get("id") is None:
            return None
        try:
            row = saved.get(int(advance["id"]))
        except (TypeError, ValueError) as error:
            raise self.error(ADVANCES_INVALID) from error
        if row is None:
            raise self.error(ADVANCES_INVALID)
        if not self.can_change_saved:
            raise self.error(ADVANCE_LOCKED_ROLE)
        return row

    def clean_advance(self, advance, saved):
        if not isinstance(advance, dict):
            raise self.error(ADVANCES_INVALID)
        row = self.saved_row(advance, saved)
        if row and advance.get("quitar") is True:
            return {
                "row": row,
                "remove": True,
                "amount": 0,
                "method": row.metodo_pago,
                "reference": "",
            }
        amount = advance.get("monto")
        method = advance.get("metodo")
        reference = advance.get("referencia") or ""
        if amount in (None, "", 0):
            raise self.error(ADVANCE_AMOUNT_REQUIRED)
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
            raise self.error(ADVANCES_INVALID)
        if method not in PaymentLabels.METHODS or not isinstance(reference, str):
            raise self.error(ADVANCES_INVALID)
        reference = reference.strip()
        if len(reference) > REFERENCE_MAX_LENGTH:
            raise self.error(ADVANCES_INVALID)
        return {
            "row": row,
            "remove": False,
            "amount": amount,
            "method": method,
            "reference": reference,
        }
