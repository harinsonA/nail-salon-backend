from django import forms

from apps.appointments.calendar.constants import APPOINTMENT_PREFERENCE_FIELDS
from apps.common.form_fields import MoneyField
from apps.settings.preferences import (
    RESERVATION_AMOUNT,
    RESERVATION_DISCOUNTS_TOTAL,
    RESERVATION_ENABLED,
    RESERVATION_PAYMENT_METHOD,
)
from apps.settings.preferences.forms import PreferenceFieldsMixin


class ReservationSettingsForm(PreferenceFieldsMixin, forms.Form):
    AMOUNT_REQUIRED = "Debes establecer el valor de la reserva porque las citas la incluyen."

    preference_definitions = APPOINTMENT_PREFERENCE_FIELDS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_preference_fields()
        self.fields[RESERVATION_AMOUNT.key] = MoneyField(
            label=RESERVATION_AMOUNT.label,
            required=False,
            max_value=RESERVATION_AMOUNT.max_value,
            initial=self.fields[RESERVATION_AMOUNT.key].initial,
        )
        self.fields[RESERVATION_PAYMENT_METHOD.key].required = False

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get(RESERVATION_ENABLED.key):
            return self.clean_enabled(cleaned_data)
        return self.clean_disabled(cleaned_data)

    def clean_enabled(self, cleaned_data):
        if RESERVATION_AMOUNT.key not in self.errors and not cleaned_data.get(
            RESERVATION_AMOUNT.key
        ):
            self.add_error(RESERVATION_AMOUNT.key, self.AMOUNT_REQUIRED)
        if not cleaned_data.get(RESERVATION_PAYMENT_METHOD.key):
            cleaned_data[RESERVATION_PAYMENT_METHOD.key] = RESERVATION_PAYMENT_METHOD.default
        return cleaned_data

    def clean_disabled(self, cleaned_data):
        for preference in (RESERVATION_AMOUNT, RESERVATION_PAYMENT_METHOD):
            self.errors.pop(preference.key, None)
        return {
            **cleaned_data,
            RESERVATION_DISCOUNTS_TOTAL.key: False,
            RESERVATION_AMOUNT.key: 0,
            RESERVATION_PAYMENT_METHOD.key: RESERVATION_PAYMENT_METHOD.default,
        }
