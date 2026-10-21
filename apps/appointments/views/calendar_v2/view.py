from django.shortcuts import redirect
from django.views.generic import TemplateView

from apps.common.views.base_views import ProtectedView
from apps.settings.preferences import CALENDAR_V2

"""========================================================================="""
# region ........ Views


class CalendarV2View(ProtectedView, TemplateView):
    template_name = "calendar_v2/list.html"

    def get(self, request, *args, **kwargs):
        if not CALENDAR_V2.is_enabled():
            return redirect("calendar")
        return super().get(request, *args, **kwargs)


# endregion
"""========================================================================="""
