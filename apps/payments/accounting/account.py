from decimal import Decimal

from apps.payments.accounting.constants import (
    PREPAID_TYPES,
    RETAINED_STATES,
    SERVICE_PREPAID_TYPES,
    ZERO,
)
from apps.payments.accounting.detail import PaymentDetail


class PaymentAccount:
    def __init__(self, payment, details=None):
        self.payment = payment
        self.details = (
            list(details) if details is not None else list(payment.detalles_pago.all())
        )

    def paid(self):
        total = ZERO
        for detail in self.details:
            if PaymentDetail.is_refund(detail):
                total -= detail.monto_pago
            else:
                total += detail.monto_pago
        return total

    def refunded(self, detail):
        return sum(
            (
                item.monto_pago
                for item in self.details
                if PaymentDetail.is_refund(item) and item.detalle_devuelto_id == detail.pk
            ),
            ZERO,
        )

    def refunded_total(self):
        return sum(
            (item.monto_pago for item in self.details if PaymentDetail.is_refund(item)),
            ZERO,
        )

    def refundable(self, detail):
        if PaymentDetail.kind(detail) not in PREPAID_TYPES:
            return ZERO
        return max(ZERO, detail.monto_pago - self.refunded(detail))

    def retained(self):
        return sum(
            (
                self.refundable(detail)
                for detail in self.details
                if PaymentDetail.status(detail) in RETAINED_STATES
            ),
            ZERO,
        )

    def reservation(self):
        return sum(
            (
                self.refundable(detail)
                for detail in self.details
                if PaymentDetail.is_reservation(detail)
            ),
            ZERO,
        )

    def applied(self):
        return self.paid() - self.reservation()

    def service_retained(self):
        return sum(
            (
                self.refundable(detail)
                for detail in self.details
                if PaymentDetail.kind(detail) in SERVICE_PREPAID_TYPES
                and PaymentDetail.status(detail) in RETAINED_STATES
            ),
            ZERO,
        )

    def charges(self):
        return self.service_retained()

    def credit(self):
        return self.applied() - self.charges()

    def total(self, services_amount, cancelled=False):
        return (ZERO if cancelled else Decimal(services_amount)) + self.charges()

    def balance(self):
        return max(ZERO, self.payment.monto_total_cita - self.applied())

    def is_settled(self):
        return self.applied() >= self.payment.monto_total_cita

    def appointment_total(self):
        return self.payment.monto_total_cita - self.service_retained()

    def appointment_paid(self):
        return self.applied() - self.service_retained()

    def appointment_payments(self):
        return [
            detail for detail in self.details if PaymentDetail.is_appointment_payment(detail)
        ]
