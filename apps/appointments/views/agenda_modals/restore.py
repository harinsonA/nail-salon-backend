import json

from bootstrap_modal_forms.generic import BSModalReadView
from django import forms
from django.db import transaction
from django.http import JsonResponse
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

from apps.appointments.access import AppointmentAccessMixin, is_collaborator
from apps.appointments.models import Cita
from apps.appointments.prepaid import PrepaidCard
from apps.appointments.views.agenda_modals.common import (
    AgendaBaseModalView,
    AppointmentPanelMixin,
)
from apps.payments.accounting import AppointmentLedger, AppointmentPaymentService

"""========================================================================="""
# region ........ Constants


RESTORED_INVALID = "Los pagos a restaurar no son válidos."


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class RestorePrepaidForm(forms.Form):
    restored = forms.CharField(required=False)

    def __init__(self, *args, rows=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.rows = {row.pk for row in rows}

    def clean_restored(self):
        try:
            restored = json.loads(self.cleaned_data.get("restored") or "[]")
        except json.JSONDecodeError as error:
            raise forms.ValidationError(RESTORED_INVALID) from error
        if not isinstance(restored, list):
            raise forms.ValidationError(RESTORED_INVALID)
        if any(isinstance(pk, bool) or not isinstance(pk, int) for pk in restored):
            raise forms.ValidationError(RESTORED_INVALID)
        if len(restored) != len(set(restored)) or not set(restored) <= self.rows:
            raise forms.ValidationError(RESTORED_INVALID)
        return set(restored)


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
        if self.object.estado != Cita.EstadoChoices.CANCELADA:
            message = "Solo se pueden restaurar las agendas en estado Cancelada."
            return JsonResponse(
                {"message": message},
                status=HTTP_400_BAD_REQUEST,
            )
        rows = AppointmentLedger.for_appointment(self.object).retained_prepaid()
        if rows and is_collaborator(request.user):
            return JsonResponse(
                {"message": PrepaidCard(rows).restore_locked()},
                status=HTTP_403_FORBIDDEN,
            )
        form = RestorePrepaidForm(request.POST, rows=rows)
        if not form.is_valid():
            return JsonResponse(
                {"message": form.errors["restored"][0]},
                status=HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            self.object.estado = Cita.EstadoChoices.PENDIENTE
            self.object.save()
            AppointmentPaymentService(self.object, request.user).restore(
                form.cleaned_data["restored"]
            )
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
