from apps.common.utils.dates import format_long_date

from .form import TIME_FORMAT


class AppointmentSavedMessage:
    CREATED = "Cita agendada"
    UPDATED = "Cita actualizada"

    @staticmethod
    def client_name(client):
        return f"{client.nombre} {client.apellido or ''}".strip()

    @classmethod
    def text(cls, prefix, appointment):
        day = format_long_date(appointment.fecha_agenda).lower()
        hour = appointment.hora_agenda.strftime(TIME_FORMAT)
        return f"{prefix}: {cls.client_name(appointment.cliente)}, {day}, {hour}."

    @classmethod
    def created(cls, appointment):
        return cls.text(cls.CREATED, appointment)

    @classmethod
    def updated(cls, appointment):
        return cls.text(cls.UPDATED, appointment)
