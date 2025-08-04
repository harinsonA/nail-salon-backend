"""
Cliente factories para generar datos de test.

Este módulo contiene factories para el modelo Cliente.
"""

import factory
from factory.django import DjangoModelFactory
from factory import Faker

from apps.clients.models import Cliente


class ClienteFactory(DjangoModelFactory):
    """Factory para crear clientes."""

    class Meta:
        model = Cliente
        django_get_or_create = ("email",)

    nombre = Faker("first_name", locale="es_ES")
    apellido = Faker("last_name", locale="es_ES")
    email = Faker("email")
    activo = True
    notas = Faker("text", max_nb_chars=200)

    @factory.LazyAttribute
    def telefono(self):
        """Generar teléfono con formato colombiano."""
        import random

        return f"300{random.randint(1000000, 9999999)}"


class ClienteActivoFactory(ClienteFactory):
    """Factory para clientes activos."""

    activo = True


class ClienteInactivoFactory(ClienteFactory):
    """Factory para clientes inactivos."""

    activo = False


class ClienteConCitasFactory(ClienteFactory):
    """Factory para cliente con citas asociadas."""

    @factory.PostGeneration
    def citas(self, create, extracted, **kwargs):
        """Crear citas asociadas al cliente."""
        if not create:
            return

        # Import lazy para evitar dependencias circulares
        from .cita_factory import CitaFactory

        citas_count = extracted or 3
        for _ in range(citas_count):
            CitaFactory(cliente=self)
