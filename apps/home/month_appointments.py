from django.db.models import Count, Q

from apps.appointments.access import visible_appointments
from apps.appointments.models import Cita

Estado = Cita.EstadoChoices


class MonthAppointments:
    def __init__(self, user, month):
        self.user = user
        self.month = month

    def counts(self):
        totals = (
            visible_appointments(self.user)
            .filter(fecha_agenda__gte=self.month.start, fecha_agenda__lt=self.month.end)
            .aggregate(
                completed=Count("pk", filter=Q(estado=Estado.COMPLETADA)),
                pending=Count("pk", filter=Q(estado=Estado.PENDIENTE)),
            )
        )
        return {
            "label": self.month.label,
            "start": self.month.start,
            "appointments": totals["completed"] + totals["pending"],
            "completed": totals["completed"],
            "pending": totals["pending"],
        }
