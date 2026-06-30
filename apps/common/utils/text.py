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
