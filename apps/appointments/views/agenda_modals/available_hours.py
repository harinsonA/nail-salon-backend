from django import forms
from django.http import JsonResponse
from django.views import View

from apps.appointments.access import visible_appointments
from apps.appointments.models.agenda import Cita
from apps.appointments.views.agenda_modals.common import DATE_FORMAT, TIME_FORMAT
from apps.common.views.base_views import ProtectedAjaxView

"""========================================================================="""
# region ........ Forms


class BusyHoursFilterForm(forms.Form):
    fecha = forms.DateField(input_formats=[DATE_FORMAT])
    asignada = forms.IntegerField(required=False)
    excluir = forms.IntegerField(required=False)


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class AvailableHoursAjax(ProtectedAjaxView, View):
    def get(self, request, *args, **kwargs):
        form = BusyHoursFilterForm(request.GET)
        if not form.is_valid():
            return JsonResponse({"horas": []})
        data = form.cleaned_data
        appointments = (
            visible_appointments(request.user)
            .filter(fecha_agenda=data["fecha"])
            .exclude(estado=Cita.EstadoChoices.CANCELADA)
            .exclude(pk=data["excluir"])
        )
        hours = {}
        for hour, assigned_id in appointments.order_by("hora_agenda").values_list(
            "hora_agenda", "asignado_a_id"
        ):
            key = hour.strftime(TIME_FORMAT)
            item = hours.setdefault(
                key, {"hora": key, "total": 0, "de_asignada": False}
            )
            item["total"] += 1
            item["de_asignada"] = item["de_asignada"] or (
                data["asignada"] is not None and assigned_id == data["asignada"]
            )
        return JsonResponse({"horas": list(hours.values())})


# endregion
"""========================================================================="""
