from rest_framework.response import Response

from apis.common.views import ApiView


class CatalogView(ApiView):
    http_method_names = ["get"]
    slug = None
    serializer_class = None

    @classmethod
    def route(cls):
        return f"catalogs/{cls.slug}/"

    @classmethod
    def route_name(cls):
        return f"api_catalogs_{cls.slug.replace('-', '_')}"

    def items(self):
        raise NotImplementedError

    def get(self, request, *args, **kwargs):
        return Response(self.serializer_class(self.items(), many=True).data)
