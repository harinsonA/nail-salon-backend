from apps.settings.preferences.mobile import MobilePreferences
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


class PreferencesData:
    KEYS = {
        "calendar_view": APP_CALENDAR_VIEW.key,
        "calendar_show_pending": APP_CALENDAR_SHOW_PENDING.key,
        "calendar_show_completed": APP_CALENDAR_SHOW_COMPLETED.key,
        "calendar_show_cancelled": APP_CALENDAR_SHOW_CANCELLED.key,
        "calendar_show_debt": APP_CALENDAR_SHOW_DEBT.key,
        "idle_lock_minutes": APP_IDLE_LOCK_MINUTES.key,
        "reservation_enabled": RESERVATION_ENABLED.key,
        "reservation_amount": RESERVATION_AMOUNT.key,
        "reservation_discounts_total": RESERVATION_DISCOUNTS_TOTAL.key,
        "reservation_payment_method": RESERVATION_PAYMENT_METHOD.key,
    }

    @classmethod
    def of(cls, user) -> dict:
        values = MobilePreferences(user).values()
        return {name: values[key] for name, key in cls.KEYS.items()}

    @classmethod
    def keys_for(cls, changes: dict) -> dict:
        return {cls.KEYS[name]: value for name, value in changes.items()}
