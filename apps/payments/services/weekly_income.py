from calendar import monthrange
from decimal import Decimal

from django.utils import timezone

from apps.appointments.models import Cita
from apps.payments.accounting import PaymentExpressions
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
    """Ingreso facturado (total de la cita sin lo retenido) por semana-del-mes.

    Recibe el rango [first_day, last_day] (datetimes) que resuelve
    PaymentsFilterForm a partir del filtro `months`, y usa exactamente los
    mismos filtros que la tabla de pagos (estado COMPLETADO y cita completada; el manager de
    Pago ya excluye los eliminados) para que la suma de las barras cuadre con
    la card "Total de pagos".

    Las semanas se definen por día del mes: Sem 1 = días 1-7, Sem 2 = 8-14, …
    (4 o 5 buckets según el mes). El total de cada cita ya es un agregado, así
    que se trae una fila por pago y se pliega a semanas en Python.
    """
    year, month = first_day.year, first_day.month
    days_in_month = monthrange(year, month)[1]
    n_weeks = (days_in_month - 1) // 7 + 1  # 4 o 5

    rows = PaymentExpressions.with_appointment_summary(
        Pago.objects.filter(
            estado_pago=EstadoPago.COMPLETADO,
            cita__estado=Cita.EstadoChoices.COMPLETADA,
            fecha_cita__gte=first_day,
            fecha_cita__lte=last_day,
        )
    ).values_list("fecha_cita", "total_cita")

    buckets = [0] * n_weeks
    for moment, total in rows:
        index = (timezone.localtime(moment).day - 1) // 7
        buckets[min(index, n_weeks - 1)] += _num(total)

    labels = ["Semana {}".format(i + 1) for i in range(n_weeks)]
    return {
        "labels": labels,
        "datasets": [
            {"key": "ingresos", "label": "Ingresos", "data": buckets},
        ],
        "meta": {"empty": not any(buckets)},
    }
