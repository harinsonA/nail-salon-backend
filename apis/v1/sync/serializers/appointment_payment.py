from rest_framework import serializers

from apps.payments.accounting import AppointmentLedger
from apps.payments.accounting.account import PaymentAccount
from apps.payments.choices import EstadoPago

from .appointment_prepaid import AppointmentPrepaidSerializer


class AppointmentPaymentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    estado_pago = serializers.ChoiceField(choices=EstadoPago.CHOICES)
    total = serializers.IntegerField()
    paid = serializers.IntegerField()
    pending = serializers.IntegerField()
    prepaid = AppointmentPrepaidSerializer(many=True)

    def to_representation(self, payment):
        details = payment.detalles_pago.all()
        account = PaymentAccount(payment, details)
        return super().to_representation(
            {
                "id": payment.pk,
                "estado_pago": payment.estado_pago,
                "total": account.appointment_total(),
                "paid": account.appointment_paid(),
                "pending": account.balance(),
                "prepaid": AppointmentLedger.open_prepaid_of(details),
            }
        )
