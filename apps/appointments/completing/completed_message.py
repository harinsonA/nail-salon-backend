from apps.common.utils.dates import format_plain_date


class AppointmentCompletedMessage:
    @staticmethod
    def client_name(client):
        return f"{client.nombre or ''} {client.apellido or ''}".strip()

    @classmethod
    def text(cls, appointment):
        return (
            "La cita de %(client_name)s para el día %(date)s a las %(time)s fue "
            "completada."
        ) % {
            "client_name": cls.client_name(appointment.cliente),
            "date": format_plain_date(appointment.fecha_agenda),
            "time": appointment.hora_agenda.strftime("%H:%M"),
        }
