from drf_spectacular.utils import extend_schema

from apis.common import messages
from apis.v1.appointments.restoration import AppointmentRestorationCard
from apis.v1.appointments.serializers import (
    AppointmentRestoreSerializer,
    AppointmentSavedSerializer,
    RestorationCardSerializer,
)
from apis.v1.appointments.views.prepaid_decision import PrepaidDecisionView
from apps.appointments.engine import AppointmentRestoration
from apps.appointments.models import Cita
from apps.appointments.restoring import AppointmentRestoredMessage, RestorePrepaidForm

"""========================================================================="""
# region ........ Views


class AppointmentRestoreView(PrepaidDecisionView):
    status = Cita.EstadoChoices.CANCELADA
    wrong_status_message = messages.APPOINTMENT_NOT_CANCELLED_RESTORE
    engine_class = AppointmentRestoration
    card_class = AppointmentRestorationCard
    card_serializer = RestorationCardSerializer
    request_serializer = AppointmentRestoreSerializer
    form_class = RestorePrepaidForm
    field = "restored"
    message_class = AppointmentRestoredMessage

    def run(self, engine, decision):
        engine.restore(decision)

    @extend_schema(
        summary="Abrir Restaurar",
        description=(
            "Pagos retenidos de la cita con el título y la nota de la web, el total de los "
            "servicios y lo pagado. Con pagos, la colaboradora recibe locked y el aviso de la "
            "web. Cita que no existe o no es de la colaboradora: 404; que ya no está "
            "cancelada: 409."
        ),
        responses=RestorationCardSerializer,
    )
    def get(self, request, *args, **kwargs):
        return self.open(request, kwargs["pk"])

    @extend_schema(
        summary="Restaurar cita",
        description=(
            "Mismo motor de la web. restored lleva los pagos retenidos que vuelven a la cita; "
            "los demás quedan para el negocio de forma definitiva. seen son los pagos que vio "
            "la app: si cambiaron, 409 y no restaura. Colaboradora con pagos: 403. Un "
            "reintento con la misma Idempotency-Key devuelve la misma respuesta."
        ),
        request=AppointmentRestoreSerializer,
        responses=AppointmentSavedSerializer,
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


# endregion
"""========================================================================="""
