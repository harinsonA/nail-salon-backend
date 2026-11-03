from apps.settings.preferences.constants import Category, Scope
from apps.settings.preferences.registry import (
    CALENDAR_DEFAULT_VIEW,
    CALENDAR_SHOW_CANCELLED,
    CALENDAR_SHOW_COMPLETED,
    CALENDAR_SHOW_DEBT,
    CALENDAR_SHOW_PENDING,
    PREFERENCES,
    RESERVATION_AMOUNT,
    RESERVATION_DISCOUNTS_TOTAL,
    RESERVATION_ENABLED,
    RESERVATION_MODULE,
    SESSION_IDLE_MINUTES,
)
from apps.settings.preferences.service import (
    get_preference,
    get_preferences,
    set_preference,
)

__all__ = [
    "CALENDAR_DEFAULT_VIEW",
    "CALENDAR_SHOW_CANCELLED",
    "CALENDAR_SHOW_COMPLETED",
    "CALENDAR_SHOW_DEBT",
    "CALENDAR_SHOW_PENDING",
    "PREFERENCES",
    "RESERVATION_AMOUNT",
    "RESERVATION_DISCOUNTS_TOTAL",
    "RESERVATION_ENABLED",
    "RESERVATION_MODULE",
    "SESSION_IDLE_MINUTES",
    "Category",
    "Scope",
    "get_preference",
    "get_preferences",
    "set_preference",
]
