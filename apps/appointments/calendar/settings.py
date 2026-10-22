from apps.appointments.models import Cita
from apps.settings.preferences import (
    CALENDAR_DEFAULT_VIEW,
    CALENDAR_SHOW_CANCELLED,
    CALENDAR_SHOW_COMPLETED,
    CALENDAR_SHOW_DEBT,
    CALENDAR_SHOW_PENDING,
    get_preferences,
)

"""========================================================================="""
# region ........ Constants


STATUS_PREFERENCES = {
    Cita.EstadoChoices.PENDIENTE: CALENDAR_SHOW_PENDING,
    Cita.EstadoChoices.COMPLETADA: CALENDAR_SHOW_COMPLETED,
    Cita.EstadoChoices.CANCELADA: CALENDAR_SHOW_CANCELLED,
}


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Helpers


def calendar_settings(user):
    keys = [
        CALENDAR_DEFAULT_VIEW.key,
        CALENDAR_SHOW_DEBT.key,
        *[preference.key for preference in STATUS_PREFERENCES.values()],
    ]
    values = get_preferences(keys, user=user)
    visible = {
        status: values[preference.key]
        for status, preference in STATUS_PREFERENCES.items()
    }
    return {
        "view": values[CALENDAR_DEFAULT_VIEW.key],
        "visible": visible,
        "showDebt": values[CALENDAR_SHOW_DEBT.key],
        "filtered": not all(visible.values()),
    }


def visible_statuses(settings):
    return [status for status, shown in settings["visible"].items() if shown]


# endregion
"""========================================================================="""
