# Documentación de la App Appointments

Esta carpeta contiene la documentación completa de la aplicación `appointments` del sistema de gestión de salón de uñas.

## Estructura de la Documentación

1. **[Modelos de Appointments](./modelo_appointments.md)** - Documentación detallada de los modelos de datos
2. **[Vistas y ViewSets](./vistas_appointments.md)** - Documentación de las vistas y endpoints de la API
3. **[URLs y Rutas](./urls_appointments.md)** - Documentación del sistema de rutas
4. **[Serializers](./serializers_appointments.md)** - Documentación de los serializadores
5. **[Administración Django](./admin_appointments.md)** - Configuración del panel de administración
6. **[Pruebas (Tests)](./tests_appointments.md)** - Documentación de las pruebas unitarias
7. **[Comandos de Gestión](./commands_appointments.md)** - Comandos personalizados de Django

## Visión General

La aplicación `appointments` es responsable de gestionar todo el sistema de citas y servicios del salón de uñas. Proporciona una API RESTful completa para administrar citas, detalles de servicios, estados de citas y toda la lógica de negocio relacionada.

### Características Principales

- **Gestión Completa de Citas**: CRUD completo con validaciones de estado
- **Detalles de Servicios**: Gestión de servicios por cita con precios y cantidades
- **Estados de Cita**: Control de flujo (PENDIENTE → CONFIRMADA → COMPLETADA/CANCELADA)
- **API RESTful**: Endpoints siguiendo estándares REST
- **Autenticación Requerida**: Todos los endpoints requieren autenticación
- **Filtros Avanzados**: Por cliente, estado, fecha, rango de fechas
- **Búsqueda**: Por cliente, observaciones y servicios
- **Endpoints Especializados**: Confirmar, cancelar, completar citas
- **Validaciones de Negocio**: Fechas, estados, permisos de modificación
- **Panel de Administración**: Interfaz administrativa con inlines

### Tecnologías Utilizadas

- **Django**: Framework web principal
- **Django REST Framework**: Para la API REST
- **Django Filters**: Para filtros avanzados
- **Factory Boy**: Para generar datos de prueba
- **Pytest**: Para pruebas unitarias

## Estructura de Archivos

```
apps/appointments/
├── models/
│   ├── __init__.py
│   ├── cita.py                 # Modelo principal de Cita
│   └── detalle_cita.py         # Modelo de DetalleCita (servicios)
├── views/
│   ├── __init__.py
│   ├── cita_views.py           # ViewSet principal de citas
│   └── detalle_cita_views.py   # ViewSet para detalles de cita
├── serializers/
│   ├── __init__.py
│   ├── cita_serializer.py      # Serializadores para citas
│   └── detalle_cita_serializer.py  # Serializadores para detalles
├── management/
│   └── commands/               # Comandos personalizados
├── migrations/                 # Migraciones de base de datos
├── admin.py                   # Configuración panel admin
├── apps.py                    # Configuración de la app
├── models.py                  # Importaciones de modelos
├── urls.py                    # Configuración de URLs
└── views.py                   # Importaciones de views

tests/appointments/
├── test_crear.py              # Tests para creación de citas
├── test_listar.py             # Tests para listado de citas
├── test_detalle.py            # Tests para detalle de citas
├── test_actualizar.py         # Tests para actualización de citas
└── test_eliminar.py           # Tests para eliminación de citas
```

## Endpoints Principales

### Citas (CitaViewSet)

| Método | URL                             | Descripción                  |
| ------ | ------------------------------- | ---------------------------- |
| GET    | `/api/v1/citas/`                | Listar todas las citas       |
| POST   | `/api/v1/citas/`                | Crear nueva cita             |
| GET    | `/api/v1/citas/{id}/`           | Obtener detalle de cita      |
| PUT    | `/api/v1/citas/{id}/`           | Actualizar cita completa     |
| PATCH  | `/api/v1/citas/{id}/`           | Actualizar cita parcial      |
| DELETE | `/api/v1/citas/{id}/`           | Eliminar cita                |
| POST   | `/api/v1/citas/{id}/confirmar/` | Confirmar cita               |
| POST   | `/api/v1/citas/{id}/cancelar/`  | Cancelar cita                |
| POST   | `/api/v1/citas/{id}/completar/` | Completar cita               |
| GET    | `/api/v1/citas/{id}/servicios/` | Obtener servicios de la cita |
| GET    | `/api/v1/citas/proximas/`       | Citas próximas (7 días)      |
| GET    | `/api/v1/citas/del_dia/`        | Citas del día actual         |

### Detalles de Cita (DetalleCitaViewSet)

| Método | URL                                               | Descripción                 |
| ------ | ------------------------------------------------- | --------------------------- |
| GET    | `/api/v1/detalles-cita/`                          | Listar detalles de citas    |
| POST   | `/api/v1/detalles-cita/`                          | Crear detalle de cita       |
| GET    | `/api/v1/detalles-cita/{id}/`                     | Obtener detalle específico  |
| PUT    | `/api/v1/detalles-cita/{id}/`                     | Actualizar detalle completo |
| PATCH  | `/api/v1/detalles-cita/{id}/`                     | Actualizar detalle parcial  |
| DELETE | `/api/v1/detalles-cita/{id}/`                     | Eliminar detalle de cita    |
| POST   | `/api/v1/detalles-cita/{id}/aplicar_descuento/`   | Aplicar descuento           |
| POST   | `/api/v1/detalles-cita/{id}/actualizar_cantidad/` | Actualizar cantidad         |

## Filtros Disponibles

### Citas

- **Por estado**: `?estado_cita=PENDIENTE`
- **Por cliente**: `?cliente=123`
- **Por rango de fechas**: `?fecha_desde=2025-08-10&fecha_hasta=2025-08-15`
- **Búsqueda en texto**: `?search=manicure`
- **Ordenamiento**: `?ordering=-fecha_hora_cita`

### Detalles de Cita

- **Por cita**: `?cita=456`
- **Por servicio**: `?servicio=789`
- **Por estado de cita**: `?cita__estado_cita=CONFIRMADA`

## Estados de Cita

La aplicación maneja un flujo de estados específico:

1. **PENDIENTE**: Estado inicial al crear la cita
2. **CONFIRMADA**: Cita confirmada por el cliente o salón
3. **COMPLETADA**: Servicio realizado exitosamente
4. **CANCELADA**: Cita cancelada por cualquier motivo

### Reglas de Negocio

- Solo se pueden **modificar** citas en estado PENDIENTE o CONFIRMADA
- Solo se pueden **eliminar** citas PENDIENTES, CONFIRMADAS o CANCELADAS (NO completadas)
- Solo se pueden **confirmar** citas PENDIENTES
- Solo se pueden **completar** citas CONFIRMADAS
- Se pueden **cancelar** citas PENDIENTES o CONFIRMADAS

## Próximos Pasos

Para una comprensión completa de la aplicación, recomendamos leer los documentos en el siguiente orden:

1. Modelos de Appointments (base de datos)
2. Serializers (transformación de datos)
3. Vistas (lógica de negocio)
4. URLs (enrutamiento)
5. Tests (validación de funcionalidad)
6. Administración (panel admin)

## Relaciones con Otras Apps

- **Clients**: Cada cita pertenece a un cliente
- **Services**: Cada detalle de cita está asociado a un servicio
- **Payments**: Las citas pueden tener pagos asociados (futura integración)
