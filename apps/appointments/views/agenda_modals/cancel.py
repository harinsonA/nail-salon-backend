from bootstrap_modal_forms.generic import BSModalReadView
from django.http import JsonResponse
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

from apps.appointments.access import AppointmentAccessMixin
from apps.appointments.cancelling import AppointmentCancelledMessage, CancelRefundsForm
from apps.appointments.engine import (
    AppointmentCancellation,
    AppointmentLockedError,
    AppointmentRuleError,
)
from apps.appointments.models import Cita
from apps.appointments.views.agenda_modals.common import (
    AgendaBaseModalView,
    AppointmentPanelMixin,
)

"""========================================================================="""
# region ........ Views


class AgendaCancelModalView(
    AppointmentAccessMixin, AppointmentPanelMixin, AgendaBaseModalView, BSModalReadView
):
    model = Cita
    panel_mode = "cancel"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        engine = AppointmentCancellation(self.object, request.user)
        try:
            engine.check()
        except AppointmentLockedError as error:
            return JsonResponse({"message": error.message}, status=HTTP_403_FORBIDDEN)
        except AppointmentRuleError as error:
            return JsonResponse({"message": error.message}, status=HTTP_400_BAD_REQUEST)
        form = CancelRefundsForm(request.POST, engine=engine)
        if not form.is_valid():
            return JsonResponse(
                {"message": form.errors["refunds"][0]},
                status=HTTP_400_BAD_REQUEST,
            )
        engine.cancel(form.cleaned_data["refunds"])
        return JsonResponse(
            {"message": AppointmentCancelledMessage.text(self.object)},
            status=200,
        )


# endregion
"""========================================================================="""
