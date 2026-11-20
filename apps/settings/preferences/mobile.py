from django.db import transaction

from apps.settings.preferences.registry import (
    APP_CALENDAR_SHOW_CANCELLED,
    APP_CALENDAR_SHOW_COMPLETED,
    APP_CALENDAR_SHOW_DEBT,
    APP_CALENDAR_SHOW_PENDING,
    APP_CALENDAR_VIEW,
    APP_IDLE_LOCK_MINUTES,
    RESERVATION_AMOUNT,
    RESERVATION_DISCOUNTS_TOTAL,
    RESERVATION_ENABLED,
    RESERVATION_PAYMENT_METHOD,
)
from apps.settings.preferences.service import get_preferences, set_preference


class MobilePreferences:
    EDITABLE = (
        APP_CALENDAR_VIEW,
        APP_CALENDAR_SHOW_PENDING,
        APP_CALENDAR_SHOW_COMPLETED,
        APP_CALENDAR_SHOW_CANCELLED,
        APP_CALENDAR_SHOW_DEBT,
        APP_IDLE_LOCK_MINUTES,
    )
    READ_ONLY = (
        RESERVATION_ENABLED,
        RESERVATION_AMOUNT,
        RESERVATION_DISCOUNTS_TOTAL,
        RESERVATION_PAYMENT_METHOD,
    )
    SAVED_MESSAGE = "Preferencias actualizadas."

    def __init__(self, user):
        self.user = user

    def values(self):
        return get_preferences(
            [definition.key for definition in (*self.EDITABLE, *self.READ_ONLY)],
            user=self.user,
        )

    def update(self, changes):
        editable = {definition.key for definition in self.EDITABLE}
        with transaction.atomic():
            for key, value in changes.items():
                if key in editable:
                    set_preference(key, value, user=self.user)
        return self.values()
