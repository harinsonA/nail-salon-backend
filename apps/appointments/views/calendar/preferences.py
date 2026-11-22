from bootstrap_modal_forms.forms import BSModalForm
from bootstrap_modal_forms.generic import BSModalFormView
from django import forms
from django.http import JsonResponse
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.appointments.calendar.constants import CALENDAR_PREFERENCE_FIELDS
from apps.appointments.calendar.settings import STATUS_PREFERENCES, calendar_settings
from apps.appointments.reservation_settings import ReservationSettings, ReservationSettingsForm
from apps.common.utils.utils import get_errors_to_response
from apps.common.views.base_views import ProtectedView
from apps.settings.preferences import (
    CALENDAR_DEFAULT_VIEW,
    CALENDAR_SHOW_DEBT,
    RESERVATION_AMOUNT,
    RESERVATION_DISCOUNTS_TOTAL,
    RESERVATION_ENABLED,
    RESERVATION_PAYMENT_METHOD,
)
from apps.settings.preferences.forms import PreferenceFieldsMixin

"""========================================================================="""
# region ........ Forms


class CalendarPreferencesForm(PreferenceFieldsMixin, BSModalForm):
    preference_definitions = CALENDAR_PREFERENCE_FIELDS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_preference_fields(self.request.user)
        for key in self.preference_keys:
            if isinstance(self.fields[key], forms.BooleanField):
                self.fields[key].widget.attrs["role"] = "switch"
        self.fields[CALENDAR_DEFAULT_VIEW.key].widget = forms.RadioSelect(
            choices=CALENDAR_DEFAULT_VIEW.choices,
            attrs={"class": "form-check-input"},
        )

    @property
    def status_fields(self):
        return [
            (status, self[preference.key])
            for status, preference in STATUS_PREFERENCES.items()
        ]

    @property
    def debt_field(self):
        return self[CALENDAR_SHOW_DEBT.key]

    @property
    def view_field(self):
        return self[CALENDAR_DEFAULT_VIEW.key]


class AppointmentPreferencesForm(ReservationSettingsForm, BSModalForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for preference in (RESERVATION_ENABLED, RESERVATION_DISCOUNTS_TOTAL):
            self.fields[preference.key].widget.attrs["role"] = "switch"

    @property
    def enabled_field(self):
        return self[RESERVATION_ENABLED.key]

    @property
    def discounts_field(self):
        return self[RESERVATION_DISCOUNTS_TOTAL.key]

    @property
    def amount_field(self):
        return self[RESERVATION_AMOUNT.key]

    @property
    def method_field(self):
        return self[RESERVATION_PAYMENT_METHOD.key]


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class CalendarPreferencesModalView(ProtectedView, BSModalFormView):
    template_name = "calendar/preferences_modal.html"
    form_class = CalendarPreferencesForm

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "modal_url": self.request.path}

    def form_valid(self, form):
        form.save_preferences(self.request.user)
        return JsonResponse({"settings": calendar_settings(self.request.user)})

    def form_invalid(self, form):
        errors = get_errors_to_response(form.errors)
        return JsonResponse({"errors": errors}, status=HTTP_400_BAD_REQUEST)


class AppointmentPreferencesModalView(ProtectedView, BSModalFormView):
    template_name = "calendar/appointment_preferences_modal.html"
    form_class = AppointmentPreferencesForm

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "modal_url": self.request.path}

    def form_valid(self, form):
        ReservationSettings.save(form)
        return JsonResponse({"message": ReservationSettings.SAVED_MESSAGE})

    def form_invalid(self, form):
        return JsonResponse(
            {
                "message": ReservationSettings.INVALID_MESSAGE,
                "errors": get_errors_to_response(form.errors),
            },
            status=HTTP_400_BAD_REQUEST,
        )


# endregion
"""========================================================================="""
