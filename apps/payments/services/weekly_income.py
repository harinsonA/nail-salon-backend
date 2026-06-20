from calendar import monthrange
from decimal import Decimal

from django.db.models import Sum, DateField
from django.db.models.functions import TruncDay

from apps.payments.choices import EstadoPago
from apps.payments.models import Pago

# Servicio del gráfico "Ingresos por semana" de la página de pagos.
# Devuelve el mismo contrato JSON uniforme que los gráficos del dashboard
# (labels + datasets + meta) para poder reusar DashboardCore.renderChart.


def _num(value):
    """Normaliza valores para el JSON: None -> 0, Decimal -> float."""
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return float(value)
    return value


def weekly_income(first_day, last_day):
    """Ingreso facturado (Pago.monto_total_cita) por semana-del-mes.

    Recibe el rango [first_day, last_day] (datetimes) que resuelve
    PaymentsFilterForm a partir del filtro `months`, y usa exactamente los
    mismos filtros que la tabla de pagos (estado COMPLETADO; el manager de
    Pago ya excluye los eliminados) para que la suma de las barras cuadre con
    la card "Total de pagos".

    Las semanas se definen por día del mes: Sem 1 = días 1-7, Sem 2 = 8-14, …
    (4 o 5 buckets según el mes). Se agrupa por día en SQL (barato, <=31 filas)
    y se pliega a semanas en Python para ser independiente del motor de BD.
    """
    year, month = first_day.year, first_day.month
    days_in_month = monthrange(year, month)[1]
    n_weeks = (days_in_month - 1) // 7 + 1  # 4 o 5

    rows = (
        Pago.objects.filter(
            estado_pago=EstadoPago.COMPLETADO,
            fecha_cita__gte=first_day,
            fecha_cita__lte=last_day,
        )
        .annotate(day=TruncDay("fecha_cita", output_field=DateField()))
        .values("day")
        .annotate(total=Sum("monto_total_cita"))
    )

    buckets = [0] * n_weeks
    for row in rows:
        day = row["day"]
        if not day:
            continue
        index = (day.day - 1) // 7
        buckets[min(index, n_weeks - 1)] += _num(row["total"])

    labels = ["Semana {}".format(i + 1) for i in range(n_weeks)]
    return {
        "labels": labels,
        "datasets": [
            {"key": "ingresos", "label": "Ingresos", "data": buckets},
        ],
        "meta": {"empty": not any(buckets)},
    }
