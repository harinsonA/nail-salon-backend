# Documentación de Vistas - Cliente ViewSet

## Visión General

La aplicación clients utiliza Django REST Framework ViewSets para proporcionar una API RESTful completa. El `ClienteViewSet` es la vista principal que maneja todas las operaciones CRUD y funcionalidades adicionales para la gestión de clientes.

## Archivo Principal

**Ubicación**: `apps/clients/views/cliente_views.py`

## ClienteViewSet

### Definición de Clase

```python
class ClienteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar clientes
    """
    queryset = Cliente.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["activo", "fecha_registro"]
    search_fields = ["nombre", "apellido", "telefono", "email"]
    ordering_fields = ["fecha_registro", "nombre", "apellido"]
    ordering = ["-fecha_registro"]
```

### Configuración Base

| Atributo             | Valor                                         | Descripción                               |
| -------------------- | --------------------------------------------- | ----------------------------------------- |
| `queryset`           | `Cliente.objects.all()`                       | Conjunto base de datos                    |
| `permission_classes` | `[IsAuthenticated]`                           | Requiere autenticación                    |
| `filter_backends`    | Lista de backends                             | Habilita filtros, búsqueda y ordenamiento |
| `filterset_fields`   | `["activo", "fecha_registro"]`                | Campos filtrables                         |
| `search_fields`      | `["nombre", "apellido", "telefono", "email"]` | Campos buscables                          |
| `ordering_fields`    | `["fecha_registro", "nombre", "apellido"]`    | Campos ordenables                         |
| `ordering`           | `["-fecha_registro"]`                         | Ordenamiento por defecto                  |

## Métodos Principales

### `get_serializer_class(self)`

```python
def get_serializer_class(self):
    """
    Retornar el serializer apropiado según la acción
    """
    if self.action == "list":
        return ClienteListSerializer
    return ClienteSerializer
```

**Propósito**: Determina qué serializer usar según la acción:

- **Lista**: `ClienteListSerializer` (datos simplificados)
- **Otras acciones**: `ClienteSerializer` (datos completos)

### `get_queryset(self)`

```python
def get_queryset(self):
    """
    Filtrar clientes según parámetros de consulta
    """
    queryset = Cliente.objects.all()

    # Filtro por estado activo
    activo = self.request.query_params.get("activo", None)
    if activo is not None:
        queryset = queryset.filter(activo=activo.lower() == "true")

    return queryset
```

**Propósito**: Personaliza el queryset base aplicando filtros dinámicos.

## Endpoints Estándar (ModelViewSet)

### 1. Listar Clientes

**Endpoint**: `GET /api/clientes/`

**Funcionalidad**:

- Lista todos los clientes con paginación
- Aplica filtros, búsqueda y ordenamiento
- Usa `ClienteListSerializer` para datos optimizados

**Parámetros de Query**:

```
?search=Juan           # Busca en nombre, apellido, teléfono, email
?activo=true          # Filtra por estado activo
?ordering=nombre      # Ordena por nombre
?page=2               # Paginación
```

**Respuesta**:

```json
{
  "count": 150,
  "links": {
    "next": "http://api/clientes/?page=3",
    "previous": "http://api/clientes/?page=1"
  },
  "results": [
    {
      "id": 1,
      "cliente_id": 1,
      "nombre": "Juan",
      "apellido": "Pérez",
      "nombre_completo": "Juan Pérez",
      "telefono": "3001234567",
      "email": "juan@email.com",
      "fecha_registro": "2024-01-15",
      "activo": true,
      "notas": "Cliente frecuente"
    }
  ]
}
```

### 2. Crear Cliente

**Endpoint**: `POST /api/clientes/`

**Funcionalidad**:

- Crea un nuevo cliente
- Valida datos según el serializer
- Retorna el cliente creado con todos los campos

**Datos de Entrada**:

```json
{
  "nombre": "María",
  "apellido": "García",
  "telefono": "3009876543",
  "email": "maria@email.com",
  "notas": "Cliente nueva"
}
```

**Respuesta** (201 Created):

