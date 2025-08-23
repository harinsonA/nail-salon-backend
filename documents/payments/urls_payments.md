# Documentación de URLs - Payments App

## Visión General

La aplicación payments define sus rutas URL siguiendo las convenciones de Django REST Framework para APIs RESTful. Las URLs están organizadas de manera jerárquica y proporcionan endpoints para todas las operaciones CRUD de pagos.

## Archivos de URLs

### Estructura de Archivos

```
apps/payments/
├── urls.py                 # URLs principales de la app
└── api/
    └── urls.py            # URLs específicas de la API
```

## URLs Principales (`apps/payments/urls.py`)

### Configuración Base

```python
from django.urls import path, include

app_name = 'payments'

urlpatterns = [
    # API URLs
    path('api/', include('apps.payments.api.urls')),

    # URLs adicionales para futuras funcionalidades
    # path('reports/', include('apps.payments.reports.urls')),
    # path('exports/', include('apps.payments.exports.urls')),
]
```

### Namespace y Organización

- **App Name**: `payments`
- **Prefijo API**: `api/`
- **Versionado**: Preparado para futuras versiones
- **Modularidad**: Separación clara entre API y otras funcionalidades

## URLs de API (`apps/payments/api/urls.py`)

### Configuración del Router

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.payments.views.pago_views import PagoViewSet

# Router para ViewSets
router = DefaultRouter()
router.register(r'pagos', PagoViewSet, basename='pago')

urlpatterns = [
    # URLs del router (ViewSet)
    path('', include(router.urls)),

    # URLs personalizadas adicionales
    path('estadisticas/', EstadisticasPagosView.as_view(), name='estadisticas-pagos'),
    path('reportes/', ReportesPagosView.as_view(), name='reportes-pagos'),
]
```

### ViewSet Router URLs

El `DefaultRouter` genera automáticamente las siguientes URLs:

| Acción   | Método | URL Pattern        | Nombre                 | Descripción              |
| -------- | ------ | ------------------ | ---------------------- | ------------------------ |
| List     | GET    | `/api/pagos/`      | `payments:pago-list`   | Listar todos los pagos   |
| Create   | POST   | `/api/pagos/`      | `payments:pago-list`   | Crear nuevo pago         |
| Retrieve | GET    | `/api/pagos/{id}/` | `payments:pago-detail` | Obtener pago específico  |
| Update   | PUT    | `/api/pagos/{id}/` | `payments:pago-detail` | Actualizar pago completo |
| Partial  | PATCH  | `/api/pagos/{id}/` | `payments:pago-detail` | Actualizar pago parcial  |
| Destroy  | DELETE | `/api/pagos/{id}/` | `payments:pago-detail` | Eliminar pago            |

## URLs Detalladas

### 1. Listar y Crear Pagos

**URL**: `/api/payments/api/pagos/`

#### GET - Listar Pagos

```bash
# Listar todos los pagos
GET /api/payments/api/pagos/

# Con filtros
GET /api/payments/api/pagos/?estado_pago=PAGADO&metodo_pago=EFECTIVO

# Con paginación
GET /api/payments/api/pagos/?page=2&page_size=20

# Con ordenamiento
GET /api/payments/api/pagos/?ordering=-fecha_pago

# Con búsqueda
GET /api/payments/api/pagos/?search=adelanto
```

**Parámetros de Query Soportados**:

| Parámetro      | Tipo    | Descripción                  | Ejemplo                                          |
| -------------- | ------- | ---------------------------- | ------------------------------------------------ |
| `estado_pago`  | String  | Filtrar por estado           | `PAGADO`, `PENDIENTE`, `CANCELADO`               |
| `metodo_pago`  | String  | Filtrar por método           | `EFECTIVO`, `TARJETA`, `TRANSFERENCIA`, `CHEQUE` |
| `cita`         | Integer | Filtrar por ID de cita       | `123`                                            |
| `fecha_desde`  | Date    | Fecha mínima (YYYY-MM-DD)    | `2025-01-01`                                     |
| `fecha_hasta`  | Date    | Fecha máxima (YYYY-MM-DD)    | `2025-12-31`                                     |
| `monto_minimo` | Decimal | Monto mínimo                 | `10000.00`                                       |
| `monto_maximo` | Decimal | Monto máximo                 | `100000.00`                                      |
| `search`       | String  | Búsqueda en notas/referencia | `adelanto`                                       |
| `ordering`     | String  | Campo de ordenamiento        | `-fecha_pago`, `monto_total`                     |
| `page`         | Integer | Número de página             | `2`                                              |
| `page_size`    | Integer | Elementos por página         | `50`                                             |

#### POST - Crear Pago

```bash
POST /api/payments/api/pagos/
Content-Type: application/json

