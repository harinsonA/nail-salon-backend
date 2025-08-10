# Documentación de URLs - Sistema de Rutas Appointments

## Visión General

El sistema de URLs de la aplicación appointments utiliza Django REST Framework Routers para generar automáticamente todas las rutas RESTful necesarias. Esto proporciona un conjunto completo y consistente de endpoints para la gestión de citas y detalles de servicios.

## Archivo Principal

**Ubicación**: `apps/appointments/urls.py`

## Configuración de URLs

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.cita_views import CitaViewSet
from .views.detalle_cita_views import DetalleCitaViewSet

# Crear el router
router = DefaultRouter()
router.register(r"citas", CitaViewSet, basename="cita")
router.register(r"detalles-cita", DetalleCitaViewSet, basename="detalle-cita")

# URLs de la aplicación
urlpatterns = [
    path("", include(router.urls)),
]
```

## Componentes del Sistema

### 1. DefaultRouter

**Propósito**: Genera automáticamente todas las rutas RESTful estándar

**Configuración**:

```python
router = DefaultRouter()
```

### 2. Registro de ViewSets

#### CitaViewSet

```python
router.register(r"citas", CitaViewSet, basename="cita")
```

**Parámetros**:

- **Prefix**: `"citas"` - Base de la URL para citas
- **ViewSet**: `CitaViewSet` - Clase que maneja las vistas de citas
- **Basename**: `"cita"` - Nombre base para los patrones de URL

#### DetalleCitaViewSet

```python
router.register(r"detalles-cita", DetalleCitaViewSet, basename="detalle-cita")
```

**Parámetros**:

- **Prefix**: `"detalles-cita"` - Base de la URL para detalles
- **ViewSet**: `DetalleCitaViewSet` - Clase que maneja los detalles de servicios
- **Basename**: `"detalle-cita"` - Nombre base para los patrones de URL

## URLs Generadas Automáticamente

### Rutas para Citas (CitaViewSet)

| Método HTTP | URL Pattern    | Nombre de Vista | Descripción              |
| ----------- | -------------- | --------------- | ------------------------ |
| GET         | `/citas/`      | `cita-list`     | Listar todas las citas   |
| POST        | `/citas/`      | `cita-list`     | Crear nueva cita         |
| GET         | `/citas/{id}/` | `cita-detail`   | Obtener detalle de cita  |
| PUT         | `/citas/{id}/` | `cita-detail`   | Actualizar cita completa |
| PATCH       | `/citas/{id}/` | `cita-detail`   | Actualizar cita parcial  |
| DELETE      | `/citas/{id}/` | `cita-detail`   | Eliminar cita            |

### Rutas para Detalles de Cita (DetalleCitaViewSet)

| Método HTTP | URL Pattern            | Nombre de Vista       | Descripción                     |
| ----------- | ---------------------- | --------------------- | ------------------------------- |
| GET         | `/detalles-cita/`      | `detalle-cita-list`   | Listar todos los detalles       |
| POST        | `/detalles-cita/`      | `detalle-cita-list`   | Crear nuevo detalle de servicio |
| GET         | `/detalles-cita/{id}/` | `detalle-cita-detail` | Obtener detalle específico      |
| PUT         | `/detalles-cita/{id}/` | `detalle-cita-detail` | Actualizar detalle completo     |
| PATCH       | `/detalles-cita/{id}/` | `detalle-cita-detail` | Actualizar detalle parcial      |
| DELETE      | `/detalles-cita/{id}/` | `detalle-cita-detail` | Eliminar detalle de servicio    |

### Rutas de Acciones Personalizadas (Futuras)

| Método HTTP | URL Pattern                     | Nombre de Vista         | Descripción                  |
| ----------- | ------------------------------- | ----------------------- | ---------------------------- |
| POST        | `/citas/{id}/confirmar/`        | `cita-confirmar`        | Confirmar cita               |
| POST        | `/citas/{id}/cancelar/`         | `cita-cancelar`         | Cancelar cita                |
| POST        | `/citas/{id}/completar/`        | `cita-completar`        | Marcar cita como completada  |
| GET         | `/citas/{id}/servicios/`        | `cita-servicios`        | Obtener servicios de la cita |
| POST        | `/citas/{id}/agregar-servicio/` | `cita-agregar-servicio` | Agregar servicio a la cita   |

## Estructura Completa de URLs

### En el Contexto de la API

Cuando se incluye en el proyecto principal (`nail_salon_api/urls.py`):

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.appointments.urls')),  # URLs de appointments
    path('api/', include('apps.clients.urls')),       # URLs de clients
    # ... otras apps
]
```

**URLs Finales Resultantes**:

```
# Citas
http://localhost:8000/api/citas/                       # Lista/Crear citas
http://localhost:8000/api/citas/1/                     # Detalle/Actualizar/Eliminar cita
http://localhost:8000/api/citas/1/confirmar/           # Confirmar cita
http://localhost:8000/api/citas/1/cancelar/            # Cancelar cita
http://localhost:8000/api/citas/1/completar/           # Completar cita

# Detalles de Cita (Servicios)
http://localhost:8000/api/detalles-cita/               # Lista/Crear detalles
http://localhost:8000/api/detalles-cita/1/             # Detalle/Actualizar/Eliminar servicio
```

