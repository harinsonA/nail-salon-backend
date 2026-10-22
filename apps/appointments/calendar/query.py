from django.db.models import Value
from django.db.models.functions import Concat
from django.utils import timezone

from apps.appointments.access import visible_appointments
from apps.appointments.models import Cita
from apps.appointments.panel import is_unclosed
from apps.common.utils.search import contains_ignoring_accents
from apps.payments.choices import EstadoPago

"""========================================================================="""
# region ........ Queries


class CalendarQuery:
    def __init__(self, user, start, end, search=""):
        self.user = user
        self.start = start
        self.end = end
        self.search = search

    def queryset(self):
        queryset = visible_appointments(self.user).filter(fecha_agenda__range=(self.start, self.end))
        if self.search:
            full_name = Concat("cliente__nombre", Value(" "), "cliente__apellido")
            queryset = queryset.filter(contains_ignoring_accents(full_name, self.search))
        return queryset.order_by("fecha_agenda", "hora_agenda", "pk")

    def now(self):
        return timezone.localtime()

    def appointments(self):
        now = self.now()
        rows = self.queryset().values(
            "pk",
            "fecha_agenda",
            "hora_agenda",
            "estado",
            "cliente_id",
            "cliente__telefono",
            "cliente__nombre",
            "cliente__apellido",
            "pago__pk",
            "pago__estado_pago",
            "pago__is_removed",
        )
        result = []
        for row in rows:
            result.append(
                {
                    "id": row["pk"],
                    "fecha": row["fecha_agenda"],
                    "hora": row["hora_agenda"],
                    "estado": row["estado"],
                    "cliente_id": row["cliente_id"],
                    "telefono": row["cliente__telefono"],
                    "cliente": f"{row['cliente__nombre']} {row['cliente__apellido']}".strip(),
                    "sin_cerrar": is_unclosed(row["estado"], row["fecha_agenda"], row["hora_agenda"], now),
                    "con_saldo": row["estado"] == Cita.EstadoChoices.COMPLETADA
                    and row["pago__pk"] is not None
                    and row["pago__estado_pago"] == EstadoPago.PENDIENTE
                    and not row["pago__is_removed"],
                    "pago_id": row["pago__pk"],
                }
            )
        return result


# endregion
"""========================================================================="""
