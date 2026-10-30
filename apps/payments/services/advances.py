from datetime import datetime

from django.db.models import Exists, OuterRef, Sum
from django.utils import timezone

from apps.payments.choices import (
    EstadoDetallePago,
    EstadoPago,
    MetodoPago,
    TipoDetallePago,
)
from apps.payments.models import DetallePago, Pago
from apps.payments.services.account import ZERO, PaymentAccount

"""========================================================================="""
# region ........ Queries


def appointment_payment(appointment):
    if appointment is None or appointment.pk is None:
        return None
    return Pago.objects.filter(cita=appointment).first()


def saved_advances(payment):
    if payment is None:
        return []
    refunds = DetallePago.objects.filter(detalle_devuelto=OuterRef("pk"))
    return list(
        payment.detalles_pago.filter(tipo_detalle=TipoDetallePago.ANTICIPO)
        .annotate(has_refunds=Exists(refunds))
        .order_by("fecha_pago", "pk")
    )


def open_advances(payment):
    return [
        row
        for row in saved_advances(payment)
        if not row.has_refunds
        and (row.estado_detalle or EstadoDetallePago.VIGENTE) == EstadoDetallePago.VIGENTE
    ]


def retained_advances(payment):
    return [
        row
        for row in saved_advances(payment)
        if row.estado_detalle == EstadoDetallePago.RETENIDO
    ]


# endregion
"""========================================================================="""

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


def advance_reference(method, reference):
    return None if method == MetodoPago.EFECTIVO else reference or None


def build_advance(payment, advance, user, moment):
    method = advance["method"]
    return DetallePago(
        pago=payment,
        fecha_pago=moment,
        monto_pago=advance["amount"],
        metodo_pago=method,
        referencia_pago=advance_reference(method, advance["reference"]),
        registrado_por=user,
        tipo_detalle=TipoDetallePago.ANTICIPO,
        estado_detalle=EstadoDetallePago.VIGENTE,
    )


def update_advance(row, change):
    values = {
        "monto_pago": change["amount"],
        "metodo_pago": change["method"],
        "referencia_pago": advance_reference(change["method"], change["reference"]),
    }
    if all(getattr(row, name) == value for name, value in values.items()):
        return
    for name, value in values.items():
        setattr(row, name, value)
    row.save()


def build_refund(row, refund, user, moment):
    method = refund["method"]
    return DetallePago(
        pago=row.pago,
        fecha_pago=moment,
        monto_pago=row.monto_pago,
        metodo_pago=method,
        referencia_pago=advance_reference(method, refund["reference"]),
        registrado_por=user,
        tipo_detalle=TipoDetallePago.DEVOLUCION,
        estado_detalle=EstadoDetallePago.VIGENTE,
        detalle_devuelto=row,
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


def fill_payment(payment, appointment, cancelled=False):
    services_total, discounts = services_amounts(appointment)
    details = None if payment.pk else []
    payment.cliente_nombre = appointment.cliente.nombre_completo
    payment.fecha_cita = appointment_moment(appointment)
    payment.descuento_total = discounts
    payment.monto_total_cita = PaymentAccount(payment, details).total(
        services_total, cancelled=cancelled
    )
    return payment


def refresh_payment(payment, appointment):
    fill_payment(payment, appointment).save()


def sync_advances(appointment, changes, user):
    added = [change for change in changes if change["row"] is None]
    payment = appointment_payment(appointment)
    if payment is None:
        return register_advances(appointment, added, user)
    for change in changes:
        row = change["row"]
        if row is None:
            continue
        if change["remove"]:
            row.delete()
        else:
            update_advance(row, change)
    moment = timezone.now()
    for change in added:
        build_advance(payment, change, user, moment).save()
    refresh_payment(payment, appointment)
    return payment


def settle_cancellation(appointment, refunds, user):
    payment = appointment_payment(appointment)
    if payment is None:
        return None
    moment = timezone.now()
    for row in open_advances(payment):
        refund = refunds.get(row.pk)
        if refund:
            build_refund(row, refund, user, moment).save()
            row.estado_detalle = EstadoDetallePago.DEVUELTO
        else:
            row.estado_detalle = EstadoDetallePago.RETENIDO
        row.save()
    fill_payment(payment, appointment, cancelled=True)
    if PaymentAccount(payment).paid() > ZERO:
        payment.estado_pago = EstadoPago.COMPLETADO
        payment.fecha_pago_completado = moment
    else:
        payment.estado_pago = EstadoPago.REEMBOLSADO
    payment.save()
    return payment


def reopen_payment(appointment, restored):
    payment = appointment_payment(appointment)
    if payment is None:
        return None
    for row in retained_advances(payment):
        if row.pk in restored:
            row.estado_detalle = EstadoDetallePago.VIGENTE
        else:
            row.estado_detalle = EstadoDetallePago.RETENIDO_DEFINITIVO
        row.save()
    fill_payment(payment, appointment)
    payment.estado_pago = EstadoPago.PENDIENTE
    payment.fecha_pago_completado = None
    payment.save()
    return payment


# endregion
"""========================================================================="""
