import json

from bootstrap_modal_forms.generic import BSModalReadView
from django import forms
from django.db import transaction
from django.http import JsonResponse
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN

from apps.appointments.access import AppointmentAccessMixin, is_collaborator
from apps.appointments.models import Cita
from apps.appointments.views.agenda_modals.common import (
    AgendaBaseModalView,
    AppointmentPanelMixin,
)
from apps.payments.choices import MetodoPago
from apps.payments.services.advances import (
    appointment_payment,
    open_advances,
    settle_cancellation,
)

"""========================================================================="""
# region ........ Constants


REFUND_METHODS = {MetodoPago.EFECTIVO, MetodoPago.TRANSFERENCIA}
REFERENCE_MAX_LENGTH = 100
REFUNDS_INVALID = "Los reembolsos enviados no son válidos."
CANCEL_LOCKED = (
    "Esta cita tiene anticipos. Solo la propietaria o la encargada pueden cancelarla."
)


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class CancelRefundsForm(forms.Form):
    refunds = forms.CharField(required=False)

    def __init__(self, *args, advances=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.advances = {row.pk: row for row in advances}

    def clean_refunds(self):
        try:
            refunds = json.loads(self.cleaned_data.get("refunds") or "[]")
        except json.JSONDecodeError as error:
            raise forms.ValidationError(REFUNDS_INVALID) from error
        if not isinstance(refunds, list):
            raise forms.ValidationError(REFUNDS_INVALID)
        cleaned = {}
        for refund in refunds:
            pk, values = self.clean_refund(refund)
            if pk in cleaned:
                raise forms.ValidationError(REFUNDS_INVALID)
            cleaned[pk] = values
        return cleaned

    def clean_refund(self, refund):
        if not isinstance(refund, dict):
            raise forms.ValidationError(REFUNDS_INVALID)
        try:
            pk = int(refund.get("id"))
        except (TypeError, ValueError) as error:
            raise forms.ValidationError(REFUNDS_INVALID) from error
        method = refund.get("metodo")
        reference = refund.get("referencia") or ""
        if pk not in self.advances or method not in REFUND_METHODS:
            raise forms.ValidationError(REFUNDS_INVALID)
        if not isinstance(reference, str) or len(reference.strip()) > REFERENCE_MAX_LENGTH:
            raise forms.ValidationError(REFUNDS_INVALID)
        return pk, {"method": method, "reference": reference.strip()}


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
        if self.object.estado != Cita.EstadoChoices.PENDIENTE:
            message = "Solo se pueden cancelar las agendas en estado Pendiente."
            return JsonResponse(
                {"message": message},
                status=HTTP_400_BAD_REQUEST,
            )
        advances = open_advances(appointment_payment(self.object))
        if advances and is_collaborator(request.user):
            return JsonResponse({"message": CANCEL_LOCKED}, status=HTTP_403_FORBIDDEN)
        form = CancelRefundsForm(request.POST, advances=advances)
        if not form.is_valid():
            return JsonResponse(
                {"message": form.errors["refunds"][0]},
                status=HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            self.object.estado = Cita.EstadoChoices.CANCELADA
            self.object.save()
            settle_cancellation(self.object, form.cleaned_data["refunds"], request.user)
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
