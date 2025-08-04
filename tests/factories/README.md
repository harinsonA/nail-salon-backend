# Factories Package

Este paquete contiene factories organizadas para generar datos de test usando Factory Boy. Las factories están separadas por modelo para mantener el código limpio y fácil de mantener.

## Estructura

```
tests/factories/
├── __init__.py                     # Exports principales
├── utils.py                        # Utilidades y constantes
├── user_factory.py                 # Factories para User
├── cliente_factory.py              # Factories para Cliente
├── servicio_factory.py             # Factories para Servicio
├── cita_factory.py                 # Factories para Cita
├── detalle_cita_factory.py         # Factories para DetalleCita
├── pago_factory.py                 # Factories para Pago
└── configuracion_salon_factory.py  # Factories para ConfiguracionSalon
```

## Uso Básico

### Importar factories

```python
# Importar factories individuales
from tests.factories import ClienteFactory, ServicioFactory, CitaFactory

# Importar todas las factories
from tests.factories import *
```

### Crear datos de test

```python
# Crear un cliente básico
cliente = ClienteFactory()

# Crear un cliente con datos específicos
cliente = ClienteFactory(nombre='Juan', email='juan@test.com')

# Crear múltiples clientes
clientes = ClienteFactory.create_batch(5)

# Crear cliente activo/inactivo
cliente_activo = ClienteActivoFactory()
cliente_inactivo = ClienteInactivoFactory()
```

### Factories Especializadas

```python
# Citas con estados específicos
cita_programada = CitaProgramadaFactory()
cita_completada = CitaCompletadaFactory()
cita_cancelada = CitaCanceladaFactory()

# Servicios activos/inactivos
servicio_activo = ServicioActivoFactory()
servicio_inactivo = ServicioInactivoFactory()

# Citas con servicios asociados
cita_con_servicios = CitaConServiciosFactory(servicios=3)  # 3 servicios

# Cliente con citas asociadas
cliente_con_citas = ClienteConCitasFactory(citas=5)  # 5 citas

# Cita completa (con servicios y pago)
cita_completa = CitaCompletaFactory()
```

### Evitar Dependencias Circulares

Las factories están diseñadas para evitar dependencias circulares. Las relaciones se configuran dinámicamente:

```python
# Crear cita con cliente específico
cliente = ClienteFactory()
cita = CitaFactory(cliente=cliente)

# Crear detalle de cita con servicio específico
servicio = ServicioFactory()
cita = CitaFactory()
detalle = DetalleCitaFactory(cita=cita, servicio=servicio)
```

### Utilizar Helpers

```python
from tests.factories.utils import FactorySequenceHelper

# Emails únicos
email_sequence = FactorySequenceHelper.unique_email_sequence()

# Teléfonos únicos
phone_sequence = FactorySequenceHelper.unique_phone_sequence()

# Fechas futuras
future_dates = FactorySequenceHelper.future_datetime_sequence(days_ahead=7)
```

## Factories Disponibles

### User Factories

- `UserFactory`: Usuario básico
- `AdminUserFactory`: Usuario administrador

### Cliente Factories

- `ClienteFactory`: Cliente básico
- `ClienteActivoFactory`: Cliente activo
- `ClienteInactivoFactory`: Cliente inactivo
- `ClienteConCitasFactory`: Cliente con citas asociadas

### Servicio Factories

- `ServicioFactory`: Servicio básico
- `ServicioActivoFactory`: Servicio activo
- `ServicioInactivoFactory`: Servicio inactivo

### Cita Factories

- `CitaFactory`: Cita básica
- `CitaProgramadaFactory`: Cita programada
- `CitaCompletadaFactory`: Cita completada
- `CitaCanceladaFactory`: Cita cancelada
- `CitaConServiciosFactory`: Cita con servicios asociados
- `CitaCompletaFactory`: Cita completa (con servicios y pago)

### Otras Factories

- `DetalleCitaFactory`: Detalle de cita
- `PagoFactory`: Pago
- `ConfiguracionSalonFactory`: Configuración del salón

## Ejemplo de Test Completo

```python
from django.test import TestCase
from tests.factories import *

class TestCitaCompleta(TestCase):
    def test_crear_cita_completa(self):
        # Crear datos relacionados
        cliente = ClienteFactory(nombre='Ana', email='ana@test.com')
        servicio = ServicioFactory(nombre_servicio='Manicure Clásico', precio=25000)

        # Crear cita con datos específicos
        cita = CitaFactory(
            cliente=cliente,
            estado='programada'
        )

        # Agregar servicios a la cita
        detalle1 = DetalleCitaFactory(cita=cita, servicio=servicio)
        detalle2 = DetalleCitaFactory(cita=cita, servicio=ServicioFactory())

        # Crear pago
        pago = PagoFactory(
            cita=cita,
            monto_total=detalle1.precio_acordado + detalle2.precio_acordado
        )

        # Verificaciones
        self.assertEqual(cita.cliente.nombre, 'Ana')
        self.assertEqual(cita.detallecita_set.count(), 2)
        self.assertTrue(cita.pago_set.exists())
```

## Migración del Archivo Anterior

Si tenías factories en `tests/factories.py`, puedes actualizar los imports:

```python
# Antes
from tests.factories import ClienteFactory

# Después (funciona igual)
from tests.factories import ClienteFactory
```

El archivo `__init__.py` exporta todas las factories, por lo que el código existente seguirá funcionando sin cambios.
