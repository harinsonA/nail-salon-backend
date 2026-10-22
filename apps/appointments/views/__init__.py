# Importar desde el directorio views
# Web Views
from .agenda import (
    AppointmentsView,
    AgendaListView,
)
from .agenda_modals.available_hours import AvailableHoursAjax
from .agenda_modals.cancel import AgendaCancelModalView
from .agenda_modals.create import AgendaCreateView
from .agenda_modals.detail import AgendaSeeModalView
from .agenda_modals.edit import AgendaUpdateModalView

__all__ = [
    "AppointmentsView",
    "AgendaListView",
    "AgendaCancelModalView",
    "AgendaCreateView",
    "AgendaSeeModalView",
    "AgendaUpdateModalView",
    "AvailableHoursAjax",
]
