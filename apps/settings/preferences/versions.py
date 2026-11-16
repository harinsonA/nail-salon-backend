from django.core.exceptions import ValidationError

from apps.settings.preferences.registry import APP_LATEST_VERSION, APP_MINIMUM_VERSION

"""========================================================================="""
# region ........ Constants


MINIMUM_ABOVE_LATEST = "La versión mínima no puede ser mayor que la última versión."


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Classes


class AppVersion:
    @staticmethod
    def parse(value) -> tuple:
        return tuple(int(part) for part in value.split("."))

    @classmethod
    def clean(cls, value) -> str:
        return APP_MINIMUM_VERSION.clean(value)

    @classmethod
    def is_above(cls, version, other) -> bool:
        if not version or not other:
            return False
        return cls.parse(version) > cls.parse(other)

    @classmethod
    def check_range(cls, minimum, latest):
        if cls.is_above(minimum, latest):
            raise ValidationError(MINIMUM_ABOVE_LATEST)

    @classmethod
    def current(cls) -> dict:
        from apps.settings.preferences.service import get_preferences

        values = get_preferences([APP_MINIMUM_VERSION.key, APP_LATEST_VERSION.key])
        return {
            "minimum": values[APP_MINIMUM_VERSION.key],
            "latest": values[APP_LATEST_VERSION.key],
        }


# endregion
"""========================================================================="""
