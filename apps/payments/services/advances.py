from datetime import datetime

from django.db.models import Sum
from django.utils import timezone

from apps.payments.choices import EstadoDetallePago, MetodoPago, TipoDetallePago
from apps.payments.models import DetallePago, Pago
from apps.payments.services.account import ZERO, PaymentAccount

"""========================================================================="""
# region ........ Helpers


def appointment_moment(appointment):
    return timezone.make_aware(
        datetime.combine(appointment.fecha_agenda, appointment.hora_agenda)
    )


def services_amounts(appointment):
    totals = appointment.detalles.aggregate(
        total=Sum("precio_acordado"), discounts=Sum("descuento")
    )
    return totals["total"] or ZERO, totals["discounts"] or ZERO


def build_advance(payment, advance, user, moment):
    method = advance["method"]
    return DetallePago(
        pago=payment,
        fecha_pago=moment,
        monto_pago=advance["amount"],
        metodo_pago=method,
        referencia_pago=None
        if method == MetodoPago.EFECTIVO
        else advance["reference"] or None,
        registrado_por=user,
        tipo_detalle=TipoDetallePago.ANTICIPO,
        estado_detalle=EstadoDetallePago.VIGENTE,
    )


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Services


def register_advances(appointment, advances, user):
    if not advances:
        return None
    services_total, discounts = services_amounts(appointment)
    payment = Pago(
        cita=appointment,
        cliente_nombre=appointment.cliente.nombre_completo,
        fecha_cita=appointment_moment(appointment),
        descuento_total=discounts,
    )
    moment = timezone.now()
    rows = [build_advance(payment, advance, user, moment) for advance in advances]
    payment.monto_total_cita = PaymentAccount(payment, rows).total(services_total)
    payment.save()
    for row in rows:
        row.save()
    return payment


# endregion
"""========================================================================="""
