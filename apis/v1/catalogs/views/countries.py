from drf_spectacular.utils import extend_schema

from apis.v1.catalogs.serializers import CountrySerializer
from apis.v1.catalogs.views.base import CatalogView
from apps.common.utils.countries.constants import Country
from apps.common.utils.countries.dispatcher import CountryDispatcher


class CountriesView(CatalogView):
    slug = "countries"
    serializer_class = CountrySerializer

    def items(self):
        return [
            {
                "code": code,
                "name": name,
                "identifier_types": [
                    {"value": value, "label": label}
                    for value, label in CountryDispatcher.identifier_types(code)
                ],
            }
            for code, name in Country.choices
        ]

    @extend_schema(
        summary="Países",
        description="Cada país con sus tipos de identificador nacional, los mismos de la web.",
        responses=CountrySerializer(many=True),
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
