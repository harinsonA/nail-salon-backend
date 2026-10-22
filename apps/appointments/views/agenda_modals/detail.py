from bootstrap_modal_forms.generic import BSModalReadView

from apps.appointments.access import AppointmentAccessMixin
from apps.appointments.models import Cita
from apps.appointments.views.agenda_modals.common import AppointmentPanelMixin
from apps.common.views.base_views import ProtectedView

"""========================================================================="""
# region ........ Views


class AgendaSeeModalView(
    AppointmentAccessMixin, AppointmentPanelMixin, ProtectedView, BSModalReadView
):
    model = Cita


# endregion
"""========================================================================="""
