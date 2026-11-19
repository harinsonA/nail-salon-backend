from rest_framework import serializers

from apps.payments.accounting.account import PaymentAccount
from apps.payments.choices import EstadoPago


class AppointmentPaymentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    estado_pago = serializers.ChoiceField(choices=EstadoPago.CHOICES)
    total = serializers.IntegerField()
    paid = serializers.IntegerField()
    pending = serializers.IntegerField()

    def to_representation(self, payment):
        account = PaymentAccount(payment, payment.detalles_pago.all())
        return super().to_representation(
            {
                "id": payment.pk,
                "estado_pago": payment.estado_pago,
                "total": account.appointment_total(),
                "paid": account.appointment_paid(),
                "pending": account.balance(),
            }
        )
