# Documentación de Vistas - Servicio ViewSet

## Visión General

La aplicación services utiliza Django REST Framework ViewSets para proporcionar una API RESTful completa. El `ServicioViewSet` es la vista principal que maneja todas las operaciones CRUD y funcionalidades adicionales para la gestión de servicios del salón de uñas.

## Archivo Principal

**Ubicación**: `apps/services/views/servicio_views.py`

## ServicioViewSet

### Definición de Clase

```python
class ServicioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar servicios
    """
    queryset = Servicio.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["activo", "categoria"]
    search_fields = ["nombre_servicio", "descripcion", "categoria"]
    ordering_fields = ["nombre_servicio", "precio", "fecha_creacion"]
    ordering = ["nombre_servicio"]
```

### Configuración Base

| Atributo             | Valor                                             | Descripción                               |
| -------------------- | ------------------------------------------------- | ----------------------------------------- |
| `queryset`           | `Servicio.objects.all()`                          | Conjunto base de datos                    |
| `permission_classes` | `[IsAuthenticated]`                               | Requiere autenticación                    |
| `filter_backends`    | Lista de backends                                 | Habilita filtros, búsqueda y ordenamiento |
| `filterset_fields`   | `["activo", "categoria"]`                         | Campos filtrables                         |
| `search_fields`      | `["nombre_servicio", "descripcion", "categoria"]` | Campos buscables                          |
| `ordering_fields`    | `["nombre_servicio", "precio", "fecha_creacion"]` | Campos ordenables                         |
| `ordering`           | `["nombre_servicio"]`                             | Ordenamiento por defecto                  |

## Métodos Principales

### `get_serializer_class(self)`

```python
def get_serializer_class(self):
    """
    Retornar el serializer apropiado según la acción
    """
    if self.action == "list":
        return ServicioListSerializer
    return ServicioSerializer
```

**Propósito**: Determina qué serializer usar según la acción:

- **Lista**: `ServicioListSerializer` (datos simplificados para mejor performance)
- **Otras acciones**: `ServicioSerializer` (datos completos con validaciones)

### `get_queryset(self)`

```python
def get_queryset(self):
    """
    Filtrar servicios según parámetros de consulta
    """
    queryset = Servicio.objects.all()

    # Filtro por estado activo
    activo = self.request.query_params.get("activo", None)
    if activo is not None:
        queryset = queryset.filter(activo=activo.lower() == "true")

    # Filtro por categoría
    categoria = self.request.query_params.get("categoria", None)
    if categoria is not None:
        queryset = queryset.filter(categoria__icontains=categoria)

    return queryset
```

**Propósito**: Personaliza el queryset base aplicando filtros dinámicos personalizados.

### `update(self, request, *args, **kwargs)`

```python
def update(self, request, *args, **kwargs):
    """
    Actualizar servicio con validaciones adicionales
    """
    instance = self.get_object()

    # Validar que no se pueda desactivar un servicio si tiene citas activas
    nuevo_activo = request.data.get("activo")
    if nuevo_activo is False and instance.activo:
        # Verificar si tiene citas programadas o confirmadas
        from apps.appointments.models.detalle_cita import DetalleCita

        citas_activas = DetalleCita.objects.filter(
            servicio=instance,
            cita__estado__in=["programada", "confirmada", "en_proceso"],
        ).exists()

        if citas_activas:
            return Response(
                {
                    "error": "No se puede desactivar un servicio que tiene citas activas"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    return super().update(request, *args, **kwargs)
```

**Propósito**: Agrega validaciones de negocio específicas para la actualización de servicios.

### `destroy(self, request, *args, **kwargs)`

```python
def destroy(self, request, *args, **kwargs):
    """
    Eliminar servicio con validaciones
    """
    instance = self.get_object()

    # Verificar si tiene detalles de cita asociados
    from apps.appointments.models.detalle_cita import DetalleCita

    tiene_citas = DetalleCita.objects.filter(servicio=instance).exists()

    if tiene_citas:
        return Response(
            {"error": "No se puede eliminar un servicio que tiene citas asociadas"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return super().destroy(request, *args, **kwargs)
```

