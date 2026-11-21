from rest_framework import serializers

from .appointment_advance import AppointmentAdvanceSerializer
from .appointment_line import AppointmentLineSerializer
from .appointment_reservation import AppointmentReservationSerializer
from .appointment_summary import AppointmentSummarySerializer


class AppointmentFieldsSerializer(serializers.Serializer):
    cliente_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    asignado_a_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    fecha_agenda = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    hora_agenda = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    observaciones = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    services = AppointmentLineSerializer(many=True, required=False)
    advances = AppointmentAdvanceSerializer(many=True, required=False)
    reservation = AppointmentReservationSerializer(required=False, allow_null=True)
    summary = AppointmentSummarySerializer()
