from apps.appointments.models import Cita
from apps.payments.choices import EstadoPago
from apps.payments.models import Pago


class Debts:
    FILTERS = {
        "estado_pago__in": [EstadoPago.PENDIENTE],
        "cita__estado": Cita.EstadoChoices.COMPLETADA,
    }

    @classmethod
    def queryset(cls):
        return Pago.objects.filter(**cls.FILTERS)

    @classmethod
    def count(cls):
        return cls.queryset().count()
