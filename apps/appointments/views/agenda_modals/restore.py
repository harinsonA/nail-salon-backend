import json

from bootstrap_modal_forms.generic import BSModalReadView
from django import forms
from django.http import JsonResponse
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

from apps.appointments.access import AppointmentAccessMixin
from apps.appointments.engine import (
    AppointmentRestoration,
    AppointmentLockedError,
    AppointmentRuleError,
)
from apps.appointments.engine.messages import RESTORED_INVALID
from apps.appointments.models import Cita
from apps.appointments.views.agenda_modals.common import (
    AgendaBaseModalView,
    AppointmentPanelMixin,
)

"""========================================================================="""
# region ........ Forms


class RestorePrepaidForm(forms.Form):
    restored = forms.CharField(required=False)

    def __init__(self, *args, engine, **kwargs):
        super().__init__(*args, **kwargs)
        self.engine = engine

    def clean_restored(self):
        try:
            value = json.loads(self.cleaned_data.get("restored") or "[]")
            return self.engine.clean_restored(value)
        except json.JSONDecodeError as error:
            raise forms.ValidationError(RESTORED_INVALID) from error
        except AppointmentRuleError as error:
            raise forms.ValidationError(error.message) from error


# endregion
"""========================================================================="""

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
        message = (
            "La agenda de %(client_name)s para el día %(date)s a las %(time)s fue restaurada a Pendiente."
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
