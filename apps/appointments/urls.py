from django.urls import path
from apps.appointments.views.agenda import (
    AppointmentsView,
    AgendaListView,
    AgendaCreateModalView,
    AgendaCreateView,
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
        "agenda/crear",
        AgendaCreateView.as_view(),
        name="agenda_create",
    ),
    path(
        "agenda/crear/modal",
        AgendaCreateModalView.as_view(),
        name="agenda_create_modal",
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
