from django.core.exceptions import ObjectDoesNotExist
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.appointments.models import Cita

from .appointment_payment import AppointmentPaymentSerializer
from .appointment_service import AppointmentServiceSerializer


class AppointmentSerializer(serializers.ModelSerializer):
    services = AppointmentServiceSerializer(source="detalles", many=True)
    payment = serializers.SerializerMethodField()

    class Meta:
        model = Cita
        fields = [
            "id",
            "codigo_app",
            "fecha_agenda",
            "hora_agenda",
            "estado",
            "observaciones",
            "cliente_id",
            "asignado_a_id",
            "creado_por_id",
            "modified",
            "services",
            "payment",
        ]

    @extend_schema_field(AppointmentPaymentSerializer(allow_null=True))
    def get_payment(self, appointment):
        try:
            payment = appointment.pago
        except ObjectDoesNotExist:
            return None
        return AppointmentPaymentSerializer(payment).data
