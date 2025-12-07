# Importar desde el directorio views
# Web Views
from .agenda import (
    AppointmentsView,
    AgendaListView,
    AgendaCreateModalView,
    ServiceDetailsAjax,
    AvailableHoursAjax,
)

__all__ = [
    "AppointmentsView",
    "AgendaListView",
    "AgendaCreateModalView",
    "ServiceDetailsAjax",
    "AvailableHoursAjax",
]
