# Importar desde el directorio views
# Web Views
from .agenda import (
    AppointmentsView,
    AgendaListView,
    AgendaUpdateModalView,
    AgendaCancelModalView,
    AgendaSeeModalView,
)
from .agenda_create import (
    AgendaCreateView,
    ServiceDetailsAjax,
    AvailableHoursAjax,
)

__all__ = [
    "AppointmentsView",
    "AgendaListView",
    "AgendaCancelModalView",
    "AgendaCreateView",
    "AgendaSeeModalView",
    "AgendaUpdateModalView",
    "AvailableHoursAjax",
    "ServiceDetailsAjax",
]
