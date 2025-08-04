"""
Factories package para generar datos de test.

Este paquete contiene factories organizadas por modelo para mantener
el código limpio y fácil de mantener.
"""

# Importar todas las factories para facilitar el uso
from .user_factory import UserFactory, AdminUserFactory
from .cliente_factory import (
    ClienteFactory,
    ClienteActivoFactory,
    ClienteInactivoFactory,
    ClienteConCitasFactory,
)
from .servicio_factory import (
    ServicioFactory,
    ServicioActivoFactory,
    ServicioInactivoFactory,
)
from .cita_factory import (
    CitaFactory,
    CitaProgramadaFactory,
    CitaCompletadaFactory,
    CitaCanceladaFactory,
    CitaConServiciosFactory,
    CitaCompletaFactory,
)
from .detalle_cita_factory import DetalleCitaFactory
from .pago_factory import PagoFactory
from .configuracion_salon_factory import ConfiguracionSalonFactory
from .utils import FactorySequenceHelper

__all__ = [
    # User factories
    "UserFactory",
    "AdminUserFactory",
    # Cliente factories
    "ClienteFactory",
    "ClienteActivoFactory",
    "ClienteInactivoFactory",
    "ClienteConCitasFactory",
    # Servicio factories
    "ServicioFactory",
    "ServicioActivoFactory",
    "ServicioInactivoFactory",
    # Cita factories
    "CitaFactory",
    "CitaProgramadaFactory",
    "CitaCompletadaFactory",
    "CitaCanceladaFactory",
    "CitaConServiciosFactory",
    "CitaCompletaFactory",
    # Detalle cita factories
    "DetalleCitaFactory",
    # Pago factories
    "PagoFactory",
    # Configuracion salon factories
    "ConfiguracionSalonFactory",
    # Utilities
    "FactorySequenceHelper",
]
