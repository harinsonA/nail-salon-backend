from datetime import date

from bootstrap_modal_forms.generic import BSModalFormView
from django.utils import timezone

from apps.appointments.engine import AppointmentWriter
from apps.appointments.views.agenda_modals.common import AppointmentFormMixin
from apps.common.views.base_views import ProtectedView

"""========================================================================="""
# region ........ Views


class AgendaCreateView(AppointmentFormMixin, ProtectedView, BSModalFormView):
    def selected_date(self):
        today = timezone.localdate()
        try:
            selected = date.fromisoformat(self.kwargs.get("date", ""))
        except ValueError:
            return today
        return max(selected, today)

    def get_initial(self):
        return {
            **super().get_initial(),
            "date": self.selected_date(),
            "assigned_to": self.request.user,
        }

    def save_appointment(self, data):
        return AppointmentWriter(self.request.user).create(data)


# endregion
"""========================================================================="""
