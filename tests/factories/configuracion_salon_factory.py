"""
Configuracion Salon factories para generar datos de test.

Este módulo contiene factories para el modelo ConfiguracionSalon.
"""

import factory
from factory.django import DjangoModelFactory
from factory import Faker

from apps.settings.models import ConfiguracionSalon


class ConfiguracionSalonFactory(DjangoModelFactory):
    """Factory para crear configuración del salón."""

    class Meta:
        model = ConfiguracionSalon
        django_get_or_create = ("nombre_salon",)

    nombre_salon = "Salón de Test"
    direccion = Faker("address", locale="es_ES")
    telefono = factory.LazyAttribute(
        lambda o: f"601{factory.Faker('random_int', min=2000000, max=9999999).generate()}"
    )
    email = Faker("company_email")
    descripcion = Faker("text", max_nb_chars=500)
