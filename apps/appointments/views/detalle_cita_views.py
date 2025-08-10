from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from ..models.detalle_cita import DetalleCita
from ..serializers.detalle_cita_serializer import DetalleCitaSerializer


class DetalleCitaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar detalles de citas
    """

    queryset = DetalleCita.objects.all()
    serializer_class = DetalleCitaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["cita", "servicio", "cita__estado_cita"]
    search_fields = ["servicio__nombre_servicio", "notas_detalle"]
    ordering_fields = ["fecha_creacion", "precio_acordado", "cantidad_servicios"]
    ordering = ["-fecha_creacion"]

    def get_queryset(self):
        """
        Filtrar detalles según parámetros de consulta
        """
        queryset = DetalleCita.objects.select_related(
            "cita", "servicio", "cita__cliente"
        )

        # Filtro por cita específica
        cita_id = self.request.query_params.get("cita_id", None)
        if cita_id:
            queryset = queryset.filter(cita_id=cita_id)

        return queryset

    @action(detail=True, methods=["post"])
    def aplicar_descuento(self, request, pk=None):
        """
        Aplicar descuento a un detalle específico
        """
        detalle = self.get_object()
        descuento = request.data.get("descuento", 0)

        try:
            descuento = float(descuento)
            if 0 <= descuento <= 100:
                detalle.descuento = descuento
                detalle.save()

                serializer = self.get_serializer(detalle)
                return Response(
                    {
                        "mensaje": f"Descuento del {descuento}% aplicado correctamente",
                        "detalle": serializer.data,
                    }
                )
            else:
                return Response(
                    {"error": "El descuento debe estar entre 0 y 100"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except (ValueError, TypeError):
            return Response(
                {"error": "Descuento inválido"}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"])
    def actualizar_cantidad(self, request, pk=None):
        """
        Actualizar la cantidad de servicios
        """
        detalle = self.get_object()
        cantidad = request.data.get("cantidad_servicios", 1)

        try:
            cantidad = int(cantidad)
            if cantidad > 0:
                detalle.cantidad_servicios = cantidad
                detalle.save()

                serializer = self.get_serializer(detalle)
                return Response(
                    {
                        "mensaje": f"Cantidad actualizada a {cantidad}",
                        "detalle": serializer.data,
                    }
                )
            else:
                return Response(
                    {"error": "La cantidad debe ser mayor a 0"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except (ValueError, TypeError):
            return Response(
                {"error": "Cantidad inválida"}, status=status.HTTP_400_BAD_REQUEST
            )

    def perform_create(self, serializer):
        """
        Personalizar la creación de detalles de cita
        """
        serializer.save()

    def perform_update(self, serializer):
        """
        Personalizar la actualización de detalles de cita
        """
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """
        Personalizar la eliminación de detalles
        """
        detalle = self.get_object()

        # Verificar que la cita pueda ser modificada
        if not detalle.cita.puede_ser_modificada():
            return Response(
                {
                    "error": "No se puede eliminar servicios de una cita completada o cancelada"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(request, *args, **kwargs)