**Propósito**: Previene la eliminación de servicios que tienen relaciones críticas.

## Endpoints Estándar (ModelViewSet)

### 1. Listar Servicios

**Endpoint**: `GET /api/servicios/`

**Funcionalidad**:

- Lista todos los servicios con paginación
- Aplica filtros, búsqueda y ordenamiento
- Usa `ServicioListSerializer` para datos optimizados

**Parámetros de Query**:

```
?search=Manicure          # Busca en nombre, descripción y categoría
?activo=true             # Filtra por estado activo
?categoria=Manicure      # Filtra por categoría específica
?ordering=precio         # Ordena por precio
?page=2                  # Paginación
```

**Respuesta**:

```json
{
  "count": 25,
  "links": {
    "next": "http://api/servicios/?page=3",
    "previous": "http://api/servicios/?page=1"
  },
  "results": [
    {
      "id": 1,
      "servicio_id": 1,
      "nombre_servicio": "Manicure Básico",
      "precio": "25000.00",
      "precio_formateado": "$25,000.00",
      "descripcion": "Manicure estándar con esmaltado básico",
      "duracion_estimada": "01:00:00",
      "duracion_estimada_horas": "1h 0m",
      "categoria": "Manicure",
      "activo": true
    }
  ]
}
```

### 2. Crear Servicio

**Endpoint**: `POST /api/servicios/`

**Funcionalidad**:

- Crea un nuevo servicio
- Valida datos según el serializer
- Retorna el servicio creado con todos los campos

**Datos de Entrada**:

```json
{
  "nombre_servicio": "Pedicure Premium",
  "precio": "45000.00",
  "descripcion": "Pedicure completo con tratamiento especial",
  "duracion_estimada": "02:00:00",
  "categoria": "Pedicure",
  "activo": true
}
```

**Respuesta** (201 Created):

```json
{
  "id": 2,
  "servicio_id": 2,
  "nombre_servicio": "Pedicure Premium",
  "precio": "45000.00",
  "precio_formateado": "$45,000.00",
  "descripcion": "Pedicure completo con tratamiento especial",
  "duracion_estimada": "02:00:00",
  "duracion_estimada_horas": "2h 0m",
  "activo": true,
  "categoria": "Pedicure",
  "imagen": null,
  "fecha_creacion": "2024-01-15T10:30:00Z",
  "fecha_actualizacion": "2024-01-15T10:30:00Z"
}
```

### 3. Obtener Detalle de Servicio

**Endpoint**: `GET /api/servicios/{id}/`

**Funcionalidad**:

- Retorna información completa de un servicio específico
- Usa `ServicioSerializer` para datos completos

**Respuesta** (200 OK):

```json
{
  "id": 1,
  "servicio_id": 1,
  "nombre_servicio": "Manicure Básico",
  "precio": "25000.00",
  "precio_formateado": "$25,000.00",
  "descripcion": "Manicure estándar con esmaltado básico",
  "duracion_estimada": "01:00:00",
  "duracion_estimada_horas": "1h 0m",
  "activo": true,
  "categoria": "Manicure",
  "imagen": null,
  "fecha_creacion": "2024-01-15T09:00:00Z",
  "fecha_actualizacion": "2024-01-15T09:00:00Z"
}
```

### 4. Actualizar Servicio Completo

**Endpoint**: `PUT /api/servicios/{id}/`

**Funcionalidad**:

- Actualiza todos los campos del servicio
- Requiere enviar todos los campos obligatorios
- Incluye validaciones de negocio

**Datos de Entrada**:

```json
{
  "nombre_servicio": "Manicure Básico Premium",
  "precio": "30000.00",
  "descripcion": "Manicure mejorado con tratamiento de cutículas",
  "duracion_estimada": "01:30:00",
  "activo": true,
  "categoria": "Manicure"
}
```

### 5. Actualizar Servicio Parcial

