from rest_framework import serializers

from .detail_badge import DetailBadgeSerializer
from .detail_payment_line import DetailPaymentLineSerializer
from .detail_person import DetailPersonSerializer
from .detail_reservation import DetailReservationSerializer
from .detail_row import DetailRowSerializer


class DetailPaymentSerializer(serializers.Serializer):
    badge = DetailBadgeSerializer(allow_null=True)
    rows = DetailRowSerializer(many=True)
    first = DetailPersonSerializer(allow_null=True)
    payments = DetailPaymentLineSerializer(many=True, allow_null=True)
    reservations = DetailReservationSerializer(many=True)
    can_pay = serializers.BooleanField()