{
  "cita": 456,
  "monto_total": "25000.00",
  "metodo_pago": "TARJETA",
  "estado_pago": "PENDIENTE",
  "referencia_pago": "TXN-123456",
  "notas_pago": "Pago con tarjeta de crédito"
}
```

### 2. Operaciones Específicas de Pago

**URL**: `/api/payments/api/pagos/{id}/`

#### GET - Obtener Detalle

```bash
# Obtener pago específico
GET /api/payments/api/pagos/123/
```

#### PUT - Actualización Completa

```bash
PUT /api/payments/api/pagos/123/
Content-Type: application/json

{
  "cita": 456,
  "fecha_pago": "2025-08-23T14:30:00Z",
  "monto_total": "25000.00",
  "metodo_pago": "EFECTIVO",
  "estado_pago": "PAGADO",
  "referencia_pago": null,
  "notas_pago": "Pago actualizado a efectivo"
}
```

#### PATCH - Actualización Parcial

```bash
PATCH /api/payments/api/pagos/123/
Content-Type: application/json

{
  "estado_pago": "PAGADO",
  "notas_pago": "Pago confirmado"
}
```

#### DELETE - Eliminar Pago

```bash
DELETE /api/payments/api/pagos/123/
```

## URLs Personalizadas Adicionales

### 1. Estadísticas de Pagos

**URL**: `/api/payments/api/estadisticas/`

```python
# En apps/payments/api/urls.py
path('estadisticas/', EstadisticasPagosView.as_view(), name='estadisticas-pagos'),
```

**Uso**:

```bash
# Estadísticas generales
GET /api/payments/api/estadisticas/

# Estadísticas por período
GET /api/payments/api/estadisticas/?fecha_desde=2025-08-01&fecha_hasta=2025-08-31

# Estadísticas por método de pago
GET /api/payments/api/estadisticas/?metodo_pago=EFECTIVO
```

**Respuesta Ejemplo**:

```json
{
  "total_pagos": 150,
  "total_monto": "3750000.00",
  "pagos_por_estado": {
    "PAGADO": 120,
    "PENDIENTE": 25,
    "CANCELADO": 5
  },
  "pagos_por_metodo": {
    "EFECTIVO": 80,
    "TARJETA": 45,
    "TRANSFERENCIA": 20,
    "CHEQUE": 5
  },
  "promedio_pago": "25000.00",
  "monto_por_metodo": {
    "EFECTIVO": "2000000.00",
    "TARJETA": "1125000.00",
    "TRANSFERENCIA": "500000.00",
    "CHEQUE": "125000.00"
  }
}
```

### 2. Reportes de Pagos

**URL**: `/api/payments/api/reportes/`

```python
# En apps/payments/api/urls.py
path('reportes/', ReportesPagosView.as_view(), name='reportes-pagos'),
```

**Uso**:

```bash
# Reporte general
GET /api/payments/api/reportes/

# Reporte por período
GET /api/payments/api/reportes/?fecha_desde=2025-08-01&fecha_hasta=2025-08-31&formato=excel

# Reporte por cliente
GET /api/payments/api/reportes/?cliente=123&formato=pdf
```

**Parámetros Soportados**:

| Parámetro     | Tipo    | Descripción              | Valores Permitidos           |
| ------------- | ------- | ------------------------ | ---------------------------- |
| `fecha_desde` | Date    | Fecha inicio del reporte | YYYY-MM-DD                   |
| `fecha_hasta` | Date    | Fecha fin del reporte    | YYYY-MM-DD                   |
| `cliente`     | Integer | ID del cliente           | ID numérico                  |
| `metodo_pago` | String  | Método de pago           | EFECTIVO, TARJETA, etc.      |
| `estado_pago` | String  | Estado del pago          | PAGADO, PENDIENTE, CANCELADO |
| `formato`     | String  | Formato del reporte      | json, excel, pdf             |

## Configuración en URLs Principales

### En `nail_salon_api/urls.py`

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Apps URLs
    path('api/appointments/', include('apps.appointments.urls')),
    path('api/clients/', include('apps.clients.urls')),
    path('api/payments/', include('apps.payments.urls')),  # URLs de payments
    path('api/services/', include('apps.services.urls')),
    path('api/settings/', include('apps.settings.urls')),
    path('api/authentication/', include('apps.authentication.urls')),

    # API Root
    path('api/', include('apps.core.urls')),
]
```

