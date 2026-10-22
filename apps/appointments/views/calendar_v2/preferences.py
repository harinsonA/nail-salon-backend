from bootstrap_modal_forms.forms import BSModalForm
from bootstrap_modal_forms.generic import BSModalFormView
from django import forms
from django.http import JsonResponse
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.appointments.calendar_v2.settings import STATUS_PREFERENCES, calendar_settings
from apps.common.utils.utils import get_errors_to_response
from apps.common.views.base_views import ProtectedView
from apps.settings.preferences import (
    CALENDAR_DEFAULT_VIEW,
    CALENDAR_SHOW_DEBT,
    Category,
)
from apps.settings.preferences.forms import PreferenceFieldsMixin

"""========================================================================="""
# region ........ Forms


class CalendarPreferencesForm(PreferenceFieldsMixin, BSModalForm):
    preference_category = Category.AGENDA

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


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class CalendarPreferencesModalView(ProtectedView, BSModalFormView):
    template_name = "calendar_v2/preferences_modal.html"
    form_class = CalendarPreferencesForm

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "modal_url": self.request.path}

    def form_valid(self, form):
        form.save_preferences(self.request.user)
        return JsonResponse({"settings": calendar_settings(self.request.user)})

    def form_invalid(self, form):
        errors = get_errors_to_response(form.errors)
        return JsonResponse({"errors": errors}, status=HTTP_400_BAD_REQUEST)


# endregion
"""========================================================================="""