```json
{
  "id": 2,
  "cliente_id": 2,
  "nombre": "María",
  "apellido": "García",
  "nombre_completo": "María García",
  "telefono": "3009876543",
  "email": "maria@email.com",
  "fecha_registro": "2024-01-15",
  "activo": true,
  "notas": "Cliente nueva",
  "fecha_creacion": "2024-01-15T10:30:00Z",
  "fecha_actualizacion": "2024-01-15T10:30:00Z"
}
```

### 3. Obtener Detalle de Cliente

**Endpoint**: `GET /api/clientes/{id}/`

**Funcionalidad**:

- Retorna información completa de un cliente específico
- Usa `ClienteSerializer` para datos completos

**Respuesta** (200 OK):

```json
{
  "id": 1,
  "cliente_id": 1,
  "nombre": "Juan",
  "apellido": "Pérez",
  "nombre_completo": "Juan Pérez",
  "telefono": "3001234567",
  "email": "juan@email.com",
  "fecha_registro": "2024-01-15",
  "activo": true,
  "notas": "Cliente frecuente",
  "fecha_creacion": "2024-01-15T09:00:00Z",
  "fecha_actualizacion": "2024-01-15T09:00:00Z"
}
```

### 4. Actualizar Cliente Completo

**Endpoint**: `PUT /api/clientes/{id}/`

**Funcionalidad**:

- Actualiza todos los campos del cliente
- Requiere enviar todos los campos obligatorios

**Datos de Entrada**:

```json
{
  "nombre": "Juan Carlos",
  "apellido": "Pérez García",
  "telefono": "3001234567",
  "email": "juan.carlos@email.com",
  "activo": true,
  "notas": "Cliente VIP actualizado"
}
```

### 5. Actualizar Cliente Parcial

**Endpoint**: `PATCH /api/clientes/{id}/`

**Funcionalidad**:

- Actualiza solo los campos enviados
- Mantiene el resto de campos sin cambios

**Datos de Entrada**:

```json
{
  "telefono": "3005555555",
  "notas": "Teléfono actualizado"
}
```

### 6. Eliminar Cliente

**Endpoint**: `DELETE /api/clientes/{id}/`

**Funcionalidad**:

- Elimina físicamente el cliente de la base de datos
- Retorna 204 No Content si es exitoso

## Acciones Personalizadas

### 1. Desactivar Cliente

**Endpoint**: `POST /api/clientes/{id}/desactivar/`

```python
@action(detail=True, methods=["post"])
def desactivar(self, request, pk=None):
    """
    Desactivar un cliente
    """
    cliente = self.get_object()
    cliente.activo = False
    cliente.save()
    return Response({"mensaje": "Cliente desactivado correctamente"})
```

**Funcionalidad**:

- Marca el cliente como inactivo (soft delete)
- Preserva los datos para referencia histórica

**Respuesta**:

```json
{
  "mensaje": "Cliente desactivado correctamente"
}
```

### 2. Activar Cliente

**Endpoint**: `POST /api/clientes/{id}/activar/`

```python
@action(detail=True, methods=["post"])
def activar(self, request, pk=None):
    """
    Activar un cliente
    """
    cliente = self.get_object()
    cliente.activo = True
    cliente.save()
    return Response({"mensaje": "Cliente activado correctamente"})
```

**Funcionalidad**:

- Reactiva un cliente previamente desactivado

### 3. Obtener Citas del Cliente

**Endpoint**: `GET /api/clientes/{id}/citas/`

```python
@action(detail=True, methods=["get"])
def citas(self, request, pk=None):
    """
    Obtener las citas de un cliente específico
    """
    # Esta funcionalidad se implementará cuando tengamos el modelo de Citas
    return Response({
        "mensaje": "Funcionalidad pendiente: listar citas del cliente"
    })
```

**Estado**: Pendiente de implementación (depende del modelo Citas)

## Métodos de Personalización

### `perform_create(self, serializer)`

```python
def perform_create(self, serializer):
    """
    Personalizar la creación de clientes
    """
    serializer.save()
```

**Propósito**: Hook para personalizar el proceso de creación (actualmente básico).

