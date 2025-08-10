from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from ..models.servicio import Servicio
from ..serializers.servicio_serializer import ServicioSerializer, ServicioListSerializer


class ServicioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar servicios
    """

    queryset = Servicio.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["activo", "categoria"]
    search_fields = ["nombre_servicio", "descripcion", "categoria"]
    ordering_fields = ["nombre_servicio", "precio", "fecha_creacion"]
    ordering = ["nombre_servicio"]

    def get_serializer_class(self):
        """
        Retornar el serializer apropiado según la acción
        """
        if self.action == "list":
            return ServicioListSerializer
        return ServicioSerializer

    def get_queryset(self):
        """
        Filtrar servicios según parámetros de consulta
        """
        queryset = Servicio.objects.all()

        # Filtro por estado activo
        activo = self.request.query_params.get("activo", None)
        if activo is not None:
            queryset = queryset.filter(activo=activo.lower() == "true")

        # Filtro por categoría
        categoria = self.request.query_params.get("categoria", None)
        if categoria is not None:
            queryset = queryset.filter(categoria__icontains=categoria)

        return queryset

    def update(self, request, *args, **kwargs):
        """
        Actualizar servicio con validaciones adicionales
        """
        instance = self.get_object()

        # Validar que no se pueda desactivar un servicio si tiene citas activas
        nuevo_activo = request.data.get("activo")
        if nuevo_activo is False and instance.activo:
            # Verificar si tiene citas programadas o confirmadas
            from apps.appointments.models.detalle_cita import DetalleCita

            citas_activas = DetalleCita.objects.filter(
                servicio=instance,
                cita__estado__in=["programada", "confirmada", "en_proceso"],
            ).exists()

            if citas_activas:
                return Response(
                    {
                        "error": "No se puede desactivar un servicio que tiene citas activas"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Eliminar servicio con validaciones
        """
        instance = self.get_object()

        # Verificar si tiene detalles de cita asociados
        from apps.appointments.models.detalle_cita import DetalleCita

        tiene_citas = DetalleCita.objects.filter(servicio=instance).exists()

        if tiene_citas:
            return Response(
                {"error": "No se puede eliminar un servicio que tiene citas asociadas"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(request, *args, **kwargs)
