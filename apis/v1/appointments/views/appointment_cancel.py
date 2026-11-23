from drf_spectacular.utils import extend_schema

from apis.common import messages
from apis.v1.appointments.cancellation import AppointmentCancellationCard
from apis.v1.appointments.serializers import (
    AppointmentCancelSerializer,
    AppointmentSavedSerializer,
    CancellationCardSerializer,
)
from apis.v1.appointments.views.prepaid_decision import PrepaidDecisionView
from apps.appointments.cancelling import AppointmentCancelledMessage, CancelRefundsForm
from apps.appointments.engine import AppointmentCancellation
from apps.appointments.models import Cita

"""========================================================================="""
# region ........ Views


class AppointmentCancelView(PrepaidDecisionView):
    status = Cita.EstadoChoices.PENDIENTE
    wrong_status_message = messages.APPOINTMENT_NOT_PENDING_CANCEL
    engine_class = AppointmentCancellation
    card_class = AppointmentCancellationCard
    card_serializer = CancellationCardSerializer
    request_serializer = AppointmentCancelSerializer
    form_class = CancelRefundsForm
    field = "refunds"
    message_class = AppointmentCancelledMessage

    def run(self, engine, decision):
        engine.cancel(decision)

    @extend_schema(
        summary="Abrir Cancelar",
        description=(
            "Pagos vigentes de la cita (reserva y anticipos) con el título y la nota de la "
            "web. Con pagos, la colaboradora recibe locked y el aviso de la web. Cita que no "
            "existe o no es de la colaboradora: 404; que ya no está pendiente: 409."
        ),
        responses=CancellationCardSerializer,
    )
    def get(self, request, *args, **kwargs):
        return self.open(request, kwargs["pk"])

    @extend_schema(
        summary="Cancelar cita",
        description=(
            "Mismo motor de la web. refunds lleva los pagos que se reembolsan, con método y "
            "referencia; los demás quedan retenidos. seen son los pagos que vio la app: si "
            "cambiaron, 409 y no cancela. Colaboradora con pagos: 403. Un reintento con la "
            "misma Idempotency-Key devuelve la misma respuesta."
        ),
        request=AppointmentCancelSerializer,
        responses=AppointmentSavedSerializer,
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


# endregion
"""========================================================================="""
