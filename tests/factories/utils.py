"""
Utilidades y helpers para factories.

Este módulo contiene funciones de ayuda y secuencias para generar
datos únicos en las factories.
"""

import factory
from datetime import timedelta
from django.utils import timezone


class FactorySequenceHelper:
    """Helpers para crear secuencias y datos únicos."""

    @staticmethod
    def unique_email_sequence():
        """Generar secuencia de emails únicos."""
        return factory.Sequence(lambda n: f"test.user.{n}@example.com")

    @staticmethod
    def unique_phone_sequence():
        """Generar secuencia de teléfonos únicos."""
        return factory.Sequence(lambda n: f"300{str(n).zfill(7)}")

    @staticmethod
    def future_datetime_sequence(days_ahead=1):
        """Generar secuencia de fechas futuras."""
        return factory.Sequence(
            lambda n: timezone.now() + timedelta(days=days_ahead, hours=n % 24)
        )


# Utilidades para datos realistas
NAIL_SERVICES = [
    "Manicure Clásico",
    "Pedicure Spa",
    "Esmaltado Gel",
    "Decoración de Uñas",
    "Tratamiento de Cutículas",
    "Manicure Express",
    "Pedicure Medicinal",
    "Uñas Acrílicas",
    "Extensión de Uñas",
    "Nail Art",
]

SERVICE_CATEGORIES = [
    "Manicure",
    "Pedicure",
    "Decoración",
    "Tratamientos",
    "Extensiones",
]

APPOINTMENT_STATES = [
    "PENDIENTE",
    "CONFIRMADA",
    "CANCELADA",
    "COMPLETADA",
]

PAYMENT_METHODS = ["EFECTIVO", "TARJETA", "TRANSFERENCIA", "CHEQUE"]

PAYMENT_STATES = ["PENDIENTE", "PAGADO", "CANCELADO"]