### `perform_update(self, serializer)`

```python
def perform_update(self, serializer):
    """
    Personalizar la actualización de clientes
    """
    serializer.save()
```

**Propósito**: Hook para personalizar el proceso de actualización.

## Filtros y Búsqueda

### Filtros Disponibles

1. **Por Estado Activo**:

   ```
   GET /api/clientes/?activo=true
   GET /api/clientes/?activo=false
   ```

2. **Por Fecha de Registro**:
   ```
   GET /api/clientes/?fecha_registro=2024-01-15
   GET /api/clientes/?fecha_registro__gte=2024-01-01
   ```

### Búsqueda de Texto

```
GET /api/clientes/?search=Juan
```

Busca en los campos: `nombre`, `apellido`, `telefono`, `email`

### Ordenamiento

```
GET /api/clientes/?ordering=nombre           # Ascendente por nombre
GET /api/clientes/?ordering=-fecha_registro  # Descendente por fecha
GET /api/clientes/?ordering=apellido,nombre  # Múltiples campos
```

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
    "count": 150,
    "links": {
        "next": "http://api/clientes/?page=3",
        "previous": "http://api/clientes/?page=1"
    },
    "results": [...]
}
```

## Manejo de Errores

### Errores Comunes

1. **Cliente No Encontrado** (404):

   ```json
   {
     "detail": "Not found."
   }
   ```

2. **Datos Inválidos** (400):

   ```json
   {
     "email": ["Ya existe un cliente con este email."],
     "telefono": ["Este campo es requerido."]
   }
   ```

3. **Sin Autenticación** (401):
   ```json
   {
     "detail": "Authentication credentials were not provided."
   }
   ```

## Optimizaciones de Performance

### Queries Optimizadas

1. **Lista de Clientes**: Usa `ClienteListSerializer` con menos campos
2. **Ordenamiento por Defecto**: Optimizado con índice en `fecha_registro`
3. **Filtros Eficientes**: Campos indexados para filtros rápidos

### Recomendaciones Futuras

1. **Caché**: Implementar caché Redis para listados frecuentes
2. **Select Related**: Para relaciones futuras con otros modelos
3. **Prefetch Related**: Para relaciones inversa (citas, pagos)

## Casos de Uso Comunes

### 1. Buscar Cliente por Teléfono

```
GET /api/clientes/?search=3001234567
```

### 2. Listar Clientes Activos Ordenados

```
GET /api/clientes/?activo=true&ordering=apellido
```

### 3. Clientes Registrados Recientemente

```
GET /api/clientes/?fecha_registro__gte=2024-01-01&ordering=-fecha_registro
```

### 4. Desactivar Cliente (Soft Delete)

```
POST /api/clientes/1/desactivar/
```

### 5. Buscar por Nombre Parcial

```
GET /api/clientes/?search=Juan
```

## Integración con Frontend

### Ejemplo de Uso con JavaScript

```javascript
// Listar clientes
const response = await fetch("/api/clientes/", {
  headers: {
    Authorization: "Token your-auth-token",
  },
});
const data = await response.json();

// Crear cliente
const nuevoCliente = await fetch("/api/clientes/", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: "Token your-auth-token",
  },
  body: JSON.stringify({
    nombre: "Ana",
    apellido: "López",
    telefono: "3001111111",
    email: "ana@email.com",
  }),
});
```

## Extensibilidad

### Agregando Nuevas Acciones

```python
@action(detail=True, methods=["get"])
def historial_servicios(self, request, pk=None):
    """
    Obtener historial de servicios del cliente
    """
    cliente = self.get_object()
    # Lógica para obtener servicios
    return Response(data)
```

### Personalizando Filtros

```python
def get_queryset(self):
    queryset = super().get_queryset()

    # Filtro personalizado por rango de fechas
    fecha_desde = self.request.query_params.get('fecha_desde')
    fecha_hasta = self.request.query_params.get('fecha_hasta')

    if fecha_desde and fecha_hasta:
        queryset = queryset.filter(
            fecha_registro__range=[fecha_desde, fecha_hasta]
        )

    return queryset
```
