from bootstrap_modal_forms.generic import BSModalUpdateView

from apps.appointments.access import visible_appointments
from apps.appointments.models import Cita
from apps.common.views.base_views import ProtectedView
from apps.payments.choices import EstadoPago
from apps.payments.models import Pago
from apps.payments.views.debtors.common import PaymentInstallmentMixin

"""========================================================================="""
# region ........ Views


class AgendaPaymentModalView(PaymentInstallmentMixin, ProtectedView, BSModalUpdateView):
    def get_queryset(self):
        appointments = visible_appointments(self.request.user).filter(
            estado=Cita.EstadoChoices.COMPLETADA
        )
        return Pago.objects.filter(
            cita__in=appointments, estado_pago=EstadoPago.PENDIENTE
        ).select_related("atendido_por")


# endregion
"""========================================================================="""
