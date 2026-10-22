from django.urls import path

from apps.appointments.views.agenda_modals.available_hours import AvailableHoursAjax
from apps.appointments.views.agenda_modals.cancel import AgendaCancelModalView
from apps.appointments.views.agenda_modals.complete import AgendaConfirmationModal
from apps.appointments.views.agenda_modals.create import AgendaCreateView
from apps.appointments.views.agenda_modals.delete import AgendaDeleteModalView
from apps.appointments.views.agenda_modals.detail import AgendaSeeModalView
from apps.appointments.views.agenda_modals.edit import AgendaUpdateModalView
from apps.appointments.views.agenda_modals.payment import AgendaPaymentModalView
from apps.appointments.views.agenda_modals.restore import AgendaRestoreModalView
from apps.appointments.views.calendar.preferences import CalendarPreferencesModalView
from apps.appointments.views.calendar.view import CalendarDataView, CalendarView

urlpatterns = [
    path(
        "calendario/",
        CalendarView.as_view(),
        name="calendar",
    ),
    path(
        "calendario/datos/",
        CalendarDataView.as_view(),
        name="calendar_data",
    ),
    path(
        "calendario/preferencias/",
        CalendarPreferencesModalView.as_view(),
        name="calendar_preferences",
    ),
    path(
        "calendario/agenda/<str:date>/crear/",
        AgendaCreateView.as_view(),
        name="create_appointment_from_calendar",
    ),
    path(
        "agenda/detalle/<str:pk>/editar/modal/",
        AgendaUpdateModalView.as_view(),
        name="agenda_update_modal",
    ),
    path(
        "agenda/detalle/<str:pk>/ver/modal/",
        AgendaSeeModalView.as_view(),
        name="agenda_see_modal",
    ),
    path(
        "agenda/detalle/<str:pk>/confirmar/modal/",
        AgendaConfirmationModal.as_view(),
        name="agenda_confirmation_modal",
    ),
    path(
        "agenda/pago/<int:pk>/abonar/modal/",
        AgendaPaymentModalView.as_view(),
        name="agenda_payment_modal",
    ),
    path(
        "agenda/detalle/<str:pk>/cancelar/modal/",
        AgendaCancelModalView.as_view(),
        name="agenda_cancel_modal",
    ),
    path(
        "agenda/detalle/<str:pk>/restaurar/modal/",
        AgendaRestoreModalView.as_view(),
        name="agenda_restore_modal",
    ),
    path(
        "agenda/detalle/<str:pk>/eliminar/modal/",
        AgendaDeleteModalView.as_view(),
        name="agenda_delete_modal",
    ),
    path(
        "agenda/horas/disponibles/ajax/",
        AvailableHoursAjax.as_view(),
        name="available_hours_ajax",
    ),
]
