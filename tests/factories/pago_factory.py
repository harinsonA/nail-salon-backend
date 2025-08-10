"""
Pago factories para generar datos de test.

Este módulo contiene factories para el modelo Pago.
"""

import factory
from factory.django import DjangoModelFactory
from factory import Faker
from decimal import Decimal
from django.utils import timezone

from apps.payments.models import Pago
from .utils import PAYMENT_METHODS, PAYMENT_STATES


class PagoFactory(DjangoModelFactory):
    """Factory para crear pagos."""

    class Meta:
        model = Pago

    # La relación se asignará dinámicamente para evitar dependencias circulares
    cita = factory.LazyAttribute(lambda o: None)
    fecha_pago = factory.LazyFunction(timezone.now)
    referencia_pago = Faker("uuid4")
    notas_pago = Faker("text", max_nb_chars=100)

    @factory.LazyAttribute
    def monto_total(self):
        """Calcular monto basado en servicios de la cita."""
        # Por simplicidad, usar un monto aleatorio realista
        import random

        return Decimal(str(random.randint(20000, 100000)))

    @factory.LazyAttribute
    def metodo_pago(self):
        """Generar métodos de pago realistas."""
        import random

        return random.choice(PAYMENT_METHODS)

    @factory.LazyAttribute
    def estado_pago(self):
        """Generar estados de pago realistas."""
        return factory.Faker("random_element", elements=PAYMENT_STATES).generate()

    @factory.PostGeneration
    def setup_cita(self, create, extracted, **kwargs):
        """Configurar cita si no se proporciona."""
        if not create:
            return

        if not self.cita:
            # Import lazy para evitar dependencias circulares
            from .cita_factory import CitaFactory

            self.cita = CitaFactory()
            self.save()
