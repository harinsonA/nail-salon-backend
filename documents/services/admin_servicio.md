# Documentación de Administración Django - Servicios

## Visión General

La aplicación services incluye una configuración completa del panel de administración de Django que permite gestionar los servicios del salón de uñas de manera intuitiva y eficiente. La interfaz administrativa proporciona todas las funcionalidades necesarias para la gestión diaria de servicios.

## Archivo Principal

**Ubicación**: `apps/services/admin.py`

## Configuración del Admin

### ServicioAdmin

```python
@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    """
    Configuración del admin para Servicio
    """
```

Esta configuración registra automáticamente el modelo Servicio en el panel de administración con todas las personalizaciones definidas.

## Configuración de la Lista

### Campos Mostrados (list_display)

```python
list_display = [
    "servicio_id",
    "nombre_servicio",
    "categoria",
    "precio_formateado",
    "duracion_formateada",
    "activo",
    "fecha_creacion",
]
```

**Vista de Lista**:

| Campo                 | Tipo     | Descripción                  | Ordenable |
| --------------------- | -------- | ---------------------------- | --------- |
| `servicio_id`         | Number   | ID único del servicio        | ✅        |
| `nombre_servicio`     | Text     | Nombre del servicio          | ✅        |
| `categoria`           | Text     | Categoría del servicio       | ✅        |
| `precio_formateado`   | Currency | Precio con formato ($25,000) | ✅        |
| `duracion_formateada` | Time     | Duración legible (1h 30m)    | ✅        |
| `activo`              | Boolean  | Estado activo/inactivo       | ✅        |
| `fecha_creacion`      | DateTime | Fecha de creación            | ✅        |

### Filtros Laterales (list_filter)

```python
list_filter = [
    "activo",
    "categoria",
    "fecha_creacion",
    "fecha_actualizacion",
]
```

**Panel de Filtros**:

1. **Por Estado Activo**:

   - ✅ Activo
   - ❌ Inactivo
   - 🔄 Todos

2. **Por Categoría**:

   - Lista dinámica de todas las categorías existentes
   - Filtro de múltiples valores

3. **Por Fecha de Creación**:

   - Hoy
   - Últimos 7 días
   - Este mes
   - Este año

4. **Por Fecha de Actualización**:
   - Hoy
   - Últimos 7 días
   - Este mes
   - Este año

### Campos de Búsqueda (search_fields)

```python
search_fields = [
    "nombre_servicio",
    "descripcion",
    "categoria",
]
```

**Funcionalidad de Búsqueda**:

- Búsqueda en tiempo real
- Búsqueda parcial (contiene el término)
- Insensible a mayúsculas/minúsculas
- Búsqueda en múltiples campos simultáneamente

**Ejemplos de Búsqueda**:

- `"manicure"` → encuentra "Manicure Básico", "Manicure Premium"
- `"premium"` → encuentra servicios con "premium" en nombre o descripción
- `"pedi"` → encuentra "Pedicure Completo", "Pedicure Express"

## Formulario de Edición

### Organización por Secciones (fieldsets)

#### 1. Información Básica

```python
("Información Básica", {
    "fields": (
        "nombre_servicio",
        "descripcion",
        "categoria",
    )
})
```

**Campos**:

- **Nombre del Servicio**: Campo de texto requerido
- **Descripción**: Campo de texto largo opcional
- **Categoría**: Campo de texto para clasificación

#### 2. Detalles del Servicio

```python
("Detalles del Servicio", {
    "fields": (
        "precio",
        "precio_formateado",
        "duracion_estimada",
        "duracion_formateada",
        "activo",
    )
})
```

**Campos**:

- **Precio**: Campo decimal editable
- **Precio Formateado**: Campo de solo lectura con formato de moneda
- **Duración Estimada**: Campo de duración editable (HH:MM:SS)
- **Duración Formateada**: Campo de solo lectura legible
- **Activo**: Checkbox para activar/desactivar

#### 3. Imagen (Colapsible)

```python
("Imagen", {
    "fields": ("imagen",),
    "classes": ("collapse",)
})
```

**Campos**:

- **Imagen**: Campo de subida de archivos opcional
- **Sección Colapsible**: Se puede expandir/contraer

#### 4. Información del Sistema (Colapsible)

```python
("Información del Sistema", {
    "fields": (
        "servicio_id",
        "fecha_creacion",
        "fecha_actualizacion",
    ),
    "classes": ("collapse",),
})
```

**Campos de Solo Lectura**:

- **ID del Servicio**: Identificador único
- **Fecha de Creación**: Timestamp automático
- **Fecha de Actualización**: Timestamp automático

