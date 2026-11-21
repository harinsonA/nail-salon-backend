from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apis.common import errors, messages
from apis.common.views import ApiView
from apis.v1.services.form_data import ServiceFormData
from apis.v1.services.serializers import (
    ServiceFieldsSerializer,
    ServiceSavedSerializer,
    ServiceUpdateSerializer,
)
from apps.services.editing import ServiceEditor, ServicesForm
from apps.services.models import Servicio

"""========================================================================="""
# region ........ Helpers


def valid_form(data):
    form = ServicesForm(data=data)
    if not form.is_valid():
        raise serializers.ValidationError(ServiceFormData.errors(form))
    return form


def saved_response(message, service, status_code=status.HTTP_200_OK):
    return Response(
        ServiceSavedSerializer({"message": message, "service": service}).data,
        status=status_code,
    )


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class ServicesView(ApiView):
    http_method_names = ["post"]

    @extend_schema(
        summary="Crear servicio",
        description=(
            "Mismo formulario y validaciones de la web; nace activo. precio en pesos enteros y "
            "duracion_estimada en minutos. Solo administración."
        ),
        request=ServiceFieldsSerializer,
        responses={201: ServiceSavedSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = ServiceFieldsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        form = valid_form(ServiceFormData.for_create(serializer.validated_data))
        service = ServiceEditor.create(form)
        return saved_response(
            ServiceEditor.created_message(service), service, status.HTTP_201_CREATED
        )


class ServiceView(ApiView):
    http_method_names = ["patch"]

    @extend_schema(
        summary="Editar servicio",
        description=(
            "Solo lo que cambió, incluido estado. No se activa con la categoría inactiva, como "
            "en la web. Con version distinta al modified responde 409."
        ),
        request=ServiceUpdateSerializer,
        responses=ServiceSavedSerializer,
    )
    def patch(self, request, *args, **kwargs):
        service = Servicio.objects.filter(pk=kwargs["pk"]).first()
        if service is None:
            raise NotFound(messages.SERVICE_NOT_FOUND)
        serializer = ServiceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        changes = serializer.validated_data
        version = changes.get("version")
        if version and version != service.modified:
            raise errors.Conflict(messages.SERVICE_CHANGED)
        form = valid_form(ServiceFormData.for_update(service, changes))
        result = ServiceEditor.update(service, form)
        if result.is_err():
            raise serializers.ValidationError(ServiceFormData.category_error(result.err_value))
        return saved_response(ServiceEditor.updated_message(result.ok_value), result.ok_value)


# endregion
"""========================================================================="""