## Análisis Detallado de Cada Endpoint

### 1. Lista de Citas - `/citas/`

**Métodos Soportados**: GET, POST

#### GET - Listar Citas

**URL**: `GET /api/citas/`

**Parámetros de Query Soportados**:

```
?search=Juan           # Busca en nombre del cliente u observaciones
?estado=programada     # Filtra por estado específico
?cliente=1             # Filtra por ID del cliente
?fecha_cita=2024-01-15 # Filtra por fecha específica
?ordering=-fecha_cita  # Ordena por fecha (descendente)
?page=2                # Paginación
?page_size=20          # Tamaño de página personalizado
```

**Ejemplo de Respuesta**:

```json
{
  "count": 150,
  "next": "http://api/citas/?page=3",
  "previous": "http://api/citas/?page=1",
  "results": [
    {
      "id": 1,
      "cliente": {
        "id": 1,
        "nombre_completo": "Juan Pérez",
        "telefono": "3001234567"
      },
      "fecha_cita": "2024-01-20T14:30:00Z",
      "fecha_formateada": "20/01/2024 14:30",
      "estado": "programada",
      "total": "85000.00",
      "total_formateado": "$85,000",
      "observaciones": "Manicure y pedicure"
    }
  ]
}
```

#### POST - Crear Cita

**URL**: `POST /api/citas/`

**Content-Type**: `application/json`

**Ejemplo de Datos**:

```json
{
  "cliente_id": 1,
  "fecha_cita": "2024-01-25T15:00:00Z",
  "observaciones": "Cita para manicure"
}
```

### 2. Detalle de Cita - `/citas/{id}/`

**Métodos Soportados**: GET, PUT, PATCH, DELETE

#### GET - Obtener Detalle

**URL**: `GET /api/citas/1/`

**Ejemplo de Respuesta**:

```json
{
  "id": 1,
  "cliente": {
    "id": 1,
    "nombre_completo": "Juan Pérez",
    "telefono": "3001234567",
    "email": "juan@email.com"
  },
  "fecha_cita": "2024-01-20T14:30:00Z",
  "estado": "programada",
  "total": "85000.00",
  "total_formateado": "$85,000",
  "observaciones": "Manicure y pedicure",
  "fecha_creacion": "2024-01-15T10:00:00Z",
  "fecha_actualizacion": "2024-01-15T10:00:00Z",
  "detalles": [
    {
      "id": 1,
      "servicio": {
        "id": 1,
        "nombre": "Manicure Clásico",
        "precio": "45000.00"
      },
      "precio": "45000.00",
      "cantidad": 1,
      "subtotal": "45000.00",
      "subtotal_formateado": "$45,000"
    }
  ]
}
```

#### PUT - Actualizar Completo

**URL**: `PUT /api/citas/1/`

**Validaciones**:

- No se pueden modificar citas completadas o canceladas
- La fecha debe ser futura
- El cliente debe existir y estar activo

#### PATCH - Actualizar Parcial

**URL**: `PATCH /api/citas/1/`

**Ejemplo de Datos**:

```json
{
  "estado": "confirmada",
  "observaciones": "Cita confirmada por teléfono"
}
```

#### DELETE - Eliminar Cita

**URL**: `DELETE /api/citas/1/`

**Validaciones**:

- No se pueden eliminar citas completadas
- Elimina automáticamente los detalles asociados

### 3. Lista de Detalles de Cita - `/detalles-cita/`

**Métodos Soportados**: GET, POST

#### GET - Listar Detalles

**URL**: `GET /api/detalles-cita/`

**Parámetros de Query Soportados**:

```
?cita=1       # Filtra por ID de la cita
?servicio=2   # Filtra por ID del servicio
```

**Ejemplo de Respuesta**:

```json
{
  "count": 25,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "cita": 1,
      "servicio": {
        "id": 1,
        "nombre": "Manicure Clásico",
        "precio": "45000.00",
        "duracion": 60
      },
      "precio": "45000.00",
      "cantidad": 1,
      "subtotal": "45000.00",
      "subtotal_formateado": "$45,000"
    }
  ]
}
```

#### POST - Crear Detalle

**URL**: `POST /api/detalles-cita/`

**Ejemplo de Datos**:

```json
{
  "cita": 1,
  "servicio_id": 2,
  "cantidad": 1,
  "precio": "40000.00"
}
```

**Validaciones**:

- La cita debe existir y no estar completada o cancelada
- El servicio debe existir y estar activo
- El precio y cantidad deben ser positivos

### 4. Detalle de Servicio en Cita - `/detalles-cita/{id}/`

**Métodos Soportados**: GET, PUT, PATCH, DELETE

#### GET - Obtener Detalle

**URL**: `GET /api/detalles-cita/1/`

#### PUT/PATCH - Actualizar Servicio

**URL**: `PUT /api/detalles-cita/1/`

**Validaciones**:

- La cita asociada no debe estar completada o cancelada
- Los nuevos valores deben cumplir las validaciones

