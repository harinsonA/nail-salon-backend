# Documentación de Vistas - Appointments ViewSets

## Visión General

La aplicación appointments utiliza Django REST Framework ViewSets para proporcionar una API RESTful completa. Los ViewSets principales (`CitaViewSet` y `DetalleCitaViewSet`) manejan todas las operaciones CRUD y funcionalidades adicionales para la gestión de citas y detalles de servicios.

## Archivos Principales

**Ubicación**: `apps/appointments/views/`

- `cita_views.py` - ViewSet principal para citas
- `detalle_cita_views.py` - ViewSet para detalles de servicios en citas

## CitaViewSet

### Definición de Clase

```python
class CitaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar citas
    """
    queryset = Cita.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["estado", "cliente", "fecha_cita"]
    search_fields = ["cliente__nombre", "cliente__apellido", "observaciones"]
    ordering_fields = ["fecha_cita", "fecha_creacion"]
    ordering = ["-fecha_cita"]
```

### Configuración Base

| Atributo             | Valor                                                       | Descripción                               |
| -------------------- | ----------------------------------------------------------- | ----------------------------------------- |
| `queryset`           | `Cita.objects.all()`                                        | Conjunto base de datos                    |
| `permission_classes` | `[IsAuthenticated]`                                         | Requiere autenticación                    |
| `filter_backends`    | Lista de backends                                           | Habilita filtros, búsqueda y ordenamiento |
| `filterset_fields`   | `["estado", "cliente", "fecha_cita"]`                       | Campos filtrables                         |
| `search_fields`      | `["cliente__nombre", "cliente__apellido", "observaciones"]` | Campos buscables                          |
| `ordering_fields`    | `["fecha_cita", "fecha_creacion"]`                          | Campos ordenables                         |
| `ordering`           | `["-fecha_cita"]`                                           | Ordenamiento por defecto                  |

## Métodos Principales

### `get_serializer_class(self)`

```python
def get_serializer_class(self):
    """
    Retornar el serializer apropiado según la acción
    """
    if self.action == "list":
        return CitaListSerializer
    return CitaSerializer
```

**Propósito**: Determina qué serializer usar según la acción:

- **Lista**: `CitaListSerializer` (datos simplificados)
- **Otras acciones**: `CitaSerializer` (datos completos)

### `get_queryset(self)`

```python
def get_queryset(self):
    """
    Filtrar citas según parámetros de consulta
    """
    queryset = Cita.objects.select_related('cliente')

    # Filtro por estado
    estado = self.request.query_params.get("estado", None)
    if estado is not None:
        queryset = queryset.filter(estado=estado)

    # Filtro por cliente
    cliente = self.request.query_params.get("cliente", None)
    if cliente is not None:
        queryset = queryset.filter(cliente_id=cliente)

    # Filtro por fecha
    fecha = self.request.query_params.get("fecha_cita", None)
    if fecha is not None:
        queryset = queryset.filter(fecha_cita__date=fecha)

    return queryset
```

**Propósito**: Personaliza el queryset base aplicando filtros dinámicos y optimizaciones.

### `update(self, request, *args, **kwargs)`

```python
def update(self, request, *args, **kwargs):
    """
    Actualizar cita con validaciones de estado
    """
    instance = self.get_object()

    # Validar transiciones de estado
    nuevo_estado = request.data.get('estado')
    if nuevo_estado and instance.estado == 'completada':
        return Response(
            {"error": "No se puede modificar una cita completada"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if nuevo_estado and instance.estado == 'cancelada':
        return Response(
            {"error": "No se puede modificar una cita cancelada"},
            status=status.HTTP_400_BAD_REQUEST
        )

    return super().update(request, *args, **kwargs)
```

**Propósito**: Añade validaciones de negocio para transiciones de estado.

### `destroy(self, request, *args, **kwargs)`

```python
def destroy(self, request, *args, **kwargs):
    """
    Eliminar cita con validaciones
    """
    instance = self.get_object()

    if instance.estado == 'completada':
        return Response(
            {"error": "No se puede eliminar una cita completada"},
            status=status.HTTP_400_BAD_REQUEST
        )

    return super().destroy(request, *args, **kwargs)
```

**Propósito**: Previene la eliminación de citas en estados no permitidos.

## Endpoints Estándar (ModelViewSet)

### 1. Listar Citas

**Endpoint**: `GET /api/citas/`

**Funcionalidad**:

- Lista todas las citas con paginación
- Aplica filtros, búsqueda y ordenamiento
- Usa `CitaListSerializer` para datos optimizados

**Parámetros de Query**:

```
?search=Juan           # Busca en nombre del cliente u observaciones
?estado=programada     # Filtra por estado
?cliente=1             # Filtra por ID del cliente
?fecha_cita=2024-01-15 # Filtra por fecha específica
?ordering=-fecha_cita  # Ordena por fecha descendente
?page=2                # Paginación
```

