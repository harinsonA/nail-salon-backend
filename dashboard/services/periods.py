from collections import namedtuple
from datetime import date

# Periodo resuelto que consumen las funciones de metrics:
#   - start_date: primer día del mes más antiguo (para filtrar el queryset).
#   - keys: date(año, mes, 1) en orden cronológico; coincide con la salida de
#     TruncMonth sobre un DateField, para mapear resultados encima.
#   - labels: etiquetas "Ene", "Feb", … alineadas 1:1 con keys.
Period = namedtuple("Period", ["start_date", "keys", "labels"])

# Tope de meses para un rango personalizado (evita series gigantes).
MAX_BUCKETS = 36

# Etiquetas de mes en español (índice 0 = Enero)
MONTH_LABELS_ES = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
]


def month_label(month):
    return MONTH_LABELS_ES[month - 1]


def _build(pairs):
    """Construye un Period a partir de pares (año, mes) en orden cronológico."""
    pairs = pairs[-MAX_BUCKETS:]
    keys = [date(year, month, 1) for (year, month) in pairs]
    labels = [month_label(month) for (_, month) in pairs]
    return Period(start_date=keys[0], keys=keys, labels=labels)


def last_n_months(months, today=None):
    """Pares (año, mes) de los últimos `months`, del más antiguo al actual."""
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


def last_months(months, today=None):
    """Period de los últimos `months` meses (incluye el mes actual)."""
    return _build(last_n_months(months, today))


def between(date_from, date_to):
    """Period con los meses calendario entre `date_from` y `date_to` (inclusive).

    Agrupa por mes calendario: si el rango es parcial (p. ej. del 10/03 al
    25/05), incluye los meses completos marzo→mayo.
    """
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    pairs = []
    year, month = date_from.year, date_from.month
    while (year, month) <= (date_to.year, date_to.month):
        pairs.append((year, month))
        month += 1
        if month == 13:
            month = 1
            year += 1
    return _build(pairs)
