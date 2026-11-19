from django.db.models import Prefetch, Q

from apps.appointments.access import visible_appointments
from apps.appointments.models import Cita, DetalleCita
from apps.payments.models import Pago
from apps.sync.window import SyncWindow


class AppointmentFeed:
    def __init__(self, user, mark, window):
        self.user = user
        self.mark = mark
        self.window = window

    def alive(self):
        return visible_appointments(self.user).filter(fecha_agenda__range=self.window.as_range())

    def changed(self):
        since = self.mark.changed_since
        return (
            Q(modified__gte=since)
            | Q(detalles__modified__gte=since)
            | Q(pago__modified__gte=since)
            | Q(pago__detalles_pago__modified__gte=since)
        )

    def entering_days(self):
        previous_end = SyncWindow.at(self.mark.moment).end
        return Q(fecha_agenda__gt=previous_end, fecha_agenda__lte=self.window.end)

    def items(self):
        alive = self.alive()
        if not self.mark.is_full:
            selected = alive.filter(self.changed() | self.entering_days()).values("pk")
            alive = alive.filter(pk__in=selected)
        return alive.order_by("fecha_agenda", "hora_agenda", "pk").prefetch_related(
            Prefetch("detalles", queryset=DetalleCita.objects.order_by("pk")),
            Prefetch("pago", queryset=Pago.objects.prefetch_related("detalles_pago")),
        )

    def removed(self):
        if self.mark.is_full:
            return []
        return list(
            Cita.all_objects.filter(modified__gte=self.mark.changed_since)
            .exclude(pk__in=self.alive().values("pk"))
            .order_by("pk")
            .values_list("pk", flat=True)
        )