**Respuesta**:

```json
{
  "count": 75,
  "links": {
    "next": "http://api/citas/?page=3",
    "previous": "http://api/citas/?page=1"
  },
  "results": [
    {
      "id": 1,
      "cliente": {
        "id": 1,
        "nombre_completo": "Juan Pérez",
        "telefono": "3001234567"
      },
      "fecha_cita": "2024-01-20T14:30:00Z",
      "estado": "programada",
      "total": "85000.00",
      "observaciones": "Manicure y pedicure"
    }
  ]
}
```

### 2. Crear Cita

**Endpoint**: `POST /api/citas/`

**Funcionalidad**:

- Crea una nueva cita
- Valida datos según el serializer
- Estado inicial "programada"
- Retorna la cita creada con todos los campos

**Datos de Entrada**:

```json
{
  "cliente": 1,
  "fecha_cita": "2024-01-25T15:00:00Z",
  "observaciones": "Cita para manicure"
}
```

**Respuesta** (201 Created):

```json
{
  "id": 2,
  "cliente": {
    "id": 1,
    "nombre_completo": "Juan Pérez",
    "telefono": "3001234567",
    "email": "juan@email.com"
  },
  "fecha_cita": "2024-01-25T15:00:00Z",
  "estado": "programada",
  "total": "0.00",
  "observaciones": "Cita para manicure",
  "fecha_creacion": "2024-01-15T11:30:00Z",
  "fecha_actualizacion": "2024-01-15T11:30:00Z",
  "detalles": []
}
```

### 3. Obtener Detalle de Cita

**Endpoint**: `GET /api/citas/{id}/`

**Funcionalidad**:

- Retorna información completa de una cita específica
- Incluye detalles de servicios asociados
- Usa `CitaSerializer` para datos completos

