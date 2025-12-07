"""
Utilidades base para tests del proyecto nail-salon-backend.

Este módulo contiene:
- Utilidades generales para tests
- Helpers comunes para validaciones
- Factories para crear datos de test
"""

from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

# Obtener el modelo de usuario personalizado
User = get_user_model()

# Importar modelos
from apps.clients.models import Cliente
from apps.services.models import Servicio
from apps.appointments.models import Cita

# Importar factories organizadas
from tests.factories import (
    UserFactory,
    AdminUserFactory,
    ClienteFactory,
    ServicioFactory,
    CitaFactory,
    DetalleCitaFactory,
    PagoFactory,
)


# ===========================================
# HELPERS PARA CREAR DATOS DE TEST
# ===========================================


def create_cliente_data(**kwargs):
    """
    Crear datos válidos para un cliente.

    Args:
        **kwargs: Campos a sobrescribir

    Returns:
        dict: Datos del cliente
    """
    base_data = {
        "nombre": "Juan",
        "apellido": "Pérez",
        "telefono": "3001234567",
        "email": f"juan.perez.{timezone.now().timestamp()}@test.com",
        "activo": True,
        "notas": "Cliente de test",
    }
    base_data.update(kwargs)
    return base_data


def create_cliente(**kwargs):
    """
    Crear un cliente en la base de datos.

    Args:
        **kwargs: Campos a sobrescribir

    Returns:
        Cliente: Instancia del cliente creado
    """
    data = create_cliente_data(**kwargs)
    return Cliente.objects.create(**data)


def create_servicio_data(**kwargs):
    """
    Crear datos válidos para un servicio.

    Args:
        **kwargs: Campos a sobrescribir

    Returns:
        dict: Datos del servicio
    """
    base_data = {
        "nombre": "Manicure Test",
        "precio": Decimal("25000.00"),
        "descripcion": "Servicio de test",
        "duracion_estimada": timedelta(hours=1),
        "activo": True,
        "categoria": "Test",
    }
    base_data.update(kwargs)
    return base_data


def create_servicio(**kwargs):
    """
    Crear un servicio en la base de datos.

    Args:
        **kwargs: Campos a sobrescribir

    Returns:
        Servicio: Instancia del servicio creado
    """
    data = create_servicio_data(**kwargs)
    return Servicio.objects.create(**data)


def create_cita_data(cliente=None, **kwargs):
    """
    Crear datos válidos para una cita.

    Args:
        cliente: Instancia del cliente (se crea uno si no se proporciona)
        **kwargs: Campos a sobrescribir

    Returns:
        dict: Datos de la cita
    """
    if cliente is None:
        cliente = create_cliente()

    base_data = {
        "cliente": cliente,
        "fecha_agenda": timezone.now() + timedelta(days=1),
        "estado": "programada",
        "notas": "Cita de test",
    }
    base_data.update(kwargs)
    return base_data


def create_cita(cliente=None, **kwargs):
    """
    Crear una cita en la base de datos.

    Args:
        cliente: Instancia del cliente (se crea uno si no se proporciona)
        **kwargs: Campos a sobrescribir

    Returns:
        Cita: Instancia de la cita creada
    """
    data = create_cita_data(cliente=cliente, **kwargs)
    return Cita.objects.create(**data)
