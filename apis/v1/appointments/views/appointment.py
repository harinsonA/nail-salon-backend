from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apis.common import errors, messages
from apis.common.idempotency import IdempotentWrite
from apis.common.views import ApiView
from apis.v1.appointments.saving import AppointmentSaving
from apis.v1.appointments.serializers import (
    AppointmentSavedSerializer,
    AppointmentUpdateSerializer,
)
from apps.appointments.access import visible_appointments
from apps.appointments.editing import AppointmentSavedMessage
from apps.appointments.engine import AppointmentWriter
from apps.appointments.models import Cita

"""========================================================================="""
# region ........ Views


class AppointmentView(ApiView):
    http_method_names = ["put"]

    def update(self, request, pk):
        appointment = visible_appointments(request.user).filter(pk=pk).first()
        if appointment is None:
            raise NotFound(messages.APPOINTMENT_NOT_FOUND)
        serializer = AppointmentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        changes = serializer.validated_data
        version = changes.get("version")
        if version and version != appointment.modified:
            raise errors.Conflict(messages.APPOINTMENT_CHANGED)
        if appointment.estado != Cita.EstadoChoices.PENDIENTE:
            raise errors.Conflict(messages.APPOINTMENT_NOT_PENDING)
        data = AppointmentSaving(request, appointment).validated(changes)
        appointment = AppointmentWriter(request.user).update(appointment, data)
        appointment = AppointmentSaving.reloaded(appointment)
        body = {"message": AppointmentSavedMessage.updated(appointment), "appointment": appointment}
        return Response(AppointmentSavedSerializer(body).data)

    @extend_schema(
        summary="Editar cita",
        description=(
            "Todos los datos del formulario, cada servicio y anticipo guardado con su id. "
            "Con version distinta al modified de la cita responde 409; si ya no está "
            "pendiente, también 409. El resumen se valida igual que al crear."
        ),
        request=AppointmentUpdateSerializer,
        responses=AppointmentSavedSerializer,
    )
    def put(self, request, *args, **kwargs):
        return IdempotentWrite(request).run(lambda: self.update(request, kwargs["pk"]))


# endregion
"""========================================================================="""
