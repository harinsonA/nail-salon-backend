"""
Cita factories para generar datos de test.

Este módulo contiene factories para el modelo Cita.
"""

import factory
from factory.django import DjangoModelFactory
from factory import Faker
from datetime import timedelta
from django.utils import timezone

from apps.appointments.models import Cita
from .utils import APPOINTMENT_STATES


class CitaFactory(DjangoModelFactory):
    """Factory para crear citas."""

    class Meta:
        model = Cita

    # Import lazy para evitar dependencias circulares
    cliente = factory.LazyAttribute(lambda o: None)  # Se asignará dinámicamente

    @factory.LazyAttribute
    def fecha_hora_cita(self):
        """Generar fecha futura para la cita."""
        import random

        days_ahead = random.randint(1, 30)
        hour = random.randint(8, 18)
        return timezone.now() + timedelta(days=days_ahead, hours=hour)

    observaciones = Faker("text", max_nb_chars=200)

    @factory.LazyAttribute
    def estado_cita(self):
        """Generar estados realistas."""
        import random

        return random.choice(APPOINTMENT_STATES)

    @factory.PostGeneration
    def setup_cliente(self, create, extracted, **kwargs):
        """Configurar cliente si no se proporciona."""
        if not create:
            return

        if not self.cliente:
            # Import lazy para evitar dependencias circulares
            from .cliente_factory import ClienteFactory

            self.cliente = ClienteFactory()
            self.save()


class CitaProgramadaFactory(CitaFactory):
    """Factory para citas programadas."""

    estado_cita = "programada"
    fecha_hora_cita = factory.LazyFunction(lambda: timezone.now() + timedelta(days=1))


class CitaCompletadaFactory(CitaFactory):
    """Factory para citas completadas."""

    estado = "completada"
    fecha_hora_cita = factory.LazyFunction(lambda: timezone.now() - timedelta(days=1))


class CitaCanceladaFactory(CitaFactory):
    """Factory para citas canceladas."""

    estado = "cancelada"
    fecha_hora_cita = factory.LazyFunction(lambda: timezone.now() + timedelta(days=1))


class CitaConServiciosFactory(CitaFactory):
    """Factory para cita con servicios asociados."""

    @factory.PostGeneration
    def servicios(self, create, extracted, **kwargs):
        """Crear servicios asociados a la cita."""
        if not create:
            return

        # Import lazy para evitar dependencias circulares
        from .detalle_cita_factory import DetalleCitaFactory

        servicios_count = extracted or 2
        for _ in range(servicios_count):
            DetalleCitaFactory(cita=self)


class CitaCompletaFactory(CitaFactory):
    """Factory para crear una cita completa con todos los datos relacionados."""

    @factory.PostGeneration
    def setup_complete_cita(self, create, extracted, **kwargs):
        """Configurar cita completa con servicios y pago."""
        if not create:
            return

        # Import lazy para evitar dependencias circulares
        from .detalle_cita_factory import DetalleCitaFactory
        from .pago_factory import PagoFactory

        # Crear servicios para la cita
        servicio1 = DetalleCitaFactory(cita=self)
        servicio2 = DetalleCitaFactory(cita=self)

        # Calcular monto total
        monto_total = servicio1.precio_acordado + servicio2.precio_acordado

        # Crear pago
        PagoFactory(cita=self, monto_total=monto_total)
