from drf_spectacular.utils import extend_schema

from apis.v1.catalogs.serializers import PhonePrefixSerializer
from apis.v1.catalogs.views.base import CatalogView
from apps.common.utils.countries.constants import COUNTRIES, phone_prefix_label


class PhonePrefixesView(CatalogView):
    slug = "phone-prefixes"
    serializer_class = PhonePrefixSerializer

    def items(self):
        return [
            {
                "value": country.PHONE_PREFIX,
                "label": phone_prefix_label(country),
                "country": country.COUNTRY_CODE,
            }
            for country in COUNTRIES
        ]

    @extend_schema(
        summary="Prefijos de teléfono",
        description="Prefijo de cada país, con la misma etiqueta de la web.",
        responses=PhonePrefixSerializer(many=True),
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
