from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apis.common import errors, messages
from apis.common.idempotency import IdempotentWrite
from apis.common.views import ApiView
from apis.v1.appointments.detail import AppointmentDetail
from apis.v1.appointments.saving import AppointmentSaving
from apis.v1.appointments.serializers import (
    AppointmentDetailSerializer,
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
    http_method_names = ["get", "put"]
    not_pending_messages = {
        Cita.EstadoChoices.COMPLETADA: messages.APPOINTMENT_COMPLETED_EDIT,
        Cita.EstadoChoices.CANCELADA: messages.APPOINTMENT_CANCELLED_EDIT,
    }

    @staticmethod
    def visible(request, pk):
        appointment = visible_appointments(request.user).filter(pk=pk).first()
        if appointment is None:
            raise NotFound(messages.APPOINTMENT_NOT_FOUND)
        return appointment

    @extend_schema(
        summary="Detalle de cita",
        description=(
            "Lo que muestra el panel de la web que no está en la copia local: equipo, pago "
            "(filas, pagos registrados y reservas) y quién la creó y cuándo. Los textos y montos "
            "llegan listos para mostrar. Cita que no existe o no es de la colaboradora: 404."
        ),
        responses=AppointmentDetailSerializer,
    )
    def get(self, request, *args, **kwargs):
        appointment = self.visible(request, kwargs["pk"])
        return Response(AppointmentDetailSerializer(AppointmentDetail(appointment, request.user).build()).data)

    def update(self, request, pk):
        appointment = self.visible(request, pk)
        serializer = AppointmentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        changes = serializer.validated_data
        if appointment.estado != Cita.EstadoChoices.PENDIENTE:
            raise errors.Conflict(self.not_pending_messages.get(appointment.estado, messages.APPOINTMENT_NOT_PENDING))
        version = changes.get("version")
        if version and version != appointment.modified:
            raise errors.Conflict(messages.APPOINTMENT_CHANGED)
        data = AppointmentSaving(request, appointment).validated(changes)
        appointment = AppointmentWriter(request.user).update(appointment, data)
        appointment = AppointmentSaving.reloaded(appointment)
        body = {"message": AppointmentSavedMessage.updated(appointment), "appointment": appointment}
        return Response(AppointmentSavedSerializer(body).data)

    @extend_schema(
        summary="Editar cita",
        description=(
            "Todos los datos del formulario, cada servicio y anticipo guardado con su id. "
            "Si ya no está pendiente responde 409 diciendo si fue completada o cancelada, antes "
            "de revisar la versión; con version distinta al modified de la cita, también 409. El resumen se valida igual que al crear."
        ),
        request=AppointmentUpdateSerializer,
        responses=AppointmentSavedSerializer,
    )
    def put(self, request, *args, **kwargs):
        return IdempotentWrite(request).run(lambda: self.update(request, kwargs["pk"]))


# endregion
"""========================================================================="""
