from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response

from apis.common import errors, messages
from apis.common.idempotency import IdempotentWrite
from apis.common.views import ApiView
from apis.v1.appointments.completion import AppointmentCompletionCard, AppointmentCompletionData
from apis.v1.appointments.lookup import AppointmentLookup
from apis.v1.appointments.saving import AppointmentSaving
from apis.v1.appointments.serializers import (
    AppointmentCompleteSerializer,
    AppointmentSavedSerializer,
    CompletionCardSerializer,
)
from apps.appointments.completing import AppointmentCompletedMessage, CompletionForm
from apps.appointments.models import Cita

"""========================================================================="""
# region ........ Views


class AppointmentCompleteView(ApiView):
    http_method_names = ["get", "post"]

    @staticmethod
    def pending(request, pk, lock=False):
        appointment = AppointmentLookup.visible(request.user, pk, lock)
        if appointment.estado != Cita.EstadoChoices.PENDIENTE:
            raise errors.Conflict(messages.APPOINTMENT_NOT_PENDING_COMPLETE)
        return appointment

    @extend_schema(
        summary="Abrir Completar",
        description=(
            "Total de los servicios, lo pagado antes (reserva y anticipos) y el saldo, con "
            "las mismas cuentas del modal de la web. Si ya está todo pagado, settled_hint "
            "trae el aviso; si lo pagado supera el total, blocked trae el motivo. Cita que "
            "no existe o no es de la colaboradora: 404; que ya no está pendiente: 409."
        ),
        responses=CompletionCardSerializer,
    )
    def get(self, request, *args, **kwargs):
        appointment = self.pending(request, kwargs["pk"])
        card = AppointmentCompletionCard(appointment, request.user).build()
        return Response(CompletionCardSerializer(card).data)

    @transaction.atomic
    def complete(self, request, pk):
        serializer = AppointmentCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        changes = serializer.validated_data
        appointment = self.pending(request, pk, lock=True)
        form = CompletionForm(
            data=AppointmentCompletionData.for_form(changes),
            request=request,
            instance=appointment,
        )
        if form.completion.remaining_changed(changes["remaining"]):
            raise errors.Conflict(messages.APPOINTMENT_PAYMENT_CHANGED)
        if not form.is_valid():
            raise serializers.ValidationError(AppointmentCompletionData.errors(form))
        form.complete(request.user)
        appointment = AppointmentSaving.reloaded(appointment)
        body = {"message": AppointmentCompletedMessage.text(appointment), "appointment": appointment}
        return Response(AppointmentSavedSerializer(body).data)

    @extend_schema(
        summary="Completar cita",
        description=(
            "Mismo formulario y motor de la web. remaining es el saldo que vio la app: si "
            "cambió, responde 409 y no completa. Un reintento con la misma Idempotency-Key "
            "devuelve la misma respuesta."
        ),
        request=AppointmentCompleteSerializer,
        responses=AppointmentSavedSerializer,
    )
    def post(self, request, *args, **kwargs):
        return IdempotentWrite(request).run(lambda: self.complete(request, kwargs["pk"]))


# endregion
"""========================================================================="""
