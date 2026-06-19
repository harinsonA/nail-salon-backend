from datetime import date

# Etiquetas de mes en español (índice 0 = Enero)
MONTH_LABELS_ES = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
]


def last_n_months(months, today=None):
    """Lista de pares (año, mes) de los últimos `months` meses, del más
    antiguo al más reciente e incluyendo el mes actual."""
    today = today or date.today()
    pairs = []
    year, month = today.year, today.month
    for _ in range(months):
        pairs.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    pairs.reverse()
    return pairs


def month_label(month):
    return MONTH_LABELS_ES[month - 1]


def month_range(months, today=None):
    """Devuelve (start_date, period_keys, labels) para los últimos `months`.

    - start_date: primer día del mes más antiguo (para filtrar el queryset).
    - period_keys: date(año, mes, 1) en orden cronológico; coincide con la
      salida de TruncMonth sobre un DateField, para mapear resultados encima.
    - labels: etiquetas "Ene", "Feb", … alineadas 1:1 con period_keys.
    """
    pairs = last_n_months(months, today)
    period_keys = [date(year, month, 1) for (year, month) in pairs]
    labels = [month_label(month) for (_, month) in pairs]
    start_date = period_keys[0]
    return start_date, period_keys, labels
