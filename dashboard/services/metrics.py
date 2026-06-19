from decimal import Decimal

from django.db.models import Count, Sum, DateField
from django.db.models.functions import TruncMonth

from apps.appointments.models.agenda import Cita
from apps.appointments.models.detalle_cita import DetalleCita
from apps.payments.models.pago import Pago
from apps.payments.models.detalle_pago import DetallePago
from apps.payments.choices import MetodoPago

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
    """Facturado (Pago.monto_total_cita por fecha_cita) vs. cobrado
    (DetallePago.monto_pago por fecha_pago), por mes."""
    billed_rows = (
        Pago.objects.filter(fecha_cita__gte=period.start_date)
        .annotate(period=TruncMonth("fecha_cita", output_field=DateField()))
        .values("period")
        .annotate(total=Sum("monto_total_cita"))
    )
    collected_rows = (
        DetallePago.objects.filter(
            pago__is_removed=False,
            fecha_pago__gte=period.start_date,
        )
        .annotate(period=TruncMonth("fecha_pago", output_field=DateField()))
        .values("period")
        .annotate(total=Sum("monto_pago"))
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
        Cita.objects.filter(fecha_agenda__gte=period.start_date)
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
    """Monto cobrado agrupado por método de pago en el período."""
    rows = (
        DetallePago.objects.filter(
            pago__is_removed=False,
            fecha_pago__gte=period.start_date,
        )
        .values("metodo_pago")
        .annotate(total=Sum("monto_pago"))
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
    """Servicios más solicitados (suma de cantidad) en el período, top `limit`."""
    rows = (
        DetalleCita.objects.filter(
            cita__is_removed=False,
            cita__fecha_agenda__gte=period.start_date,
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
    """Ingresos (suma de precio_acordado) agrupados por categoría en el período."""
    rows = (
        DetalleCita.objects.filter(
            cita__is_removed=False,
            cita__fecha_agenda__gte=period.start_date,
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
