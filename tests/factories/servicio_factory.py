"""
Servicio factories para generar datos de test.

Este módulo contiene factories para el modelo Servicio.
"""

import factory
import random
from factory.django import DjangoModelFactory
from decimal import Decimal
from datetime import timedelta

from apps.services.models import Servicio
from .utils import NAIL_SERVICES, SERVICE_CATEGORIES


class ServicioFactory(DjangoModelFactory):
    """Factory para crear servicios."""

    class Meta:
        model = Servicio

    precio = factory.LazyFunction(lambda: Decimal(str(random.randint(15000, 80000))))
    descripcion = factory.Faker("text", max_nb_chars=300)
    duracion_estimada = factory.LazyFunction(
        lambda: timedelta(minutes=random.randint(30, 180))
    )
    activo = True

    @factory.LazyAttribute
    def nombre(self):
        """Generar nombres de servicios realistas."""
        return random.choice(NAIL_SERVICES)

    @factory.LazyAttribute
    def categoria(self):
        """Generar categorías realistas."""
        return random.choice(SERVICE_CATEGORIES)


class ServicioActivoFactory(ServicioFactory):
    """Factory para servicios activos."""

    activo = True


class ServicioInactivoFactory(ServicioFactory):
    """Factory para servicios inactivos."""

    activo = False
