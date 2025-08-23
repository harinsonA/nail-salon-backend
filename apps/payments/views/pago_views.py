from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum
from decimal import Decimal

from ..models.pago import Pago
from ..serializers.pago_serializer import (
    PagoSerializer,
    PagoListSerializer,
    PagoCreateSerializer,
)


class PagoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar pagos
    """

    queryset = Pago.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = [
        "estado_pago",
        "metodo_pago",
        "cita",
        "cita__cliente",
    ]
    search_fields = [
        "referencia_pago",
        "notas_pago",
        "cita__cliente__nombre",
        "cita__cliente__apellido",
    ]
    ordering_fields = ["fecha_pago", "monto_total", "fecha_creacion", "estado_pago"]
    ordering = ["-fecha_pago"]

    def get_serializer_class(self):
        """
        Retornar el serializer apropiado según la acción
        """
        if self.action == "list":
            return PagoListSerializer
        elif self.action == "create":
            return PagoCreateSerializer
        return PagoSerializer

    def get_queryset(self):
        """
        Filtrar pagos según parámetros de consulta con optimizaciones
        """
        queryset = Pago.objects.select_related(
            "cita", "cita__cliente", "creado_por"
        ).all()

        # Filtro por estado de pago
        estado_pago = self.request.query_params.get("estado_pago", None)
        if estado_pago:
            queryset = queryset.filter(estado_pago=estado_pago)

        # Filtro por método de pago
        metodo_pago = self.request.query_params.get("metodo_pago", None)
        if metodo_pago:
            queryset = queryset.filter(metodo_pago=metodo_pago)

        # Filtro por cita específica
        cita_id = self.request.query_params.get("cita", None)
        if cita_id:
            queryset = queryset.filter(cita__cita_id=cita_id)

        # Filtro por cliente
        cliente_id = self.request.query_params.get("cliente", None)
        if cliente_id:
            queryset = queryset.filter(cita__cliente__cliente_id=cliente_id)

        # Filtro por rango de fechas
        fecha_desde = self.request.query_params.get("fecha_desde", None)
        fecha_hasta = self.request.query_params.get("fecha_hasta", None)

        if fecha_desde:
            queryset = queryset.filter(fecha_pago__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_pago__lte=fecha_hasta)

        # Filtro por rango de montos
        monto_minimo = self.request.query_params.get("monto_minimo", None)
        monto_maximo = self.request.query_params.get("monto_maximo", None)

        if monto_minimo:
            try:
                queryset = queryset.filter(monto_total__gte=Decimal(monto_minimo))
            except (ValueError, TypeError):
                pass
        if monto_maximo:
            try:
                queryset = queryset.filter(monto_total__lte=Decimal(monto_maximo))
            except (ValueError, TypeError):
                pass

        return queryset

    @action(detail=True, methods=["post"])
    def marcar_pagado(self, request, pk=None):
        """
        Marcar un pago como pagado
        """
        pago = self.get_object()

        if pago.estado_pago == "pagado":
            return Response(
                {"error": "El pago ya está marcado como pagado"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pago.marcar_como_pagado()

        return Response(
            {
                "mensaje": "Pago marcado como pagado correctamente",
                "pago_id": pago.pago_id,
                "estado_anterior": request.data.get("estado_anterior", "pendiente"),
                "estado_actual": pago.estado_pago,
            }
        )

    @action(detail=True, methods=["post"])
    def reembolsar(self, request, pk=None):
        """
        Procesar reembolso de un pago
        """
        pago = self.get_object()

        if pago.estado_pago != "pagado":
            return Response(
                {
                    "error": "Solo se pueden reembolsar pagos que estén en estado 'pagado'"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Actualizar estado a reembolsado
        pago.estado_pago = "reembolsado"
        pago.save()

        # Agregar nota de reembolso si se proporciona
        motivo_reembolso = request.data.get("motivo", "")
        if motivo_reembolso:
            nota_anterior = pago.notas_pago or ""
            pago.notas_pago = f"{nota_anterior}\n[REEMBOLSO] {motivo_reembolso}".strip()
            pago.save()

        return Response(
            {
                "mensaje": "Reembolso procesado correctamente",
                "pago_id": pago.pago_id,
                "monto_reembolsado": str(pago.monto_total),
                "motivo": motivo_reembolso,
            }
        )

    @action(detail=False, methods=["get"])
    def estadisticas(self, request):
        """
        Obtener estadísticas de pagos
        """
        queryset = self.get_queryset()

        # Estadísticas básicas
        total_pagos = queryset.count()
        total_monto = queryset.aggregate(total=Sum("monto_total"))["total"] or 0

        # Por estado
        por_estado = {}
        for estado in ["pendiente", "pagado", "reembolsado"]:
            estado_qs = queryset.filter(estado_pago=estado)
            por_estado[estado] = {
                "cantidad": estado_qs.count(),
                "monto_total": str(
                    estado_qs.aggregate(total=Sum("monto_total"))["total"] or 0
                ),
            }

        # Por método de pago
        por_metodo = {}
        for metodo in [
            "efectivo",
            "tarjeta_credito",
            "tarjeta_debito",
            "transferencia",
        ]:
            metodo_qs = queryset.filter(metodo_pago=metodo)
            por_metodo[metodo] = {
                "cantidad": metodo_qs.count(),
                "monto_total": str(
                    metodo_qs.aggregate(total=Sum("monto_total"))["total"] or 0
                ),
            }

        return Response(
            {
                "resumen": {
                    "total_pagos": total_pagos,
                    "monto_total": str(total_monto),
                    "promedio_pago": str(
                        total_monto / total_pagos if total_pagos > 0 else 0
                    ),
                },
                "por_estado": por_estado,
                "por_metodo": por_metodo,
            }
        )

    @action(detail=False, methods=["get"])
    def por_cita(self, request):
        """
        Obtener pagos agrupados por cita
        """
        cita_id = request.query_params.get("cita_id")
        if not cita_id:
            return Response(
                {"error": "Se requiere el parámetro cita_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pagos = self.get_queryset().filter(cita__cita_id=cita_id)
        serializer = self.get_serializer(pagos, many=True)

        # Calcular totales
        total_pagado = (
            pagos.filter(estado_pago="pagado").aggregate(total=Sum("monto_total"))[
                "total"
            ]
            or 0
        )

        total_pendiente = (
            pagos.filter(estado_pago="pendiente").aggregate(total=Sum("monto_total"))[
                "total"
            ]
            or 0
        )

        return Response(
            {
                "cita_id": cita_id,
                "pagos": serializer.data,
                "resumen": {
                    "total_pagos": pagos.count(),
                    "total_pagado": str(total_pagado),
                    "total_pendiente": str(total_pendiente),
                    "total_general": str(total_pagado + total_pendiente),
                },
            }
        )

    def perform_create(self, serializer):
        """
        Personalizar la creación de pagos
        """
        # El serializer ya maneja la asignación del usuario
        serializer.save()

    def create(self, request, *args, **kwargs):
        """
        Crear un pago y retornar la representación completa
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pago = serializer.save()

        # Usar PagoSerializer para la respuesta completa
        response_serializer = PagoSerializer(
            pago, context=self.get_serializer_context()
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        """
        Personalizar la actualización de pagos
        """
        # Validaciones adicionales en actualización si es necesario
        instance = serializer.save()

        # Si se marca como pagado, ejecutar lógica adicional
        if (
            instance.estado_pago == "pagado"
            and serializer.validated_data.get("estado_pago") == "pagado"
        ):
            # Lógica adicional al marcar como pagado si es necesario
            pass

    def perform_destroy(self, instance):
        """
        Personalizar la eliminación de pagos
        """
        # Verificar si el pago puede ser eliminado
        if instance.estado_pago == "pagado":
            # Podríamos permitir o no la eliminación de pagos pagados
            # Por ahora permitimos pero podríamos agregar validaciones
            pass

        instance.delete()
