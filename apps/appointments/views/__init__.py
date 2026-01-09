# Importar desde el directorio views
# Web Views
from .agenda import (
    AppointmentsView,
    AgendaListView,
    AgendaUpdateModalView,
    AgendaCancelModalView,
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
    "AgendaUpdateModalView",
    "AvailableHoursAjax",
    "ServiceDetailsAjax",
]