### URLs Completas de la Aplicación

Todas las URLs de payments son accesibles bajo el prefijo `/api/payments/`:

```
/api/payments/api/pagos/                     # Lista/Crear pagos
/api/payments/api/pagos/{id}/                # Detalle/Actualizar/Eliminar pago
/api/payments/api/estadisticas/              # Estadísticas de pagos
/api/payments/api/reportes/                  # Reportes de pagos
```

## Resolución de URLs

### Usando Django's reverse()

```python
from django.urls import reverse

# URLs del ViewSet
list_url = reverse('payments:pago-list')
# Resultado: '/api/payments/api/pagos/'

detail_url = reverse('payments:pago-detail', kwargs={'pk': 123})
# Resultado: '/api/payments/api/pagos/123/'

# URLs personalizadas
stats_url = reverse('payments:estadisticas-pagos')
# Resultado: '/api/payments/api/estadisticas/'
```

### Usando Django REST Framework's reverse()

```python
from rest_framework.reverse import reverse

# En un ViewSet o Serializer
def get_absolute_url(self, request=None):
    return reverse('payments:pago-detail',
                  kwargs={'pk': self.pk},
                  request=request)
```

## Middleware y Configuración

### CORS Configuration

Para permitir acceso desde el frontend:

```python
# En settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Frontend local
    "https://mi-salon.com",   # Producción
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
```

### Authentication en URLs

Todas las URLs de payments requieren autenticación:

```python
# En settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

### Headers Requeridos

Para acceder a las APIs:

```bash
# Header de autenticación
Authorization: Token abc123def456ghi789

# Header de contenido (para POST/PUT/PATCH)
Content-Type: application/json

# Header opcional para identificar la aplicación
User-Agent: SalonApp/1.0
```

## Testing de URLs

### Ejemplos de Pruebas

```python
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

class PagoURLsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Setup de usuario y autenticación

    def test_pago_list_url(self):
        url = reverse('payments:pago-list')
        self.assertEqual(url, '/api/payments/api/pagos/')

    def test_pago_detail_url(self):
        url = reverse('payments:pago-detail', kwargs={'pk': 123})
        self.assertEqual(url, '/api/payments/api/pagos/123/')

    def test_estadisticas_url(self):
        url = reverse('payments:estadisticas-pagos')
        self.assertEqual(url, '/api/payments/api/estadisticas/')
```

## Versionado de API

### Preparación para Versiones Futuras

```python
# Estructura preparada para versionado
urlpatterns = [
    # Versión actual (v1 implícita)
    path('api/', include('apps.payments.api.urls')),

    # Futuras versiones
    # path('api/v2/', include('apps.payments.api.v2.urls')),
    # path('api/v3/', include('apps.payments.api.v3.urls')),
]
```

### Headers de Versión

```bash
# Header opcional para especificar versión
Accept: application/json; version=1.0

# O usando query parameter
GET /api/payments/api/pagos/?version=1.0
```

## Documentación de API

### Swagger/OpenAPI

Las URLs están documentadas automáticamente:

```bash
# Documentación interactiva
GET /api/docs/

# Schema OpenAPI
GET /api/schema/
```

### Metadatos de Endpoints

Cada endpoint incluye metadatos:

```json
{
  "name": "Pago List",
  "description": "Lista paginada de pagos con filtros y búsqueda",
  "renders": ["application/json"],
  "parses": ["application/json"],
  "actions": {
    "POST": {
      "cita": { "type": "integer", "required": true },
      "monto_total": { "type": "decimal", "required": true }
    }
  }
}
```

---

**Última actualización**: Agosto 2025  
**Versión**: 1.0  
**Estado**: ✅ Completamente configurado y funcional
