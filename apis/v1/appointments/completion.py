from apps.appointments.engine import AppointmentCompletion, AppointmentRuleError
from apps.appointments.panel import person_name

"""========================================================================="""
# region ........ Builders


class AppointmentCompletionCard:
    def __init__(self, appointment, viewer):
        self.appointment = appointment
        self.viewer = viewer
        self.completion = AppointmentCompletion(appointment)

    def blocked(self):
        try:
            self.completion.clean_amount(True, None)
        except AppointmentRuleError as error:
            return error.message
        return None

    def reservation(self):
        card = self.completion.reservation_card()
        if card is None:
            return None
        row = self.completion.reservation_row()
        return {"label": card["label"], "amount": int(row.monto_pago), "discounts": card["discounts"]}

    def build(self):
        completion = self.completion
        remaining = completion.remaining
        return {
            "id": self.appointment.pk,
            "services_total": int(completion.services_total),
            "prepaid": int(completion.prepaid),
            "remaining": int(remaining),
            "full_payment_label": completion.full_payment_label(),
            "settled_hint": None if remaining else completion.settled_hint(),
            "blocked": self.blocked(),
            "credit": [
                {"label": label, "amount": int(amount)} for label, amount in completion.credit_parts()
            ],
            "reservation": self.reservation(),
            "attended_by": person_name(self.viewer, self.viewer),
        }


class AppointmentCompletionData:
    API_FIELDS = {
        "down_payment": "monto_pago",
        "payment_method": "metodo_pago",
        "payment_reference": "referencia_pago",
        "observations": "notas_detalle",
        "__all__": "non_field_errors",
    }

    @staticmethod
    def for_form(changes):
        amount = changes.get("monto_pago")
        return {
            "full_payment": "on" if changes["full_payment"] else "",
            "down_payment": "" if amount is None else str(amount),
            "payment_method": changes.get("metodo_pago") or "",
            "payment_reference": changes.get("referencia_pago") or "",
            "observations": changes.get("notas_detalle") or "",
        }

    @classmethod
    def errors(cls, form):
        return {cls.API_FIELDS.get(name, name): messages for name, messages in form.errors.items()}


# endregion
"""========================================================================="""
