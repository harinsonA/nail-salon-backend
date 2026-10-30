from decimal import Decimal

from django.db.models import Case, DecimalField, F, Q, Sum, Value, When
from django.db.models.functions import Coalesce

from apps.payments.choices import EstadoDetallePago, TipoDetallePago

"""========================================================================="""
# region ........ Constants


ZERO = Decimal("0")
MONEY_FIELD = DecimalField(max_digits=12, decimal_places=2)
PREPAID_TYPES = (TipoDetallePago.RESERVA, TipoDetallePago.ANTICIPO)
RETAINED_STATES = (EstadoDetallePago.RETENIDO, EstadoDetallePago.RETENIDO_DEFINITIVO)


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Queries


def signed_amount(prefix=""):
    return Case(
        When(
            **{f"{prefix}tipo_detalle": TipoDetallePago.DEVOLUCION},
            then=-F(f"{prefix}monto_pago"),
        ),
        default=F(f"{prefix}monto_pago"),
        output_field=MONEY_FIELD,
    )


def net_paid(prefix=""):
    return Coalesce(Sum(signed_amount(prefix)), Value(ZERO), output_field=MONEY_FIELD)


def incoming(prefix=""):
    return ~Q(**{f"{prefix}tipo_detalle": TipoDetallePago.DEVOLUCION})


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Helpers


def detail_type(detail):
    return detail.tipo_detalle or TipoDetallePago.ABONO


def detail_status(detail):
    return detail.estado_detalle or EstadoDetallePago.VIGENTE


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Classes


class PaymentAccount:
    def __init__(self, payment, details=None):
        self.payment = payment
        self.details = (
            list(details) if details is not None else list(payment.detalles_pago.all())
        )

    def paid(self):
        total = ZERO
        for detail in self.details:
            if detail_type(detail) == TipoDetallePago.DEVOLUCION:
                total -= detail.monto_pago
            else:
                total += detail.monto_pago
        return total

    def refunded(self, detail):
        return sum(
            (
                item.monto_pago
                for item in self.details
                if detail_type(item) == TipoDetallePago.DEVOLUCION
                and item.detalle_devuelto_id == detail.pk
            ),
            ZERO,
        )

    def refundable(self, detail):
        if detail_type(detail) not in PREPAID_TYPES:
            return ZERO
        return max(ZERO, detail.monto_pago - self.refunded(detail))

    def retained(self):
        return sum(
            (
                self.refundable(detail)
                for detail in self.details
                if detail_status(detail) in RETAINED_STATES
            ),
            ZERO,
        )

    def charges(self):
        total = ZERO
        for detail in self.details:
            kind = detail_type(detail)
            if kind == TipoDetallePago.RESERVA or (
                kind == TipoDetallePago.ANTICIPO
                and detail_status(detail) in RETAINED_STATES
            ):
                total += self.refundable(detail)
        return total

    def credit(self):
        return self.paid() - self.charges()

    def total(self, services_amount, cancelled=False):
        return (ZERO if cancelled else Decimal(services_amount)) + self.charges()

    def balance(self):
        return max(ZERO, self.payment.monto_total_cita - self.paid())


# endregion
"""========================================================================="""