### Campos de Solo Lectura (readonly_fields)

```python
readonly_fields = [
    "servicio_id",
    "fecha_creacion",
    "fecha_actualizacion",
    "precio_formateado",
    "duracion_formateada",
]
```

Estos campos se muestran pero no se pueden editar directamente.

## Métodos Personalizados

### precio_formateado

```python
def precio_formateado(self, obj):
    """Muestra el precio formateado con símbolo de moneda"""
    return f"${obj.precio:,.0f}"

precio_formateado.short_description = "Precio"
precio_formateado.admin_order_field = "precio"
```

**Características**:

- Formatea el precio con símbolo de moneda
- Agrega separadores de miles
- Es ordenable por el campo precio original
- Se muestra como "Precio" en la interfaz

**Ejemplos**:

- `25000.00` → `"$25,000"`
- `1500.50` → `"$1,501"` (redondeado)
- `150000.00` → `"$150,000"`

### duracion_formateada

```python
def duracion_formateada(self, obj):
    """Muestra la duración en formato legible"""
    if obj.duracion_estimada:
        total_seconds = obj.duracion_estimada.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    return "No especificado"

duracion_formateada.short_description = "Duración"
duracion_formateada.admin_order_field = "duracion_estimada"
```

**Características**:

- Convierte timedelta a formato legible
- Maneja casos con y sin horas
- Muestra "No especificado" si es None
- Es ordenable por el campo duracion_estimada

**Ejemplos**:

- `timedelta(hours=1, minutes=30)` → `"1h 30m"`
- `timedelta(minutes=45)` → `"45m"`
- `None` → `"No especificado"`

## Acciones Personalizadas

### activar_servicios

```python
def activar_servicios(self, request, queryset):
    """Activa los servicios seleccionados"""
    updated = queryset.update(activo=True)
    self.message_user(request, f"{updated} servicios activados exitosamente.")

activar_servicios.short_description = "Activar servicios seleccionados"
```

**Funcionalidad**:

- Activa múltiples servicios a la vez
- Muestra mensaje de confirmación con cantidad actualizada
- Disponible en el dropdown de acciones

### desactivar_servicios

```python
def desactivar_servicios(self, request, queryset):
    """Desactiva los servicios seleccionados"""
    updated = queryset.update(activo=False)
    self.message_user(request, f"{updated} servicios desactivados exitosamente.")

desactivar_servicios.short_description = "Desactivar servicios seleccionados"
```

**Funcionalidad**:

- Desactiva múltiples servicios a la vez
- Muestra mensaje de confirmación
- Útil para mantenimiento masivo

## Configuración de Paginación

### Configuración de Lista

```python
list_per_page = 25          # Servicios por página
list_max_show_all = 100     # Máximo para "mostrar todos"
list_editable = ["activo"]  # Campos editables en línea
```

**Características**:

- **25 servicios por página**: Balance entre usabilidad y performance
- **Máximo 100**: Límite razonable para "mostrar todos"
- **Edición en línea**: El campo `activo` se puede editar directamente en la lista

## Ordenamiento

### Ordenamiento por Defecto

```python
ordering = ["nombre_servicio"]
```

Los servicios se ordenan alfabéticamente por nombre por defecto.

### Campos Ordenables

Todos los campos en `list_display` son ordenables:

- Nombre del servicio (alfabético)
- Categoría (alfabético)
- Precio (numérico)
- Duración (temporal)
- Estado activo (booleano)
- Fecha de creación (cronológico)

## Optimizaciones

### Consultas Optimizadas

```python
def get_queryset(self, request):
    """Optimizar consultas"""
    return super().get_queryset(request)
```

**Optimizaciones Aplicadas**:

- Consulta base sin optimizaciones adicionales por ahora
- Preparado para agregar `select_related` o `prefetch_related` según sea necesario

### Performance

**Configuraciones para Performance**:

- Paginación limitada (25 por página)
- Campos computados eficientes
- Filtros indexados
- Búsqueda optimizada

## Casos de Uso Comunes

### 1. Crear Nuevo Servicio

**Proceso**:

1. Acceder a `/admin/services/servicio/add/`
2. Completar "Información Básica":
   - Nombre del servicio (requerido)
   - Descripción (opcional)
   - Categoría (opcional)
3. Completar "Detalles del Servicio":
   - Precio (requerido)
   - Duración estimada (opcional)
   - Estado activo (default: True)
4. Agregar imagen si es necesario
5. Guardar

### 2. Búsqueda de Servicios

**Métodos de Búsqueda**:

