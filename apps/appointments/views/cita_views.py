from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import timedelta

from ..models.cita import Cita
from ..serializers.cita_serializer import CitaSerializer, CitaListSerializer


class CitaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar citas
    """

    queryset = Cita.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["estado_cita", "cliente"]
    search_fields = [
        "cliente__nombre",
        "cliente__apellido",
        "cliente__telefono",
        "observaciones",
    ]
    ordering_fields = ["fecha_hora_cita", "fecha_creacion", "monto_total"]
    ordering = ["-fecha_hora_cita"]

    def get_serializer_class(self):
        """
        Retornar el serializer apropiado según la acción
        """
        if self.action == "list":
            return CitaListSerializer
        return CitaSerializer

    def get_queryset(self):
        """
        Filtrar citas según parámetros de consulta
        """
        queryset = Cita.objects.select_related(
            "cliente", "creado_por"
        ).prefetch_related("detalles__servicio")

        # Filtro por estado
        estado = self.request.query_params.get("estado", None)
        if estado:
            queryset = queryset.filter(estado_cita=estado.upper())

        # Filtro por rango de fechas
        fecha_desde = self.request.query_params.get("fecha_desde", None)
        fecha_hasta = self.request.query_params.get("fecha_hasta", None)

        if fecha_desde and fecha_hasta:
            queryset = queryset.filter(
                fecha_hora_cita__date__range=[fecha_desde, fecha_hasta]
            )
        elif fecha_desde:
            queryset = queryset.filter(fecha_hora_cita__date__gte=fecha_desde)
        elif fecha_hasta:
            queryset = queryset.filter(fecha_hora_cita__date__lte=fecha_hasta)

        # Filtro por cliente específico
        cliente_id = self.request.query_params.get("cliente_id", None)
        if cliente_id:
            queryset = queryset.filter(cliente_id=cliente_id)

        return queryset

    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        """
        Confirmar una cita
        """
        cita = self.get_object()

        if cita.estado_cita != "PENDIENTE":
            return Response(
                {"error": "Solo se pueden confirmar citas pendientes"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cita.estado_cita = "CONFIRMADA"
        cita.save()

        return Response(
            {
                "mensaje": "Cita confirmada correctamente",
                "cita_id": cita.cita_id,
                "estado": cita.estado_cita,
            }
        )

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        """
        Cancelar una cita
        """
        cita = self.get_object()
        motivo = request.data.get("motivo", "Sin motivo especificado")

        if cita.estado_cita in ["COMPLETADA", "CANCELADA"]:
            return Response(
                {"error": "No se puede cancelar una cita completada o ya cancelada"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cita.estado_cita = "CANCELADA"
        cita.observaciones = f"{cita.observaciones or ''}\nCancelada: {motivo}".strip()
        cita.save()

        return Response(
            {
                "mensaje": "Cita cancelada correctamente",
                "cita_id": cita.cita_id,
                "estado": cita.estado_cita,
                "motivo": motivo,
            }
        )

    @action(detail=True, methods=["post"])
    def completar(self, request, pk=None):
        """
        Completar una cita
        """
        cita = self.get_object()

        if cita.estado_cita != "CONFIRMADA":
            return Response(
                {"error": "Solo se pueden completar citas confirmadas"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verificar que la cita tenga al menos un servicio
        if not cita.detalles.exists():
            return Response(
                {"error": "No se puede completar una cita sin servicios"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cita.estado_cita = "COMPLETADA"
        cita.save()

        return Response(
            {
                "mensaje": "Cita completada correctamente",
                "cita_id": cita.cita_id,
                "estado": cita.estado_cita,
                "monto_total": cita.monto_total,
            }
        )

    @action(detail=True, methods=["get"])
    def servicios(self, request, pk=None):
        """
        Obtener los servicios de una cita específica
        """
        cita = self.get_object()
        detalles = cita.detalles.all()

        from ..serializers.detalle_cita_serializer import DetalleCitaSerializer

        serializer = DetalleCitaSerializer(detalles, many=True)

        return Response(
            {
                "cita_id": cita.cita_id,
                "servicios": serializer.data,
                "total_servicios": detalles.count(),
                "monto_total": cita.monto_total,
            }
        )

    @action(detail=False, methods=["get"])
    def proximas(self, request):
        """
        Obtener las próximas citas (siguientes 7 días)
        """
        fecha_limite = timezone.now() + timedelta(days=7)
        citas = self.get_queryset().filter(
            fecha_hora_cita__gte=timezone.now(),
            fecha_hora_cita__lte=fecha_limite,
            estado_cita__in=["PENDIENTE", "CONFIRMADA"],
        )

        serializer = CitaListSerializer(citas, many=True)
        return Response({"proximas_citas": serializer.data, "total": citas.count()})

    @action(detail=False, methods=["get"])
    def del_dia(self, request):
        """
        Obtener las citas del día actual
        """
        hoy = timezone.now().date()
        citas = self.get_queryset().filter(fecha_hora_cita__date=hoy)

        serializer = CitaListSerializer(citas, many=True)
        return Response(
            {"citas_del_dia": serializer.data, "total": citas.count(), "fecha": hoy}
        )

    def perform_create(self, serializer):
        """
        Personalizar la creación de citas
        """
        serializer.save()

    def perform_update(self, serializer):
        """
        Personalizar la actualización de citas
        """
        instance = self.get_object()

        # Validar que no se modifiquen citas completadas o canceladas
        if instance.estado_cita in ["COMPLETADA", "CANCELADA"]:
            raise ValidationError(
                f"No se puede modificar una cita con estado {instance.estado_cita}."
            )

        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """
        Personalizar la eliminación de citas
        """
        cita = self.get_object()

        # Solo NO permitir eliminar citas completadas
        if cita.estado_cita == "COMPLETADA":
            return Response(
                {"error": "No se puede eliminar una cita completada"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(request, *args, **kwargs)
