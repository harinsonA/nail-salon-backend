from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response

from apis.common.views import ApiView
from apis.v1.sync.serializers import ChangesSerializer
from apps.sync import SyncChanges


class ChangesView(ApiView):
    http_method_names = ["get"]

    @extend_schema(
        summary="Cambios para la copia local",
        description=(
            "Sin marca, o con una marca vieja o inválida, entrega todo (full). Con marca, solo lo que "
            "cambió desde ella, los días que entraron a la ventana y los borrados."
        ),
        parameters=[OpenApiParameter("since", OpenApiTypes.DATETIME, required=False)],
        responses=ChangesSerializer,
    )
    def get(self, request, *args, **kwargs):
        changes = SyncChanges(request.user, request.query_params.get("since"))
        return Response(ChangesSerializer(changes.build()).data)
