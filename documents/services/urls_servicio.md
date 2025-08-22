# Documentación de URLs - Sistema de Rutas de Servicios

## Visión General

El sistema de URLs de la aplicación services utiliza Django REST Framework Routers para generar automáticamente todas las rutas RESTful necesarias. Esto proporciona un conjunto completo y consistente de endpoints para la gestión de servicios del salón de uñas.

## Archivo Principal

**Ubicación**: `apps/services/urls.py`

## Configuración de URLs

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.servicio_views import ServicioViewSet

# Crear el router
router = DefaultRouter()
router.register(r"servicios", ServicioViewSet, basename="servicio")

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
router.register(r"servicios", ServicioViewSet, basename="servicio")
```

**Parámetros**:

- **Prefix**: `"servicios"` - Base de la URL
- **ViewSet**: `ServicioViewSet` - Clase que maneja las vistas
- **Basename**: `"servicio"` - Nombre base para los patrones de URL

## URLs Generadas Automáticamente

### Rutas Estándar (ModelViewSet)

| Método HTTP | URL Pattern        | Nombre de Vista   | Descripción                  |
| ----------- | ------------------ | ----------------- | ---------------------------- |
| GET         | `/servicios/`      | `servicio-list`   | Listar todos los servicios   |
| POST        | `/servicios/`      | `servicio-list`   | Crear nuevo servicio         |
| GET         | `/servicios/{id}/` | `servicio-detail` | Obtener detalle de servicio  |
| PUT         | `/servicios/{id}/` | `servicio-detail` | Actualizar servicio completo |
| PATCH       | `/servicios/{id}/` | `servicio-detail` | Actualizar servicio parcial  |
| DELETE      | `/servicios/{id}/` | `servicio-detail` | Eliminar servicio            |

### Rutas de Acciones Personalizadas (Futuras)

| Método HTTP | URL Pattern                     | Nombre de Vista         | Descripción               |
| ----------- | ------------------------------- | ----------------------- | ------------------------- |
| GET         | `/servicios/{id}/estadisticas/` | `servicio-estadisticas` | Estadísticas del servicio |
| POST        | `/servicios/{id}/activar/`      | `servicio-activar`      | Activar servicio          |
| POST        | `/servicios/{id}/desactivar/`   | `servicio-desactivar`   | Desactivar servicio       |

## Estructura Completa de URLs

### En el Contexto de la API

Cuando se incluye en el proyecto principal (`nail_salon_api/urls.py`):

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.services.urls')),  # URLs de services
    # ... otras apps
]
```

**URLs Finales Resultantes**:

```
http://localhost:8000/api/servicios/                    # Lista/Crear
http://localhost:8000/api/servicios/1/                  # Detalle/Actualizar/Eliminar
http://localhost:8000/api/servicios/1/estadisticas/     # Estadísticas (futuro)
http://localhost:8000/api/servicios/1/activar/          # Activar (futuro)
http://localhost:8000/api/servicios/1/desactivar/       # Desactivar (futuro)
```

## Análisis Detallado de Cada Endpoint

### 1. Lista de Servicios - `/servicios/`

**Métodos Soportados**: GET, POST

#### GET - Listar Servicios

**URL Completa**: `http://localhost:8000/api/servicios/`

**Parámetros de Query Soportados**:

```
?search=<término>          # Búsqueda en nombre, descripción, categoría
?activo=<true|false>       # Filtrar por estado activo
?categoria=<categoría>     # Filtrar por categoría específica
?ordering=<campo>          # Ordenar por campo específico
?page=<número>             # Número de página
?page_size=<tamaño>        # Tamaño de página
```

**Ejemplos de URLs**:

```
/api/servicios/?search=Manicure
/api/servicios/?activo=true
/api/servicios/?categoria=Pedicure
/api/servicios/?ordering=precio
/api/servicios/?ordering=-precio&activo=true
/api/servicios/?page=2&page_size=10
/api/servicios/?search=premium&categoria=Manicure&ordering=precio
```

#### POST - Crear Servicio

**URL Completa**: `http://localhost:8000/api/servicios/`

**Content-Type**: `application/json`

**Datos Requeridos**:

- `nombre_servicio` (string, requerido)
- `precio` (decimal, requerido)

**Datos Opcionales**:

- `descripcion` (text, opcional)
- `duracion_estimada` (duration, opcional)
- `categoria` (string, opcional)
- `activo` (boolean, default: true)

### 2. Detalle de Servicio - `/servicios/{id}/`

**Métodos Soportados**: GET, PUT, PATCH, DELETE

**Parámetro de Ruta**:

- `{id}`: ID del servicio (servicio_id)

**Ejemplos**:

```
/api/servicios/1/           # Servicio con ID 1
/api/servicios/25/          # Servicio con ID 25
/api/servicios/999/         # Error 404 si no existe
```

#### GET - Obtener Detalle

**Respuesta**: Información completa del servicio con todos los campos.

#### PUT - Actualización Completa

**Requiere**: Todos los campos obligatorios.
**Validaciones**: Incluye validaciones de negocio (citas activas).

#### PATCH - Actualización Parcial

**Requiere**: Solo los campos a actualizar.
**Validaciones**: Incluye validaciones de negocio.

#### DELETE - Eliminar Servicio

**Validaciones**: No se puede eliminar si tiene citas asociadas.
**Respuesta**: 204 No Content si exitoso, 400 Bad Request si tiene restricciones.

## Nombres de Vista (Reverse URLs)

### Uso en Templates Django

