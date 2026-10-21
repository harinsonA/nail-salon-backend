from django.urls import reverse

from apps.appointments.models import Cita

"""========================================================================="""
# region ........ Constants


MONTH_VISIBLE_PER_DAY = 3

ACTIONS = {
    "detalle": ("Ver detalle", "visibility", "agenda_see_modal", "bs-xl-modal"),
    "editar": ("Editar cita", "edit_document", "agenda_update_modal", "canvas-modal"),
    "completar": ("Completar cita", "check_circle", "agenda_confirmation_modal", "bs-modal"),
    "cancelar": ("Cancelar cita", "cancel", "agenda_cancel_modal", "bs-modal is-danger"),
    "restaurar": ("Restaurar cita", "restore", "agenda_restore_modal", "bs-modal"),
}

ACTIONS_BY_STATUS = {
    Cita.EstadoChoices.PENDIENTE: ["detalle", "editar", "completar", "cancelar"],
    Cita.EstadoChoices.COMPLETADA: ["detalle"],
    Cita.EstadoChoices.CANCELADA: ["detalle", "restaurar"],
}


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Builders


class CalendarBuilder:
    def __init__(self, appointments):
        self.appointments = appointments

    @staticmethod
    def action(key, appointment_id):
        label, icon, url_name, class_name = ACTIONS[key]
        return {
            "label": label,
            "icon": icon,
            "link": reverse(url_name, args=[appointment_id]),
            "bsModal": True,
            "className": class_name,
        }

    def serialize(self, appointment):
        return {
            "id": appointment["id"],
            "hora": appointment["hora"].strftime("%H:%M"),
            "cliente": appointment["cliente"],
            "estado": appointment["estado"],
            "sin_cerrar": appointment["sin_cerrar"],
            "con_saldo": appointment["con_saldo"],
            "acciones": [
                self.action(key, appointment["id"]) for key in ACTIONS_BY_STATUS.get(appointment["estado"], [])
            ],
        }

    def by_day(self):
        days = {}
        for appointment in self.appointments:
            days.setdefault(appointment["fecha"].isoformat(), []).append(appointment)
        return days

    def build(self):
        raise NotImplementedError


class MonthBuilder(CalendarBuilder):
    def build(self):
        return {
            "dias": {
                day: {
                    "total": len(appointments),
                    "citas": [self.serialize(appointment) for appointment in appointments[:MONTH_VISIBLE_PER_DAY]],
                    "mas": max(0, len(appointments) - MONTH_VISIBLE_PER_DAY),
                }
                for day, appointments in self.by_day().items()
            }
        }


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Registry


BUILDERS = {"mes": MonthBuilder}


# endregion
"""========================================================================="""