**Endpoint**: `PATCH /api/servicios/{id}/`

**Funcionalidad**:

- Actualiza solo los campos enviados
- Mantiene el resto de campos sin cambios
- Incluye validaciones de negocio

**Datos de Entrada**:

```json
{
  "precio": "28000.00",
  "descripcion": "Descripción actualizada"
}
```

### 6. Eliminar Servicio

**Endpoint**: `DELETE /api/servicios/{id}/`

**Funcionalidad**:

- Elimina físicamente el servicio de la base de datos
- Valida que no tenga citas asociadas
- Retorna 204 No Content si es exitoso

**Validaciones**:

- No se puede eliminar si tiene citas asociadas
- Retorna error 400 con mensaje descriptivo

## Filtros y Búsqueda

### Filtros Disponibles

1. **Por Estado Activo**:

   ```
   GET /api/servicios/?activo=true
   GET /api/servicios/?activo=false
   ```

2. **Por Categoría**:

   ```
   GET /api/servicios/?categoria=Manicure
   GET /api/servicios/?categoria=Pedicure
   ```

3. **Filtros Combinados**:
   ```
   GET /api/servicios/?activo=true&categoria=Manicure
   ```

### Búsqueda de Texto

```
GET /api/servicios/?search=básico
```

Busca en los campos: `nombre_servicio`, `descripcion`, `categoria`

**Ejemplos**:

- `?search=Manicure` - encuentra servicios con "Manicure" en cualquier campo buscable
- `?search=premium` - encuentra servicios premium en nombre o descripción

### Ordenamiento

```
GET /api/servicios/?ordering=nombre_servicio     # Ascendente por nombre
GET /api/servicios/?ordering=-precio            # Descendente por precio
GET /api/servicios/?ordering=fecha_creacion     # Por fecha de creación
GET /api/servicios/?ordering=precio,nombre_servicio  # Múltiples campos
```

**Campos Ordenables**:

- `nombre_servicio`
- `precio`
- `fecha_creacion`

## Validaciones de Negocio

### Validación de Desactivación

**Regla**: No se puede desactivar un servicio que tiene citas activas.

**Estados de Cita que Impiden Desactivación**:

- `programada`
- `confirmada`
- `en_proceso`

**Respuesta de Error**:

```json
{
  "error": "No se puede desactivar un servicio que tiene citas activas"
}
```

**Status Code**: 400 Bad Request

### Validación de Eliminación

**Regla**: No se puede eliminar un servicio que tiene citas asociadas (cualquier estado).

**Respuesta de Error**:

```json
{
  "error": "No se puede eliminar un servicio que tiene citas asociadas"
}
```

**Status Code**: 400 Bad Request

## Permisos y Autenticación

### Requisitos de Autenticación

- **Todos los endpoints requieren autenticación**
- Utiliza `IsAuthenticated` de DRF
- Compatible con autenticación por token, sesión, JWT, etc.

### Verificación de Permisos

```python
permission_classes = [IsAuthenticated]
```

### Comportamiento sin Autenticación

**Respuesta** (401 Unauthorized):

```json
{
  "detail": "Authentication credentials were not provided."
}
```

## Paginación

### Configuración

La paginación se configura a nivel global en Django settings:

```python
REST_FRAMEWORK = {
    'PAGE_SIZE': 20,
    'PAGE_SIZE_QUERY_PARAM': 'page_size',
    'MAX_PAGE_SIZE': 100
}
```

### Estructura de Respuesta Paginada

```json
{
  "count": 25,
  "links": {
    "next": "http://api/servicios/?page=3",
    "previous": "http://api/servicios/?page=1"
  },
  "results": [...]
}
```

## Manejo de Errores

### Errores Comunes

1. **Servicio No Encontrado** (404):

   ```json
   {
     "detail": "Not found."
   }
   ```

2. **Datos Inválidos** (400):

   ```json
   {
     "nombre_servicio": ["Ya existe un servicio con este nombre."],
     "precio": ["El precio debe ser mayor o igual a 0."]
   }
   ```

