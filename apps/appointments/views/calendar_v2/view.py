from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from apps.appointments.calendar_v2.builders import BUILDERS
from apps.appointments.calendar_v2.filters import VIEW_CHOICES, VIEW_WEEK, CalendarFilterForm
from apps.appointments.calendar_v2.query import CalendarQuery
from apps.common.views.base_views import ProtectedAjaxView, ProtectedView
from apps.settings.preferences import CALENDAR_V2

"""========================================================================="""
# region ........ Constants


DATE_PLACEHOLDER = "__fecha__"
GRID_HOURS = {"desde": 5, "hasta": 24}
NOT_ENABLED_MESSAGE = "El calendario nuevo no está activo en este negocio."


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class CalendarV2View(ProtectedView, TemplateView):
    template_name = "calendar_v2/list.html"

    def get(self, request, *args, **kwargs):
        if not CALENDAR_V2.is_enabled():
            return redirect("calendar")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        today = timezone.localdate()
        new_appointment_url = reverse("create_appointment_from_calendar", args=[today.isoformat()])
        return {
            **super().get_context_data(**kwargs),
            "new_appointment_url": new_appointment_url,
            "calendar_config": {
                "dataUrl": reverse("calendar_v2_data"),
                "today": today.isoformat(),
                "timeZone": timezone.get_current_timezone_name(),
                "view": VIEW_WEEK,
                "views": [{"key": key, "label": label} for key, label in VIEW_CHOICES],
                "hours": GRID_HOURS,
                "newAppointmentUrl": reverse("create_appointment_from_calendar", args=[DATE_PLACEHOLDER]),
                "datePlaceholder": DATE_PLACEHOLDER,
            },
        }


class CalendarV2DataView(ProtectedAjaxView, View):
    def get(self, request, *args, **kwargs):
        if not CALENDAR_V2.is_enabled():
            return JsonResponse({"message": NOT_ENABLED_MESSAGE}, status=HTTP_404_NOT_FOUND)
        form = CalendarFilterForm(request.GET)
        if not form.is_valid():
            errors = [error for field_errors in form.errors.values() for error in field_errors]
            return JsonResponse({"message": errors[0], "errors": form.errors}, status=HTTP_400_BAD_REQUEST)
        data = form.cleaned_data
        query = CalendarQuery(request.user, data["desde"], data["hasta"], data["buscar"])
        builder = BUILDERS[data["vista"]](query.appointments())
        return JsonResponse(builder.build())


# endregion
"""========================================================================="""
