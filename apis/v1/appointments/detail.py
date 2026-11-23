from apps.appointments.panel import AppointmentPanel

"""========================================================================="""
# region ........ Builders


class AppointmentDetail:
    def __init__(self, appointment, viewer):
        self.appointment = appointment
        self.context = AppointmentPanel(appointment, viewer).context()

    def payment(self):
        payment = self.context["payment"]
        badge = payment.get("badge")
        return {
            "badge": badge,
            "rows": [{"debt": False, **row} for row in payment["rows"]],
            "first": payment.get("first"),
            "payments": payment.get("payments") if badge else None,
            "reservations": payment.get("reservations", []),
            "can_pay": bool(payment.get("pay_url")),
        }

    def build(self):
        context = self.context
        return {
            "id": self.appointment.pk,
            "status": context["status"],
            "team": context["team"],
            "payment": self.payment(),
            "created": {"name": context["created_by"] or "—", "when": context["created_at"]},
        }


# endregion
"""========================================================================="""