- **Búsqueda rápida**: Usar el campo de búsqueda superior
- **Filtros**: Usar el panel lateral de filtros
- **Combinación**: Combinar búsqueda + filtros para resultados precisos

**Ejemplos**:

- Buscar "manicure" + filtrar por "activo" = servicios de manicure activos
- Filtrar por categoría "Pedicure" + ordenar por precio

### 3. Gestión Masiva

**Activar/Desactivar en Masa**:

1. Seleccionar servicios usando checkboxes
2. Elegir acción en el dropdown superior
3. Confirmar la acción
4. Ver mensaje de confirmación

### 4. Edición Rápida

**Cambiar Estado**:

- Usar el campo editable `activo` directamente en la lista
- Cambiar múltiples estados sin entrar al formulario de edición

### 5. Análisis de Datos

**Uso de Filtros para Análisis**:

- Filtrar por fecha de creación para ver servicios nuevos
- Filtrar por categoría para análisis por tipo
- Combinar filtros para reportes específicos

## Mensajes del Sistema

### Mensajes de Confirmación

**Acciones Exitosas**:

- `"El servicio se agregó exitosamente."`
- `"El servicio se cambió exitosamente."`
- `"5 servicios activados exitosamente."`
- `"3 servicios desactivados exitosamente."`

**Mensajes de Error**:

- Validaciones de campo (precio negativo, nombre duplicado)
- Errores de formato en duración
- Errores de subida de imagen

### Validaciones en Tiempo Real

**Validaciones del Formulario**:

- Nombre del servicio único
- Precio mayor a 0
- Formato de duración válido
- Tamaño de imagen permitido

## Extensibilidad

### Agregando Nuevos Filtros

```python
# Ejemplo de filtro personalizado
class PrecioRangoFilter(admin.SimpleListFilter):
    title = 'rango de precio'
    parameter_name = 'precio_rango'

    def lookups(self, request, model_admin):
        return (
            ('economico', 'Económico (< $30,000)'),
            ('medio', 'Medio ($30,000 - $50,000)'),
            ('premium', 'Premium (> $50,000)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'economico':
            return queryset.filter(precio__lt=30000)
        if self.value() == 'medio':
            return queryset.filter(precio__gte=30000, precio__lte=50000)
        if self.value() == 'premium':
            return queryset.filter(precio__gt=50000)
```

### Agregando Nuevas Acciones

```python
def duplicar_servicios(self, request, queryset):
    """Duplica los servicios seleccionados"""
    duplicados = 0
    for servicio in queryset:
        servicio.pk = None
        servicio.nombre_servicio = f"Copia de {servicio.nombre_servicio}"
        servicio.save()
        duplicados += 1

    self.message_user(request, f"{duplicados} servicios duplicados exitosamente.")

duplicar_servicios.short_description = "Duplicar servicios seleccionados"
```

### Integrando con Aplicaciones Relacionadas

```python
# Ejemplo de inline para detalles de citas (futuro)
class DetalleCitaInline(admin.TabularInline):
    model = DetalleCita
    extra = 0
    readonly_fields = ['cita', 'precio_acordado']
    can_delete = False

# En ServicioAdmin
inlines = [DetalleCitaInline]
```

## Permisos y Seguridad

### Permisos por Defecto

**Permisos Automáticos**:

- `services.add_servicio` - Agregar servicio
- `services.change_servicio` - Cambiar servicio
- `services.delete_servicio` - Eliminar servicio
- `services.view_servicio` - Ver servicio

### Personalización de Permisos

```python
def has_delete_permission(self, request, obj=None):
    """Personalizar permisos de eliminación"""
    if obj and obj.detalle_citas.exists():
        return False  # No eliminar si tiene citas
    return super().has_delete_permission(request, obj)
```

## Estado Actual

✅ **Configuración Completa**

- Interfaz administrativa completa
- Campos personalizados y formateo
- Filtros y búsqueda optimizados
- Acciones masivas implementadas
- Formulario organizado por secciones
- Validaciones integradas
- Paginación configurada
- Mensajes informativos

## Capturas de Funcionalidad

### Lista de Servicios

- Vista tabular con todos los campos relevantes
- Filtros laterales dinámicos
- Búsqueda en tiempo real
- Acciones masivas disponibles
- Paginación eficiente

### Formulario de Edición

- Organizado en secciones lógicas
- Campos computados de solo lectura
- Validaciones en tiempo real
- Interfaz intuitiva y clara

### Funcionalidades Avanzadas

- Edición en línea del estado activo
- Acciones personalizadas para gestión masiva
- Filtros inteligentes por fecha y categoría
- Búsqueda flexible en múltiples campos
