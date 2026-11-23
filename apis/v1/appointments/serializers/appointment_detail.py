from rest_framework import serializers

from .detail_payment import DetailPaymentSerializer
from .detail_person import DetailPersonSerializer
from .detail_status import DetailStatusSerializer
from .detail_team import DetailTeamSerializer


class AppointmentDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = DetailStatusSerializer()
    team = DetailTeamSerializer()
    payment = DetailPaymentSerializer()
    created = DetailPersonSerializer()
