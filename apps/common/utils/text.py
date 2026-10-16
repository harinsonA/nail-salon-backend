def truncate_text(value, limit: int = 80, suffix: str = "...") -> str:
    """Recorta un texto a `limit` caracteres y agrega `suffix` si se cortó.

    Pensado para mostrar valores en tablas (p. ej. la celda 'valor' de los
    errores de importación), donde un texto demasiado largo rompe el layout.

    >>> truncate_text("hola")
    'hola'
    >>> truncate_text("x" * 80)[-3:]
    '...'
    """
    text = "" if value is None else str(value)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + suffix


def join_name_parts(*parts):
    return " ".join(part for part in parts if part)


def split_name(full_name):
    first, _, rest = (full_name or "").strip().partition(" ")
    return first, rest.strip()
