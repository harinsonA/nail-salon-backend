import json

from bootstrap_modal_forms.generic import BSModalReadView
from django import forms
from django.http import JsonResponse
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

from apps.appointments.access import AppointmentAccessMixin
from apps.appointments.engine import (
    AppointmentCancellation,
    AppointmentLockedError,
    AppointmentRuleError,
)
from apps.appointments.engine.messages import REFUNDS_INVALID
from apps.appointments.models import Cita
from apps.appointments.views.agenda_modals.common import (
    AgendaBaseModalView,
    AppointmentPanelMixin,
)

"""========================================================================="""
# region ........ Forms


class CancelRefundsForm(forms.Form):
    refunds = forms.CharField(required=False)

    def __init__(self, *args, engine, **kwargs):
        super().__init__(*args, **kwargs)
        self.engine = engine

    def clean_refunds(self):
        try:
            value = json.loads(self.cleaned_data.get("refunds") or "[]")
            return self.engine.clean_refunds(value)
        except json.JSONDecodeError as error:
            raise forms.ValidationError(REFUNDS_INVALID) from error
        except AppointmentRuleError as error:
            raise forms.ValidationError(error.message) from error


# endregion
"""========================================================================="""

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
        message = (
            "La agenda de %(client_name)s para el día %(date)s a las %(time)s fue cancelada."
        ) % {
            "client_name": self._get_client_full_name(self.object),
            "date": self._get_date_formatted(self.object),
            "time": self._get_time_formatted(self.object),
        }
        return JsonResponse(
            {"message": message},
            status=200,
        )


# endregion
"""========================================================================="""
