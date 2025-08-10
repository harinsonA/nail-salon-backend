# Documentación de URLs - Sistema de Rutas

## Visión General

El sistema de URLs de la aplicación clients utiliza Django REST Framework Routers para generar automáticamente todas las rutas RESTful necesarias. Esto proporciona un conjunto completo y consistente de endpoints para la gestión de clientes.

## Archivo Principal

**Ubicación**: `apps/clients/urls.py`

## Configuración de URLs

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.cliente_views import ClienteViewSet

# Crear el router
router = DefaultRouter()
router.register(r"clientes", ClienteViewSet, basename="cliente")

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

### 2. Registro del ViewSet

```python
router.register(r"clientes", ClienteViewSet, basename="cliente")
```

**Parámetros**:

- **Prefix**: `"clientes"` - Base de la URL
- **ViewSet**: `ClienteViewSet` - Clase que maneja las vistas
- **Basename**: `"cliente"` - Nombre base para los patrones de URL

## URLs Generadas Automáticamente

### Rutas Estándar (ModelViewSet)

| Método HTTP | URL Pattern       | Nombre de Vista  | Descripción                 |
| ----------- | ----------------- | ---------------- | --------------------------- |
| GET         | `/clientes/`      | `cliente-list`   | Listar todos los clientes   |
| POST        | `/clientes/`      | `cliente-list`   | Crear nuevo cliente         |
| GET         | `/clientes/{id}/` | `cliente-detail` | Obtener detalle de cliente  |
| PUT         | `/clientes/{id}/` | `cliente-detail` | Actualizar cliente completo |
| PATCH       | `/clientes/{id}/` | `cliente-detail` | Actualizar cliente parcial  |
| DELETE      | `/clientes/{id}/` | `cliente-detail` | Eliminar cliente            |

### Rutas de Acciones Personalizadas

| Método HTTP | URL Pattern                  | Nombre de Vista      | Descripción               |
| ----------- | ---------------------------- | -------------------- | ------------------------- |
| POST        | `/clientes/{id}/activar/`    | `cliente-activar`    | Activar cliente           |
| POST        | `/clientes/{id}/desactivar/` | `cliente-desactivar` | Desactivar cliente        |
| GET         | `/clientes/{id}/citas/`      | `cliente-citas`      | Obtener citas del cliente |

## Estructura Completa de URLs

### En el Contexto de la API

Cuando se incluye en el proyecto principal (`nail_salon_api/urls.py`):

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.clients.urls')),  # URLs de clients
    # ... otras apps
]
```

**URLs Finales Resultantes**:

```
http://localhost:8000/api/clientes/                    # Lista/Crear
http://localhost:8000/api/clientes/1/                  # Detalle/Actualizar/Eliminar
http://localhost:8000/api/clientes/1/activar/          # Activar
http://localhost:8000/api/clientes/1/desactivar/       # Desactivar
http://localhost:8000/api/clientes/1/citas/            # Citas del cliente
```

## Análisis Detallado de Cada Endpoint

### 1. Lista de Clientes - `/clientes/`

**Métodos Soportados**: GET, POST

#### GET - Listar Clientes

**URL Completa**: `http://localhost:8000/api/clientes/`

**Parámetros de Query Soportados**:

```
?search=<término>          # Búsqueda en nombre, apellido, teléfono, email
?activo=<true|false>       # Filtrar por estado activo
?fecha_registro=<fecha>    # Filtrar por fecha de registro
?ordering=<campo>          # Ordenar por campo específico
?page=<número>             # Número de página
?page_size=<tamaño>        # Tamaño de página
```

**Ejemplos de URLs**:

```
/api/clientes/?search=Juan
/api/clientes/?activo=true
/api/clientes/?ordering=-fecha_registro
/api/clientes/?page=2&page_size=10
/api/clientes/?search=juan&activo=true&ordering=apellido
```

#### POST - Crear Cliente

**URL Completa**: `http://localhost:8000/api/clientes/`

**Content-Type**: `application/json`

### 2. Detalle de Cliente - `/clientes/{id}/`

**Métodos Soportados**: GET, PUT, PATCH, DELETE

**Parámetro de Ruta**:

- `{id}`: ID del cliente (cliente_id)

**Ejemplos**:

```
/api/clientes/1/           # Cliente con ID 1
/api/clientes/25/          # Cliente con ID 25
/api/clientes/999/         # Error 404 si no existe
```

### 3. Acciones Personalizadas

#### Activar Cliente - `/clientes/{id}/activar/`

**Método**: POST
**URL**: `http://localhost:8000/api/clientes/1/activar/`
**Cuerpo**: No requiere datos adicionales

#### Desactivar Cliente - `/clientes/{id}/desactivar/`

**Método**: POST
**URL**: `http://localhost:8000/api/clientes/1/desactivar/`
**Cuerpo**: No requiere datos adicionales

#### Citas del Cliente - `/clientes/{id}/citas/`

**Método**: GET
**URL**: `http://localhost:8000/api/clientes/1/citas/`
**Estado**: Pendiente de implementación

## Nombres de Vista (Reverse URLs)

### Uso en Templates Django

```python
from django.urls import reverse

# URL para lista de clientes
url_lista = reverse('cliente-list')                    # /api/clientes/

# URL para detalle de cliente
url_detalle = reverse('cliente-detail', args=[1])      # /api/clientes/1/

# URL para acción personalizada
url_activar = reverse('cliente-activar', args=[1])     # /api/clientes/1/activar/
```

