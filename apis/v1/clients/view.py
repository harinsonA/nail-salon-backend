from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apis.common import errors, messages
from apis.common.idempotency import IdempotentWrite
from apis.common.views import ApiView
from apis.v1.clients.form_data import ClientFormData
from apis.v1.clients.serializers import (
    ClientCreateSerializer,
    ClientSavedSerializer,
    ClientUpdateSerializer,
)
from apps.clients.editing import ClientEditor, ClientsForm
from apps.clients.models import Cliente

"""========================================================================="""
# region ........ Helpers


def valid_form(data, instance=None):
    form = ClientsForm(data=data, instance=instance)
    if not form.is_valid():
        raise serializers.ValidationError(ClientFormData.errors(form))
    return form


def saved_response(message, client, status_code=status.HTTP_200_OK):
    return Response(ClientSavedSerializer({"message": message, "client": client}).data, status=status_code)


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class ClientsView(ApiView):
    http_method_names = ["post"]

    @extend_schema(
        summary="Crear cliente",
        description=(
            "Mismo formulario y validaciones de la web; nace activo. Con codigo_app repetido "
            "devuelve el cliente ya creado sin duplicarlo."
        ),
        request=ClientCreateSerializer,
        responses={201: ClientSavedSerializer, 200: ClientSavedSerializer},
    )
    def post(self, request, *args, **kwargs):
        return IdempotentWrite(request).run(lambda: self.create(request))

    def create(self, request):
        serializer = ClientCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        changes = serializer.validated_data
        codigo_app = changes.get("codigo_app")
        existing = Cliente.all_objects.filter(codigo_app=codigo_app).first() if codigo_app else None
        if existing:
            return saved_response(ClientEditor.created_message(existing), existing)
        form = valid_form(ClientFormData.for_create(changes))
        client = ClientEditor.create(form, codigo_app=codigo_app)
        return saved_response(ClientEditor.created_message(client), client, status.HTTP_201_CREATED)


class ClientView(ApiView):
    http_method_names = ["patch"]

    @extend_schema(
        summary="Editar cliente",
        description=(
            "Solo lo que cambió, incluido estado. Con version distinta al modified del cliente "
            "responde 409: cambió en otro lugar."
        ),
        request=ClientUpdateSerializer,
        responses=ClientSavedSerializer,
    )
    def patch(self, request, *args, **kwargs):
        return IdempotentWrite(request).run(lambda: self.update(request, kwargs["pk"]))

    def update(self, request, pk):
        client = Cliente.objects.filter(pk=pk).first()
        if client is None:
            raise NotFound(messages.CLIENT_NOT_FOUND)
        serializer = ClientUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        changes = serializer.validated_data
        version = changes.get("version")
        if version and version != client.modified:
            raise errors.Conflict(messages.CLIENT_CHANGED)
        form = valid_form(ClientFormData.for_update(client, changes), instance=client)
        client = ClientEditor.update(client, form)
        return saved_response(ClientEditor.updated_message(client), client)


# endregion
"""========================================================================="""
