from bootstrap_modal_forms.generic import BSModalReadView
from django.http import JsonResponse
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

from apps.appointments.access import AppointmentAccessMixin
from apps.appointments.restoring import AppointmentRestoredMessage, RestorePrepaidForm
from apps.appointments.engine import (
    AppointmentRestoration,
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


class AgendaRestoreModalView(
    AppointmentAccessMixin, AppointmentPanelMixin, AgendaBaseModalView, BSModalReadView
):
    model = Cita
    panel_mode = "restore"

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        engine = AppointmentRestoration(self.object, request.user)
        try:
            engine.check()
        except AppointmentLockedError as error:
            return JsonResponse({"message": error.message}, status=HTTP_403_FORBIDDEN)
        except AppointmentRuleError as error:
            return JsonResponse({"message": error.message}, status=HTTP_400_BAD_REQUEST)
        form = RestorePrepaidForm(request.POST, engine=engine)
        if not form.is_valid():
            return JsonResponse(
                {"message": form.errors["restored"][0]},
                status=HTTP_400_BAD_REQUEST,
            )
        engine.restore(form.cleaned_data["restored"])
        return JsonResponse(
            {"message": AppointmentRestoredMessage.text(self.object)},
            status=200,
        )


# endregion
"""========================================================================="""