#### DELETE - Eliminar Servicio

**URL**: `DELETE /api/detalles-cita/1/`

**Efecto**:

- Elimina el servicio de la cita
- Recalcula automáticamente el total de la cita

## Códigos de Respuesta HTTP

### Respuestas Exitosas

| Código | Nombre     | Descripción                 | Endpoints       |
| ------ | ---------- | --------------------------- | --------------- |
| 200    | OK         | Operación exitosa           | GET, PUT, PATCH |
| 201    | Created    | Recurso creado exitosamente | POST            |
| 204    | No Content | Eliminación exitosa         | DELETE          |

### Respuestas de Error

| Código | Nombre             | Descripción              | Casos Comunes              |
| ------ | ------------------ | ------------------------ | -------------------------- |
| 400    | Bad Request        | Datos inválidos          | Validaciones de serializer |
| 401    | Unauthorized       | No autenticado           | Token inválido/faltante    |
| 403    | Forbidden          | Sin permisos             | Permisos insuficientes     |
| 404    | Not Found          | Recurso no encontrado    | ID inexistente             |
| 405    | Method Not Allowed | Método HTTP no soportado | Método incorrecto          |

## Ejemplos de Errores Comunes

### Error de Validación (400)

```json
{
  "cliente_id": ["El cliente no existe"],
  "fecha_cita": ["La fecha de la cita debe ser futura"],
  "estado": ["\"invalido\" no es una opción válida."]
}
```

### Error de Regla de Negocio (400)

```json
{
  "error": "No se puede modificar una cita completada"
}
```

### Error de Autenticación (401)

```json
{
  "detail": "Las credenciales de autenticación no se proveyeron."
}
```

### Error de Recurso No Encontrado (404)

```json
{
  "detail": "No encontrado."
}
```

## Filtros y Búsquedas Avanzadas

### Filtros por Estado

```
GET /api/citas/?estado=programada
GET /api/citas/?estado=completada
GET /api/citas/?estado=cancelada
```

### Filtros por Fecha

```
# Citas de una fecha específica
GET /api/citas/?fecha_cita=2024-01-20

# Citas de un rango de fechas (requiere filtros personalizados)
GET /api/citas/?fecha_desde=2024-01-01&fecha_hasta=2024-01-31
```

### Búsqueda de Texto

```
# Busca en nombre del cliente y observaciones
GET /api/citas/?search=Juan
GET /api/citas/?search=manicure
```

### Ordenamiento

```
# Por fecha de cita (más reciente primero)
GET /api/citas/?ordering=-fecha_cita

# Por fecha de creación (más antiguo primero)
GET /api/citas/?ordering=fecha_creacion

# Por total (mayor a menor)
GET /api/citas/?ordering=-total
```

### Combinación de Filtros

```
# Citas programadas de un cliente específico
GET /api/citas/?estado=programada&cliente=1

# Citas del día con búsqueda
GET /api/citas/?fecha_cita=2024-01-20&search=manicure
```

## Paginación

### Configuración Predeterminada

```python
# En settings.py
REST_FRAMEWORK = {
    'PAGE_SIZE': 20,
    'PAGE_SIZE_QUERY_PARAM': 'page_size',
    'MAX_PAGE_SIZE': 100
}
```

### Navegación de Páginas

```
# Primera página (por defecto)
GET /api/citas/

# Página específica
GET /api/citas/?page=2

# Tamaño de página personalizado
GET /api/citas/?page_size=50

# Máximo permitido
GET /api/citas/?page_size=100
```

## Consideraciones de Rendimiento

### Optimizaciones Implementadas

1. **Select Related**: Evita N+1 queries en relaciones
2. **Paginación**: Limita la cantidad de datos por respuesta
3. **Serializers Diferenciados**: Usa datos mínimos en listados
4. **Filtros en Base de Datos**: Aplica filtros a nivel de SQL

### Recomendaciones de Uso

1. **Usar filtros**: Siempre que sea posible para reducir datos
2. **Paginación apropiada**: No solicitar más datos de los necesarios
3. **Serializers específicos**: Usar el endpoint apropiado para cada caso
4. **Caché**: Implementar caché en consultas frecuentes (futuro)

## Versionado de API

### Estructura Actual

```
/api/citas/              # Versión actual
/api/detalles-cita/      # Versión actual
```

### Preparación para Futuras Versiones

```
/api/v1/citas/           # Versión 1 explícita
/api/v2/citas/           # Versión 2 (cambios breaking)
```

## Documentación Automática

### URLs de Documentación

```
# Documentación interactiva (Swagger)
http://localhost:8000/api/docs/

# Documentación ReDoc
http://localhost:8000/api/redoc/

# Schema JSON
http://localhost:8000/api/schema/
```

### Metadatos de API

```python
# En CitaViewSet
class CitaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar citas del salon de uñas.

    Proporciona operaciones CRUD completas para citas,
    incluyendo validaciones de estado y reglas de negocio.
    """
```

Esta documentación de URLs proporciona una referencia completa para desarrolladores frontend y usuarios de la API, facilitando la integración y el uso correcto de todos los endpoints disponibles.
