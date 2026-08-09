from decimal import Decimal

from django.db.models import Sum

from apps.payments.choices import MetodoPago
from apps.payments.models import DetallePago

# Servicio del gráfico "Ingresos por método de pago" de la página de ingresos.
# Devuelve el mismo contrato JSON uniforme que los gráficos del dashboard
# (labels + datasets + meta) para poder reusar DashboardCore.renderChart.


def _num(value):
    """Normaliza valores para el JSON: None -> 0, Decimal -> float."""
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return float(value)
    return value


def income_by_method(filters):
    """Monto recibido (DetallePago.monto_pago) agrupado por método de pago.

    Recibe el dict de filtros ORM que arma IncomesFilterForm.clean (el rango de
    fechas y, si la usuaria eligió uno, `metodo_pago`) y lo aplica tal cual, de
    modo que las barras siempre cuadren con la tabla y las cards de la vista.
    El `pago__is_removed=False` replica el _filters de IncomesListView.

    Con un método seleccionado se grafica solo esa barra; sin filtro de método
    se grafican los cuatro y los que no tuvieron movimiento quedan en 0, para
    que el eje no cambie de forma entre rangos.
    """
    rows = (
        DetallePago.objects.filter(pago__is_removed=False, **filters)
        .values("metodo_pago")
        .annotate(total=Sum("monto_pago"))
    )
    totals = {row["metodo_pago"]: row["total"] for row in rows}

    selected = filters.get("metodo_pago")
    labels, data, keys = [], [], []
    for value, label in MetodoPago.CHOICES:
        if selected and value != selected:
            continue
        labels.append(label)
        data.append(_num(totals.get(value)))
        keys.append(value.lower())  # efectivo / tarjeta / transferencia / cheque

    return {
        "labels": labels,
        "datasets": [
            {"key": "metodo", "keys": keys, "label": "Recibido", "data": data},
        ],
        "meta": {"empty": not any(data)},
    }
