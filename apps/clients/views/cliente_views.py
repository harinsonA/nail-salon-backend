from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from ..models.cliente import Cliente
from ..serializers.cliente_serializer import ClienteSerializer, ClienteListSerializer


class ClienteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar clientes
    """

    queryset = Cliente.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["activo", "fecha_registro"]
    search_fields = ["nombre", "apellido", "telefono", "email"]
    ordering_fields = ["fecha_registro", "nombre", "apellido"]
    ordering = ["-fecha_registro"]

    def get_serializer_class(self):
        """
        Retornar el serializer apropiado según la acción
        """
        if self.action == "list":
            return ClienteListSerializer
        return ClienteSerializer

    def get_queryset(self):
        """
        Filtrar clientes según parámetros de consulta
        """
        queryset = Cliente.objects.all()

        # Filtro por estado activo
        activo = self.request.query_params.get("activo", None)
        if activo is not None:
            queryset = queryset.filter(activo=activo.lower() == "true")

        return queryset

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        """
        Desactivar un cliente
        """
        cliente = self.get_object()
        cliente.activo = False
        cliente.save()
        return Response({"mensaje": "Cliente desactivado correctamente"})

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        """
        Activar un cliente
        """
        cliente = self.get_object()
        cliente.activo = True
        cliente.save()
        return Response({"mensaje": "Cliente activado correctamente"})

    @action(detail=True, methods=["get"])
    def citas(self, request, pk=None):
        """
        Obtener las citas de un cliente específico
        """
        # Esta funcionalidad se implementará cuando tengamos el modelo de Citas
        return Response(
            {"mensaje": "Funcionalidad pendiente: listar citas del cliente"}
        )

    def perform_create(self, serializer):
        """
        Personalizar la creación de clientes
        """
        serializer.save()

    def perform_update(self, serializer):
        """
        Personalizar la actualización de clientes
        """
        serializer.save()