**Respuesta** (200 OK):

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
      "subtotal": "45000.00"
    }
  ]
}
```

### 4. Actualizar Cita Completa

**Endpoint**: `PUT /api/citas/{id}/`

**Funcionalidad**:

- Actualiza todos los campos de la cita
- Valida transiciones de estado
- Requiere enviar todos los campos obligatorios

**Datos de Entrada**:

```json
{
  "cliente": 1,
  "fecha_cita": "2024-01-25T16:00:00Z",
  "estado": "confirmada",
  "observaciones": "Cita confirmada para manicure y pedicure"
}
```

### 5. Actualizar Cita Parcial

**Endpoint**: `PATCH /api/citas/{id}/`

**Funcionalidad**:

- Actualiza solo los campos enviados
- Valida transiciones de estado
- Mantiene el resto de campos sin cambios

**Datos de Entrada**:

```json
{
  "estado": "completada",
  "observaciones": "Servicios realizados exitosamente"
}
```

### 6. Eliminar Cita

**Endpoint**: `DELETE /api/citas/{id}/`

**Funcionalidad**:

- Elimina una cita específica
- Valida que no esté completada
- Elimina en cascada los detalles asociados

**Respuesta** (204 No Content): Sin contenido

**Respuesta de Error** (400 Bad Request):

```json
{
  "error": "No se puede eliminar una cita completada"
}
```

## DetalleCitaViewSet

### Definición de Clase

```python
class DetalleCitaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar detalles de cita (servicios)
    """
    queryset = DetalleCita.objects.all()
    serializer_class = DetalleCitaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["cita", "servicio"]
    ordering_fields = ["id"]
    ordering = ["id"]
```

### Configuración Base

| Atributo             | Valor                       | Descripción                     |
| -------------------- | --------------------------- | ------------------------------- |
| `queryset`           | `DetalleCita.objects.all()` | Conjunto base de datos          |
| `serializer_class`   | `DetalleCitaSerializer`     | Serializer principal            |
| `permission_classes` | `[IsAuthenticated]`         | Requiere autenticación          |
| `filter_backends`    | Lista de backends           | Habilita filtros y ordenamiento |
| `filterset_fields`   | `["cita", "servicio"]`      | Campos filtrables               |
| `ordering_fields`    | `["id"]`                    | Campos ordenables               |
| `ordering`           | `["id"]`                    | Ordenamiento por defecto        |

### Métodos Principales

### `get_queryset(self)`

```python
def get_queryset(self):
    """
    Filtrar detalles según parámetros de consulta
    """
    queryset = DetalleCita.objects.select_related('cita', 'servicio')

    # Filtro por cita
    cita = self.request.query_params.get("cita", None)
    if cita is not None:
        queryset = queryset.filter(cita_id=cita)

    # Filtro por servicio
    servicio = self.request.query_params.get("servicio", None)
    if servicio is not None:
        queryset = queryset.filter(servicio_id=servicio)

    return queryset
```

**Propósito**: Optimiza consultas y aplica filtros específicos.

### `perform_create(self, serializer)`

```python
def perform_create(self, serializer):
    """
    Validar estado de la cita antes de crear detalle
    """
    cita = serializer.validated_data['cita']
    if cita.estado in ['completada', 'cancelada']:
        raise ValidationError("No se pueden agregar servicios a una cita completada o cancelada")

    serializer.save()
```

**Propósito**: Valida que la cita permita agregar servicios.

### `perform_update(self, serializer)`

```python
def perform_update(self, serializer):
    """
    Validar estado de la cita antes de actualizar detalle
    """
    cita = serializer.validated_data.get('cita', serializer.instance.cita)
    if cita.estado in ['completada', 'cancelada']:
        raise ValidationError("No se pueden modificar servicios de una cita completada o cancelada")

    serializer.save()
```

**Propósito**: Valida que la cita permita modificar servicios.

### `perform_destroy(self, instance)`

```python
def perform_destroy(self, instance):
    """
    Validar estado de la cita antes de eliminar detalle
    """
    if instance.cita.estado in ['completada', 'cancelada']:
        raise ValidationError("No se pueden eliminar servicios de una cita completada o cancelada")

    instance.delete()
```

**Propósito**: Valida que la cita permita eliminar servicios.

## Endpoints Estándar DetalleCita

### 1. Listar Detalles de Cita

**Endpoint**: `GET /api/detalles-cita/`

**Funcionalidad**:

- Lista todos los detalles de servicios
- Permite filtrar por cita o servicio
- Incluye información de cita y servicio relacionados

**Parámetros de Query**:

```
?cita=1       # Filtra por ID de la cita
?servicio=2   # Filtra por ID del servicio
```

**Respuesta**:

```json
{
  "count": 25,
  "links": {
    "next": "http://api/detalles-cita/?page=2",
    "previous": null
  },
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
      "subtotal": "45000.00"
    }
  ]
}
```

### 2. Crear Detalle de Cita

**Endpoint**: `POST /api/detalles-cita/`

**Funcionalidad**:

- Agrega un servicio a una cita existente
- Calcula automáticamente el subtotal
- Valida que la cita permita modificaciones

**Datos de Entrada**:

```json
{
  "cita": 1,
  "servicio": 2,
  "cantidad": 1,
  "precio": "40000.00"
}
```

**Respuesta** (201 Created):

```json
{
  "id": 2,
  "cita": 1,
  "servicio": {
    "id": 2,
    "nombre": "Pedicure Clásico",
    "precio": "40000.00",
    "duracion": 45
  },
  "precio": "40000.00",
  "cantidad": 1,
  "subtotal": "40000.00"
}
```

### 3. Obtener Detalle Específico

**Endpoint**: `GET /api/detalles-cita/{id}/`

**Funcionalidad**:

- Retorna información completa de un detalle específico
- Incluye datos del servicio y cita relacionados

### 4. Actualizar Detalle

**Endpoint**: `PUT/PATCH /api/detalles-cita/{id}/`

**Funcionalidad**:

- Actualiza cantidad, precio o servicio
- Recalcula automáticamente el subtotal
- Valida estado de la cita

### 5. Eliminar Detalle

**Endpoint**: `DELETE /api/detalles-cita/{id}/`

**Funcionalidad**:

- Elimina un servicio de la cita
- Valida que la cita permita modificaciones
- Actualiza automáticamente el total de la cita

## Estados de Cita y Validaciones

### Estados Permitidos

1. **programada**: Estado inicial, permite todas las operaciones
2. **confirmada**: Cita confirmada, permite modificaciones
3. **en_proceso**: Cita en ejecución, permite modificaciones limitadas
4. **completada**: Cita finalizada, no permite modificaciones
5. **cancelada**: Cita cancelada, no permite modificaciones

### Reglas de Negocio

1. **Citas completadas**: No se pueden modificar ni eliminar
2. **Citas canceladas**: No se pueden modificar ni eliminar
3. **Servicios en citas finalizadas**: No se pueden agregar, modificar o eliminar
4. **Cálculos automáticos**: El total de la cita se actualiza automáticamente
5. **Validaciones de fechas**: Las fechas de cita deben ser futuras (para nuevas citas)

## Optimizaciones de Rendimiento

### Select Related

```python
# En CitaViewSet
queryset = Cita.objects.select_related('cliente')

# En DetalleCitaViewSet
queryset = DetalleCita.objects.select_related('cita', 'servicio')
```

### Serializers Optimizados

- `CitaListSerializer`: Datos mínimos para listados
- `CitaSerializer`: Datos completos con detalles anidados
- `DetalleCitaSerializer`: Incluye información del servicio relacionado

## Consideraciones de Seguridad

1. **Autenticación requerida**: Todos los endpoints requieren `IsAuthenticated`
2. **Validaciones de estado**: Previenen modificaciones no autorizadas
3. **Validaciones de integridad**: Aseguran consistencia de datos
4. **Filtros seguros**: Previenen inyección de consultas maliciosas
