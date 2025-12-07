from django.urls import path
from apps.appointments.views.agenda import (
    AppointmentsView,
    AgendaListView,
    AgendaCreateModalView,
    AgendaCreateV2View,
    ServiceDetailsAjax,
    AvailableHoursAjax,
)

urlpatterns = [
    path(
        "agenda/",
        AppointmentsView.as_view(),
        name="appointments",
    ),
    path(
        "agenda/lista/ajax/",
        AgendaListView.as_view(),
        name="agenda_list",
    ),
    path(
        "agenda/crear/",
        AgendaCreateModalView.as_view(),
        name="agenda_create_modal",
    ),
    path(
        "agenda/crear/version/dos/",
        AgendaCreateV2View.as_view(),
        name="agenda_create_v2",
    ),
    path(
        "agenda/servicio/detalles/ajax/",
        ServiceDetailsAjax.as_view(),
        name="service_details_ajax",
    ),
    path(
        "agenda/horas/disponibles/ajax/",
        AvailableHoursAjax.as_view(),
        name="available_hours_ajax",
    ),
]
