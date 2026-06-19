from decimal import Decimal

from django.db.models import Count, Sum, DateField
from django.db.models.functions import TruncMonth

from apps.appointments.models.agenda import Cita
from apps.appointments.models.detalle_cita import DetalleCita
from apps.payments.models.pago import Pago
from apps.payments.models.detalle_pago import DetallePago
from apps.payments.choices import MetodoPago
from dashboard.services import periods


def _num(value):
    """Normaliza valores para el JSON: None -> 0, Decimal -> float."""
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return float(value)
    return value


def _monthly_series(period_keys, rows, value_field):
    """Mapea filas agrupadas por mes sobre el rango completo, rellenando con 0
    los meses sin datos para que el eje sea continuo."""
    by_period = {row["period"]: row for row in rows}
    series = []
    for key in period_keys:
        row = by_period.get(key)
        series.append(_num(row[value_field]) if row else 0)
    return series


def _meta(months, *series):
    return {
        "period": "last_{}_months".format(months),
        "empty": not any(any(s) for s in series),
    }


def attended_clients(months):
    """Citas completadas y clientes únicos por mes (últimos `months`).

    Un GROUP BY por mes no devuelve filas para meses sin actividad, por eso
    se generan todos los meses del rango y se rellenan con 0 los faltantes.

    Devuelve el contrato JSON uniforme: labels + datasets + meta.
    """
    start_date, period_keys, labels = periods.month_range(months)

    rows = (
        Cita.objects.filter(
            estado=Cita.EstadoChoices.COMPLETADA,
            fecha_agenda__gte=start_date,
        )
        .annotate(period=TruncMonth("fecha_agenda"))
        .values("period")
        .annotate(
            atendidas=Count("id"),
            unicos=Count("cliente", distinct=True),
        )
    )
    by_period = {row["period"]: row for row in rows}

    atendidas = []
    unicos = []
    for key in period_keys:
        row = by_period.get(key)
        atendidas.append(row["atendidas"] if row else 0)
        unicos.append(row["unicos"] if row else 0)

    return {
        "labels": labels,
        "datasets": [
            {"key": "atendidas", "label": "Citas atendidas", "data": atendidas},
            {"key": "unicos", "label": "Clientes únicos", "data": unicos},
        ],
        "meta": _meta(months, atendidas, unicos),
    }


def income_billed_vs_collected(months):
    """Facturado (Pago.monto_total_cita por fecha_cita) vs. cobrado
    (DetallePago.monto_pago por fecha_pago), por mes."""
    start_date, period_keys, labels = periods.month_range(months)

    billed_rows = (
        Pago.objects.filter(fecha_cita__gte=start_date)
        .annotate(period=TruncMonth("fecha_cita", output_field=DateField()))
        .values("period")
        .annotate(total=Sum("monto_total_cita"))
    )
    collected_rows = (
        DetallePago.objects.filter(
            pago__is_removed=False,
            fecha_pago__gte=start_date,
        )
        .annotate(period=TruncMonth("fecha_pago", output_field=DateField()))
        .values("period")
        .annotate(total=Sum("monto_pago"))
    )

    billed = _monthly_series(period_keys, billed_rows, "total")
    collected = _monthly_series(period_keys, collected_rows, "total")

    return {
        "labels": labels,
        "datasets": [
            {"key": "facturado", "label": "Facturado", "data": billed},
            {"key": "cobrado", "label": "Cobrado", "data": collected},
        ],
        "meta": _meta(months, billed, collected),
    }


def appointment_status(months):
    """Citas agrupadas por estado (pendiente/completada/cancelada) en el período."""
    start_date, _, _ = periods.month_range(months)

    rows = (
        Cita.objects.filter(fecha_agenda__gte=start_date)
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
        "meta": _meta(months, data),
    }


def payment_methods(months):
    """Monto cobrado agrupado por método de pago en el período."""
    start_date, _, _ = periods.month_range(months)

    rows = (
        DetallePago.objects.filter(
            pago__is_removed=False,
            fecha_pago__gte=start_date,
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
        "meta": _meta(months, data),
    }


def top_services(months, limit=8):
    """Servicios más solicitados (suma de cantidad) en el período, top `limit`."""
    start_date, _, _ = periods.month_range(months)

    rows = (
        DetalleCita.objects.filter(
            cita__is_removed=False,
            cita__fecha_agenda__gte=start_date,
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
        "meta": _meta(months, data),
    }


def income_by_category(months):
    """Ingresos (suma de precio_acordado) agrupados por categoría en el período."""
    start_date, _, _ = periods.month_range(months)

    rows = (
        DetalleCita.objects.filter(
            cita__is_removed=False,
            cita__fecha_agenda__gte=start_date,
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
        "meta": _meta(months, data),
    }
