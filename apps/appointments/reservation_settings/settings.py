from django.db import transaction

from apps.settings.preferences import (
    RESERVATION_AMOUNT,
    RESERVATION_DISCOUNTS_TOTAL,
    RESERVATION_ENABLED,
    RESERVATION_PAYMENT_METHOD,
)
from apps.settings.preferences.service import get_preferences

from .form import ReservationSettingsForm


class ReservationSettings:
    SAVED_MESSAGE = "La configuración de las citas se guardó."
    INVALID_MESSAGE = "Revisa los campos marcados."
    FIELDS = {
        "enabled": RESERVATION_ENABLED,
        "amount": RESERVATION_AMOUNT,
        "discounts_total": RESERVATION_DISCOUNTS_TOTAL,
        "payment_method": RESERVATION_PAYMENT_METHOD,
    }
    PREFERENCES = tuple(FIELDS.values())

    @classmethod
    def values(cls) -> dict:
        return get_preferences([preference.key for preference in cls.PREFERENCES])

    @classmethod
    def form_data(cls, changes: dict) -> dict:
        current = cls.values()
        data = {}
        for name, preference in cls.FIELDS.items():
            value = changes[name] if name in changes else current[preference.key]
            data[preference.key] = "" if value is None else value
        return data

    @classmethod
    def errors(cls, form: ReservationSettingsForm) -> dict:
        names = {preference.key: name for name, preference in cls.FIELDS.items()}
        return {names.get(key, key): messages for key, messages in form.errors.items()}

    @staticmethod
    def save(form: ReservationSettingsForm) -> None:
        with transaction.atomic():
            form.save_preferences()
