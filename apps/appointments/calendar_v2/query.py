from django.db.models import Value
from django.db.models.functions import Concat
from django.utils import timezone

from apps.appointments.models import Cita
from apps.common.utils.search import contains_ignoring_accents
from apps.payments.choices import EstadoPago
from apps.profiles.models import Perfil
from apps.profiles.permisos import rol_de

"""========================================================================="""
# region ........ Queries


class CalendarQuery:
    def __init__(self, user, start, end, search=""):
        self.user = user
        self.start = start
        self.end = end
        self.search = search

    def queryset(self):
        queryset = Cita.objects.filter(fecha_agenda__range=(self.start, self.end))
        if rol_de(self.user) == Perfil.Rol.COLABORADOR:
            queryset = queryset.filter(asignado_a=self.user)
        if self.search:
            full_name = Concat("cliente__nombre", Value(" "), "cliente__apellido")
            queryset = queryset.filter(contains_ignoring_accents(full_name, self.search))
        return queryset.order_by("fecha_agenda", "hora_agenda", "pk")

    def now(self):
        return timezone.localtime()

    def appointments(self):
        now = self.now()
        today = now.date()
        current_time = now.time()
        rows = self.queryset().values(
            "pk",
            "fecha_agenda",
            "hora_agenda",
            "estado",
            "cliente__nombre",
            "cliente__apellido",
            "pago__estado_pago",
            "pago__is_removed",
        )
        result = []
        for row in rows:
            is_pending = row["estado"] == Cita.EstadoChoices.PENDIENTE
            result.append(
                {
                    "id": row["pk"],
                    "fecha": row["fecha_agenda"],
                    "hora": row["hora_agenda"],
                    "estado": row["estado"],
                    "cliente": f"{row['cliente__nombre']} {row['cliente__apellido']}".strip(),
                    "sin_cerrar": is_pending
                    and (
                        row["fecha_agenda"] < today
                        or (row["fecha_agenda"] == today and row["hora_agenda"] < current_time)
                    ),
                    "con_saldo": row["estado"] == Cita.EstadoChoices.COMPLETADA
                    and row["pago__estado_pago"] == EstadoPago.PENDIENTE
                    and not row["pago__is_removed"],
                }
            )
        return result


# endregion
"""========================================================================="""
