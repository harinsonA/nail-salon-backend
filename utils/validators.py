from django.core.exceptions import ValidationError
import re


def validate_telefono(value):
    """
    Validador para números de teléfono.
    Acepta formatos como: +57 300 123 4567, 300-123-4567, 3001234567
    """
    # Remover espacios, guiones y paréntesis
    clean_phone = re.sub(r"[\s\-\(\)]+", "", value)

    # Validar que solo contenga números y opcionalmente un + al inicio
    if not re.match(r"^\+?\d{7,15}$", clean_phone):
        raise ValidationError(
            "El número de teléfono debe contener entre 7 y 15 dígitos y puede incluir un + al inicio."
        )


def validate_precio_positivo(value):
    """
    Validador para precios que deben ser no negativos.
    """
    if value < 0:
        raise ValidationError("El precio debe ser mayor o igual a 0.")


def validate_duracion_positiva(value):
    """
    Validador para duraciones que deben ser positivas.
    """
    if value.total_seconds() <= 0:
        raise ValidationError("La duración debe ser mayor a 0.")
