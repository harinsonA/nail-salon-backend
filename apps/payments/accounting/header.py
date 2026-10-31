from datetime import datetime

from django.db.models import Sum
from django.utils import timezone

from apps.payments.accounting.account import PaymentAccount
from apps.payments.accounting.constants import ZERO


class PaymentHeader:
    def __init__(self, appointment):
        self.appointment = appointment

    def moment(self):
        return timezone.make_aware(
            datetime.combine(self.appointment.fecha_agenda, self.appointment.hora_agenda)
        )

    def services_amounts(self):
        totals = self.appointment.detalles.aggregate(
            total=Sum("precio_acordado"), discounts=Sum("descuento")
        )
        return totals["total"] or ZERO, totals["discounts"] or ZERO

    def services_total(self):
        return self.services_amounts()[0]

    def fill(self, payment, cancelled=False, details=None):
        services_total, discounts = self.services_amounts()
        if details is None and not payment.pk:
            details = []
        payment.cliente_nombre = self.appointment.cliente.nombre_completo
        payment.fecha_cita = self.moment()
        payment.descuento_total = discounts
        payment.monto_total_cita = PaymentAccount(payment, details).total(
            services_total, cancelled=cancelled
        )
        return payment
