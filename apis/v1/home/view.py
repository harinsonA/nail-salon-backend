from drf_spectacular.utils import extend_schema
from rest_framework.response import Response

from apis.common.views import ApiView
from apis.v1.home.serializers import HomeSerializer
from apps.home import HomeSummary


class HomeView(ApiView):
    http_method_names = ["get"]

    @extend_schema(
        summary="Números de Inicio",
        description=(
            "Citas del mes (atendidas y pendientes, sin canceladas). Deudores e ingresos del mes "
            "actual y el anterior solo para quien los ve en la web; si no, llegan vacíos."
        ),
        responses=HomeSerializer,
    )
    def get(self, request, *args, **kwargs):
        return Response(HomeSerializer(HomeSummary(request.user, request.tenant).build()).data)