### Uso en Tests

```python
def test_listar_clientes(self):
    url = reverse('cliente-list')
    response = self.client.get(url)
    # ...

def test_obtener_detalle(self):
    url = reverse('cliente-detail', args=[self.cliente.pk])
    response = self.client.get(url)
    # ...
```

## Configuración del Router

### DefaultRouter vs SimpleRouter

**DefaultRouter** (Utilizado):

- Incluye vista raíz de la API
- Genera URLs con formato JSON/HTML
- Incluye sufijo de formato opcional (.json, .html)

**Características Adicionales**:

```python
# URLs adicionales generadas por DefaultRouter
/api/                      # Vista raíz de la API
/api/clientes.json         # Formato JSON explícito
/api/clientes.html         # Formato HTML para browsable API
```

### Configuración Alternativa con SimpleRouter

```python
from rest_framework.routers import SimpleRouter

router = SimpleRouter()
router.register(r"clientes", ClienteViewSet, basename="cliente")
```

**Diferencias**:

- No incluye vista raíz
- URLs más limpias
- Menos overhead

## Patrones de URL Personalizados

### Agregando URLs Adicionales

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.cliente_views import ClienteViewSet
from .views import custom_views

# Crear el router
router = DefaultRouter()
router.register(r"clientes", ClienteViewSet, basename="cliente")

# URLs adicionales personalizadas
urlpatterns = [
    path("", include(router.urls)),

    # URLs personalizadas adicionales
    path("clientes/estadisticas/", custom_views.EstadisticasClientesView.as_view(),
         name="clientes-estadisticas"),
    path("clientes/exportar/", custom_views.ExportarClientesView.as_view(),
         name="clientes-exportar"),
]
```

## Configuración de Formato

### Sufijos de Formato

El DefaultRouter permite especificar el formato de respuesta:

```
/api/clientes.json         # Fuerza formato JSON
/api/clientes.html         # Fuerza formato HTML (browsable API)
/api/clientes/1.json       # Detalle en formato JSON
```

### Configuración de Formato por Defecto

```python
# En settings.py
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'URL_FORMAT_OVERRIDE': 'format',
}
```

## Documentación de API

### Browsable API

Django REST Framework proporciona una interfaz web automática:

```
http://localhost:8000/api/clientes/     # Vista navegable web
```

**Características**:

- Interfaz web interactiva
- Formularios para POST/PUT/PATCH
- Documentación automática de campos
- Testing directo desde el navegador

### Integración con OpenAPI/Swagger

```python
# Para generar documentación OpenAPI
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("", include(router.urls)),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
```

## Versioning de API

### Configuración para Versiones Futuras

```python
# URLconf con versionado
urlpatterns = [
    path("v1/", include(router.urls)),
    path("v2/", include(router_v2.urls)),
]
```

### Headers de Versión

```python
# En settings.py
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.AcceptHeaderVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1', 'v2'],
}
```

## Seguridad en URLs

### Validación de Parámetros

```python
# El router maneja automáticamente:
# - Validación de tipos de ID
# - Conversión de tipos
# - Manejo de IDs inexistentes (404)
```

### URLs Sensibles

```python
# Ejemplo de URL con información sensible
/api/clientes/1/datos-bancarios/    # Requeriría permisos especiales
```

## Testing de URLs

### Verificación de Rutas

```python
def test_urls_resuelven_correctamente(self):
    """Test que verifica que todas las URLs se resuelven correctamente"""

    # Lista
    url = reverse('cliente-list')
    self.assertEqual(url, '/api/clientes/')

    # Detalle
    url = reverse('cliente-detail', args=[1])
    self.assertEqual(url, '/api/clientes/1/')

    # Acciones
    url = reverse('cliente-activar', args=[1])
    self.assertEqual(url, '/api/clientes/1/activar/')
```

### Testing de Parámetros

```python
def test_parametros_query(self):
    """Test de parámetros de query"""

    url = reverse('cliente-list')
    response = self.client.get(url, {'search': 'Juan', 'activo': 'true'})
    self.assertEqual(response.status_code, 200)
```

## Optimización de URLs

### Caché de URLs

```python
# En settings.py para desarrollo
USE_TZ = True
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Caché de resolución de URLs
URL_CACHE_TIMEOUT = 3600
```

### Índices de Base de Datos

Las consultas por ID están optimizadas automáticamente por la clave primaria.

## Casos de Uso Comunes

### 1. Integración con Frontend SPA

```javascript
const API_BASE = "http://localhost:8000/api";

// Configuración de rutas en frontend
const routes = {
  clientes: {
    list: `${API_BASE}/clientes/`,
    detail: (id) => `${API_BASE}/clientes/${id}/`,
    activar: (id) => `${API_BASE}/clientes/${id}/activar/`,
    desactivar: (id) => `${API_BASE}/clientes/${id}/desactivar/`,
  },
};
```

### 2. Documentación Automática

```python
# Generación automática de documentación de URLs
python manage.py show_urls  # Lista todas las URLs registradas
```

### 3. Monitoreo de Endpoints

```python
# Middleware para logging de URLs accedidas
class URLLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if '/api/clientes/' in request.path:
            logger.info(f"Cliente endpoint accessed: {request.path}")
        return self.get_response(request)
```
