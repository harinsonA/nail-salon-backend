from django.templatetags.static import static
from django.urls import reverse

from apps.appointments.models import Cita

"""========================================================================="""
# region ........ Constants


MONTH_VISIBLE_PER_DAY = 3
MIXED_STATUS = "mixto"
OVERDUE_STATUS = "vencida"

ACTIONS = {
    "detalle": ("Ver detalle", "visibility", "agenda_see_modal", "canvas-modal"),
    "editar": ("Editar cita", "edit_document", "agenda_update_modal", "bs-xl-modal"),
    "completar": ("Completar cita", "check_circle", "agenda_confirmation_modal", "bs-modal"),
    "cancelar": ("Cancelar cita", "cancel", "agenda_cancel_modal", "canvas-modal is-danger"),
    "restaurar": ("Restaurar cita", "restore", "agenda_restore_modal", "canvas-modal"),
    "abonar": ("Registrar abono", "payments", "agenda_payment_modal", "bs-modal"),
}

PAYMENT_ACTION = "abonar"

WHATSAPP_ACTION = {
    "label": "Enviar WhatsApp",
    "iconImage": "images/common/whatsapp.svg",
    "url_name": "client_whatsapp_modal",
    "className": "bs-modal",
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

    @staticmethod
    def whatsapp_action(appointment):
        return {
            "label": WHATSAPP_ACTION["label"],
            "iconImage": static(WHATSAPP_ACTION["iconImage"]),
            "link": reverse(WHATSAPP_ACTION["url_name"], args=[appointment["cliente_id"]]),
            "bsModal": True,
            "className": WHATSAPP_ACTION["className"],
        }

    def with_contact(self, appointment, actions):
        if appointment.get("telefono") and appointment.get("cliente_id"):
            actions.insert(1, self.whatsapp_action(appointment))
        return actions

    def serialize(self, appointment):
        return {
            "id": appointment["id"],
            "hora": appointment["hora"].strftime("%H:%M"),
            "cliente": appointment["cliente"],
            "estado": appointment["estado"],
            "sin_cerrar": appointment["sin_cerrar"],
            "con_saldo": appointment["con_saldo"],
            "acciones": self.with_contact(appointment, self.actions(appointment)),
        }

    def actions(self, appointment):
        actions = [
            self.action(key, appointment["id"])
            for key in ACTIONS_BY_STATUS.get(appointment["estado"], [])
        ]
        if appointment["con_saldo"] and appointment.get("pago_id"):
            actions.append(self.action(PAYMENT_ACTION, appointment["pago_id"]))
        return actions

    @staticmethod
    def visual_status(appointment):
        return OVERDUE_STATUS if appointment["sin_cerrar"] else appointment["estado"]

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


class WeekBuilder(CalendarBuilder):
    def build(self):
        return {
            "dias": {
                day: {"total": len(appointments), "bloques": self.blocks(appointments)}
                for day, appointments in self.by_day().items()
            }
        }

    def blocks(self, appointments):
        hours = {}
        for appointment in appointments:
            hours.setdefault(appointment["hora"].hour, []).append(appointment)
        return [
            {
                "hora": hour,
                "estado": self.block_status(items),
                "citas": [self.serialize(appointment) for appointment in items],
            }
            for hour, items in sorted(hours.items())
        ]

    def block_status(self, appointments):
        statuses = {self.visual_status(appointment) for appointment in appointments}
        return statuses.pop() if len(statuses) == 1 else MIXED_STATUS


class DayBuilder(WeekBuilder):
    def build(self):
        return {
            "dias": {
                day: {
                    "total": len(appointments),
                    "resumen": self.summary(appointments),
                    "bloques": self.blocks(appointments),
                }
                for day, appointments in self.by_day().items()
            }
        }

    @staticmethod
    def summary(appointments):
        counts = {status: 0 for status in Cita.EstadoChoices.values}
        for appointment in appointments:
            counts[appointment["estado"]] += 1
        return counts


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Registry


BUILDERS = {"dia": DayBuilder, "semana": WeekBuilder, "mes": MonthBuilder}


# endregion
"""========================================================================="""
