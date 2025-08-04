"""
Detalle Cita factories para generar datos de test.

Este módulo contiene factories para el modelo DetalleCita.
"""

import factory
from factory.django import DjangoModelFactory
from factory import Faker
from decimal import Decimal

from apps.appointments.models import DetalleCita


class DetalleCitaFactory(DjangoModelFactory):
    """Factory para crear detalles de cita."""

    class Meta:
        model = DetalleCita

    # Las relaciones se asignarán dinámicamente para evitar dependencias circulares
    cita = factory.LazyAttribute(lambda o: None)
    servicio = factory.LazyAttribute(lambda o: None)
    descuento = Decimal("0.00")
    notas_detalle = Faker("text", max_nb_chars=150)

    @factory.LazyAttribute
    def precio_acordado(self):
        """Usar el precio del servicio por defecto."""
        if self.servicio:
            return self.servicio.precio
        # Valor por defecto si no hay servicio
        return Decimal("25000.00")

    @factory.LazyAttribute
    def cantidad_servicios(self):
        """Generar cantidad realista."""
        return factory.Faker("random_int", min=1, max=3).generate()

    @factory.PostGeneration
    def setup_relations(self, create, extracted, **kwargs):
        """Configurar relaciones si no se proporcionan."""
        if not create:
            return

        # Configurar cita si no se proporciona
        if not self.cita:
            from .cita_factory import CitaFactory

            self.cita = CitaFactory()

        # Configurar servicio si no se proporciona
        if not self.servicio:
            from .servicio_factory import ServicioFactory

            self.servicio = ServicioFactory()

        # Actualizar precio acordado
        if self.servicio:
            self.precio_acordado = self.servicio.precio

        self.save()
