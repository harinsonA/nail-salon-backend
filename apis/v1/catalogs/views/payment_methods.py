from drf_spectacular.utils import extend_schema

from apis.v1.catalogs.serializers import ChoiceSerializer
from apis.v1.catalogs.views.base import CatalogView
from apps.payments.choices import MetodoPago


class PaymentMethodsView(CatalogView):
    slug = "payment-methods"
    serializer_class = ChoiceSerializer

    def items(self):
        return [{"value": value, "label": label} for value, label in MetodoPago.CHOICES]

    @extend_schema(
        summary="Métodos de pago",
        description="Los métodos de pago de la web.",
        responses=ChoiceSerializer(many=True),
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
