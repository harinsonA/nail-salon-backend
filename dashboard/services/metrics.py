from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, DateField, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.appointments.models.agenda import Cita
from apps.appointments.models.detalle_cita import DetalleCita
from apps.payments.accounting import PaymentExpressions
from apps.payments.choices import MetodoPago
from apps.payments.models.detalle_pago import DetallePago
from apps.payments.models.pago import Pago

# Todas las funciones reciben un `period` (dashboard.services.periods.Period)
# ya resuelto por el form a partir del filtro global, y devuelven el contrato
# JSON uniforme: labels + datasets + meta.


def _num(value):
    """Normaliza valores para el JSON: None -> 0, Decimal -> float."""
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return float(value)
    return value


def _monthly_series(period, rows, value_field):
    """Mapea filas agrupadas por mes sobre el rango completo, rellenando con 0
    los meses sin datos para que el eje sea continuo."""
    by_period = {row["period"]: row for row in rows}
    series = []
    for key in period.keys:
        row = by_period.get(key)
        series.append(_num(row[value_field]) if row else 0)
    return series


def _meta(*series):
    return {"empty": not any(any(s) for s in series)}


def attended_clients(period):
    """Citas completadas y clientes únicos por mes."""
    rows = (
        Cita.objects.filter(
            estado=Cita.EstadoChoices.COMPLETADA,
            fecha_agenda__gte=period.start_date,
            fecha_agenda__lt=period.end_date,
        )
        .annotate(period=TruncMonth("fecha_agenda"))
        .values("period")
        .annotate(
            atendidas=Count("id"),
            unicos=Count("cliente", distinct=True),
        )
    )
    by_period = {row["period"]: row for row in rows}

    atendidas, unicos = [], []
    for key in period.keys:
        row = by_period.get(key)
        atendidas.append(row["atendidas"] if row else 0)
        unicos.append(row["unicos"] if row else 0)

    return {
        "labels": period.labels,
        "datasets": [
            {"key": "atendidas", "label": "Citas atendidas", "data": atendidas},
            {"key": "unicos", "label": "Clientes únicos", "data": unicos},
        ],
        "meta": _meta(atendidas, unicos),
    }


def income_billed_vs_collected(period):
    """Facturado (total de las citas completadas sin lo retenido, por fecha_cita) vs.
    cobrado neto (DetallePago.monto_pago por fecha_pago, las devoluciones restan), por mes."""
    billed_by_month = defaultdict(Decimal)
    for moment, total in PaymentExpressions.with_appointment_summary(
        Pago.objects.filter(
            cita__estado=Cita.EstadoChoices.COMPLETADA,
            fecha_cita__date__gte=period.start_date,
            fecha_cita__date__lt=period.end_date,
        )
    ).values_list("fecha_cita", "total_cita"):
        billed_by_month[timezone.localtime(moment).date().replace(day=1)] += total
    billed_rows = [
        {"period": key, "total": total} for key, total in billed_by_month.items()
    ]
    collected_rows = (
        DetallePago.objects.filter(
            pago__is_removed=False,
            fecha_pago__date__gte=period.start_date,
            fecha_pago__date__lt=period.end_date,
        )
        .annotate(period=TruncMonth("fecha_pago", output_field=DateField()))
        .values("period")
        .annotate(total=PaymentExpressions.net_paid())
    )

    billed = _monthly_series(period, billed_rows, "total")
    collected = _monthly_series(period, collected_rows, "total")

    return {
        "labels": period.labels,
        "datasets": [
            {"key": "facturado", "label": "Facturado", "data": billed},
            {"key": "cobrado", "label": "Cobrado", "data": collected},
        ],
        "meta": _meta(billed, collected),
    }


def appointment_status(period):
    """Citas agrupadas por estado (pendiente/completada/cancelada) en el período."""
    rows = (
        Cita.objects.filter(
            fecha_agenda__gte=period.start_date,
            fecha_agenda__lt=period.end_date,
        )
        .values("estado")
        .annotate(total=Count("id"))
    )
    counts = {row["estado"]: row["total"] for row in rows}

    labels, data, keys = [], [], []
    for value, label in Cita.EstadoChoices.choices:
        labels.append(label)
        data.append(counts.get(value, 0))
        keys.append(value)  # pendiente / completada / cancelada

    return {
        "labels": labels,
        "datasets": [{"key": "estado", "keys": keys, "label": "Citas", "data": data}],
        "meta": _meta(data),
    }


def payment_methods(period):
    """Monto cobrado neto (las devoluciones restan) agrupado por método de pago en el período."""
    rows = (
        DetallePago.objects.filter(
            pago__is_removed=False,
            fecha_pago__date__gte=period.start_date,
            fecha_pago__date__lt=period.end_date,
        )
        .values("metodo_pago")
        .annotate(total=PaymentExpressions.net_paid())
    )
    totals = {row["metodo_pago"]: row["total"] for row in rows}

    labels, data, keys = [], [], []
    for value, label in MetodoPago.CHOICES:
        labels.append(label)
        data.append(_num(totals.get(value)))
        keys.append(value.lower())  # efectivo / tarjeta / transferencia / cheque

    return {
        "labels": labels,
        "datasets": [{"key": "metodo", "keys": keys, "label": "Cobrado", "data": data}],
        "meta": _meta(data),
    }


def top_services(period, limit=8):
    """Servicios más solicitados (suma de cantidad en citas completadas), top `limit`."""
    rows = (
        DetalleCita.objects.filter(
            cita__is_removed=False,
            cita__estado=Cita.EstadoChoices.COMPLETADA,
            cita__fecha_agenda__gte=period.start_date,
            cita__fecha_agenda__lt=period.end_date,
        )
        .values("nombre_servicio")
        .annotate(total=Sum("cantidad_servicios"))
        .order_by("-total")[:limit]
    )

    labels = [row["nombre_servicio"] for row in rows]
    data = [_num(row["total"]) for row in rows]

    return {
        "labels": labels,
        "datasets": [{"key": "servicios", "label": "Cantidad", "data": data}],
        "meta": _meta(data),
    }


def income_by_category(period):
    """Ingresos (suma de precio_acordado de citas completadas) agrupados por categoría."""
    rows = (
        DetalleCita.objects.filter(
            cita__is_removed=False,
            cita__estado=Cita.EstadoChoices.COMPLETADA,
            cita__fecha_agenda__gte=period.start_date,
            cita__fecha_agenda__lt=period.end_date,
        )
        .values("servicio__categoria__nombre")
        .annotate(total=Sum("precio_acordado"))
        .order_by("-total")
    )

    labels, data, keys = [], [], []
    for index, row in enumerate(rows):
        labels.append(row["servicio__categoria__nombre"] or "Sin categoría")
        data.append(_num(row["total"]))
        keys.append("cat_{}".format(index))  # colores cíclicos en el frontend

    return {
        "labels": labels,
        "datasets": [
            {"key": "ingresos", "keys": keys, "label": "Ingresos", "data": data}
        ],
        "meta": _meta(data),
    }