3. **Validaciones de Negocio** (400):

   ```json
   {
     "error": "No se puede desactivar un servicio que tiene citas activas"
   }
   ```

4. **Sin Autenticación** (401):
   ```json
   {
     "detail": "Authentication credentials were not provided."
   }
   ```

## Optimizaciones de Performance

### Queries Optimizadas

1. **Lista de Servicios**: Usa `ServicioListSerializer` con menos campos
2. **Ordenamiento por Defecto**: Optimizado con índice en `nombre_servicio`
3. **Filtros Eficientes**: Campos indexados para filtros rápidos

### Validaciones Optimizadas

1. **Citas Activas**: Usa `exists()` para verificación rápida
2. **Importación Tardía**: Models se importan solo cuando se necesitan

### Recomendaciones Futuras

1. **Caché**: Implementar caché Redis para listados frecuentes
2. **Select Related**: Para relaciones futuras con otros modelos
3. **Prefetch Related**: Para relaciones inversas (citas, historial)

## Casos de Uso Comunes

### 1. Buscar Servicios de Manicure

```
GET /api/servicios/?search=Manicure&activo=true
```

### 2. Listar Servicios por Precio

```
GET /api/servicios/?ordering=precio&activo=true
```

### 3. Servicios de una Categoría Específica

```
GET /api/servicios/?categoria=Pedicure&ordering=nombre_servicio
```

### 4. Desactivar Servicio (Soft Delete)

```
PATCH /api/servicios/1/
{
  "activo": false
}
```

### 5. Actualizar Precio de Servicio

```
PATCH /api/servicios/1/
{
  "precio": "35000.00"
}
```

## Integración con Frontend

### Ejemplo de Uso con JavaScript

```javascript
// Listar servicios activos
const response = await fetch("/api/servicios/?activo=true", {
  headers: {
    Authorization: "Token your-auth-token",
  },
});
const data = await response.json();

// Crear nuevo servicio
const nuevoServicio = await fetch("/api/servicios/", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: "Token your-auth-token",
  },
  body: JSON.stringify({
    nombre_servicio: "Nail Art Premium",
    precio: "50000.00",
    descripcion: "Diseño artístico de uñas personalizado",
    duracion_estimada: "02:30:00",
    categoria: "Nail Art",
  }),
});

// Actualizar precio
const actualizarPrecio = await fetch("/api/servicios/1/", {
  method: "PATCH",
  headers: {
    "Content-Type": "application/json",
    Authorization: "Token your-auth-token",
  },
  body: JSON.stringify({
    precio: "32000.00",
  }),
});
```

## Extensibilidad

### Agregando Nuevas Acciones

```python
from rest_framework.decorators import action

@action(detail=True, methods=["get"])
def estadisticas(self, request, pk=None):
    """
    Obtener estadísticas del servicio
    """
    servicio = self.get_object()

    # Calcular estadísticas
    total_citas = servicio.detalle_citas.count()
    ingresos_totales = servicio.detalle_citas.aggregate(
        total=models.Sum('precio_acordado')
    )['total'] or 0

    return Response({
        'total_citas': total_citas,
        'ingresos_totales': ingresos_totales,
        'promedio_por_cita': ingresos_totales / total_citas if total_citas > 0 else 0
    })
```

### Personalizando Filtros

```python
def get_queryset(self):
    queryset = super().get_queryset()

    # Filtro por rango de precios
    precio_min = self.request.query_params.get('precio_min')
    precio_max = self.request.query_params.get('precio_max')

    if precio_min:
        queryset = queryset.filter(precio__gte=precio_min)
    if precio_max:
        queryset = queryset.filter(precio__lte=precio_max)

    return queryset
```

## Estado Actual

✅ **Implementación Completa**

- CRUD completo con validaciones
- Filtros y búsqueda optimizados
- Validaciones de negocio implementadas
- Manejo de errores robusto
- Permisos y autenticación configurados
- Optimizaciones de performance aplicadas
