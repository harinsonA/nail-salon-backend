from apps.common.utils.currency import Money
from apps.common.utils.dates import format_date_time
from apps.common.utils.text import user_display_name
from apps.payments.accounting.account import PaymentAccount
from apps.payments.accounting.detail import PaymentDetail
from apps.payments.accounting.labels import PaymentLabels


class AppointmentPaymentSummary:
    def __init__(self, payment, details=None):
        self.payment = payment
        self.account = PaymentAccount(payment, details)

    @classmethod
    def for_payment(cls, payment):
        return cls(
            payment,
            payment.detalles_pago.select_related("registrado_por").order_by("fecha_pago", "pk"),
        )

    def total(self):
        return self.account.appointment_total()

    def paid(self):
        return self.account.appointment_paid()

    def pending(self):
        return self.account.balance()

    def payments(self):
        return self.account.appointment_payments()

    def credit_parts(self):
        reservation = self.account.reservation_credit()
        parts = (("Reserva", reservation), ("Anticipo", self.account.credit() - reservation))
        return [(label, amount) for label, amount in parts if amount]

    def reservation_lines(self):
        return [
            {
                "amount": Money.format(detail.monto_pago),
                "status": PaymentLabels.reservation_status(PaymentDetail.status(detail)),
            }
            for detail in self.account.separate_reservations()
        ]

    def rows(self):
        return [
            {
                "when": format_date_time(detail.fecha_pago),
                "kind": PaymentLabels.kind(detail.tipo_detalle),
                "method": PaymentLabels.method(detail.metodo_pago),
                "by": user_display_name(detail.registrado_por) if detail.registrado_por else "—",
                "amount": Money.format(detail.monto_pago),
            }
            for detail in self.payments()
        ]