```python
from django.urls import reverse

# URL para lista de servicios
url_lista = reverse('servicio-list')                    # /api/servicios/

# URL para detalle de servicio
url_detalle = reverse('servicio-detail', args=[1])      # /api/servicios/1/

# URL para acción personalizada (futuro)
url_estadisticas = reverse('servicio-estadisticas', args=[1])  # /api/servicios/1/estadisticas/
```

### Uso en Tests

```python
def test_listar_servicios(self):
    url = reverse('servicio-list')
    response = self.client.get(url)
    # ...

def test_obtener_detalle(self):
    url = reverse('servicio-detail', args=[self.servicio.pk])
    response = self.client.get(url)
    # ...

def test_crear_servicio(self):
    url = reverse('servicio-list')
    data = {
        'nombre_servicio': 'Nuevo Servicio',
        'precio': '25000.00'
    }
    response = self.client.post(url, data)
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
/api/servicios.json        # Formato JSON explícito
/api/servicios.html        # Formato HTML para browsable API
```

### Configuración Alternativa con SimpleRouter

```python
from rest_framework.routers import SimpleRouter

router = SimpleRouter()
router.register(r"servicios", ServicioViewSet, basename="servicio")
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
from .views.servicio_views import ServicioViewSet
from .views import custom_views

# Crear el router
router = DefaultRouter()
router.register(r"servicios", ServicioViewSet, basename="servicio")

# URLs adicionales personalizadas
urlpatterns = [
    path("", include(router.urls)),

    # URLs personalizadas adicionales
    path("servicios/categorias/", custom_views.CategoriasServiciosView.as_view(),
         name="servicios-categorias"),
    path("servicios/estadisticas/", custom_views.EstadisticasServiciosView.as_view(),
         name="servicios-estadisticas-generales"),
    path("servicios/populares/", custom_views.ServiciosPopularesView.as_view(),
         name="servicios-populares"),
]
```

## Configuración de Formato

### Sufijos de Formato

El DefaultRouter permite especificar el formato de respuesta:

```
/api/servicios.json         # Fuerza formato JSON
/api/servicios.html         # Fuerza formato HTML (browsable API)
/api/servicios/1.json       # Detalle en formato JSON
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
http://localhost:8000/api/servicios/     # Vista navegable web
```

**Características**:

- Interfaz web interactiva
- Formularios para POST/PUT/PATCH
- Documentación automática de campos
- Testing directo desde el navegador
- Visualización de validaciones

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

## Versionado de API

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
# Ejemplo de URLs que podrían requerir permisos especiales
/api/servicios/1/precio-historico/    # Historial de precios
/api/servicios/1/margenes/            # Información de márgenes
/api/servicios/estadisticas-ventas/   # Estadísticas de ventas
```

## Testing de URLs

### Verificación de Rutas

```python
def test_urls_resuelven_correctamente(self):
    """Test que verifica que todas las URLs se resuelven correctamente"""

    # Lista
    url = reverse('servicio-list')
    self.assertEqual(url, '/api/servicios/')

    # Detalle
    url = reverse('servicio-detail', args=[1])
    self.assertEqual(url, '/api/servicios/1/')

    # Verificar que las URLs existen
    resolver = resolve('/api/servicios/')
    self.assertEqual(resolver.view_name, 'servicio-list')
```

### Testing de Parámetros

```python
def test_parametros_query(self):
    """Test de parámetros de query"""

    url = reverse('servicio-list')
    response = self.client.get(url, {'search': 'Manicure', 'activo': 'true'})
    self.assertEqual(response.status_code, 200)

def test_filtros_combinados(self):
    """Test de filtros múltiples"""

    url = reverse('servicio-list')
    params = {
        'activo': 'true',
        'categoria': 'Manicure',
        'ordering': 'precio'
    }
    response = self.client.get(url, params)
    self.assertEqual(response.status_code, 200)
```

## Optimización de URLs

### Caché de URLs

```python
# En settings.py para desarrollo
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
  servicios: {
    list: `${API_BASE}/servicios/`,
    detail: (id) => `${API_BASE}/servicios/${id}/`,
    create: `${API_BASE}/servicios/`,
    update: (id) => `${API_BASE}/servicios/${id}/`,
    delete: (id) => `${API_BASE}/servicios/${id}/`,
  },
};

// Uso en componentes
const listarServicios = async (filtros = {}) => {
  const params = new URLSearchParams(filtros);
  const response = await fetch(`${routes.servicios.list}?${params}`);
  return response.json();
};

const obtenerServicio = async (id) => {
  const response = await fetch(routes.servicios.detail(id));
  return response.json();
};
```

### 2. Búsquedas y Filtros Comunes

```javascript
// Servicios activos de manicure
const serviciosManicure = await fetch(
  "/api/servicios/?categoria=Manicure&activo=true"
);

// Servicios ordenados por precio
const serviciosPorPrecio = await fetch("/api/servicios/?ordering=precio");

// Búsqueda de servicios
const buscarServicios = await fetch("/api/servicios/?search=premium");

// Paginación
const segundaPagina = await fetch("/api/servicios/?page=2&page_size=5");
```

### 3. Monitoreo de Endpoints

```python
# Middleware para logging de URLs accedidas
class URLLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if '/api/servicios/' in request.path:
            logger.info(f"Servicio endpoint accessed: {request.path} - Method: {request.method}")
        return self.get_response(request)
```

## Estado Actual

✅ **Implementación Completa**

- Router configurado correctamente
- URLs RESTful estándar generadas
- Nombres de vista consistentes
- Compatibilidad con browsable API
- Testing de URLs implementado
- Documentación completa de endpoints

## Próximas Mejoras

🔄 **Posibles Extensiones**:

- Acciones personalizadas adicionales
- Versionado de API
- URLs para estadísticas avanzadas
- Endpoints de búsqueda optimizada
