# Documentación del Panel de Administración - Appointments

## Visión General

El panel de administración de Django para la aplicación appointments proporciona una interfaz web completa para gestionar citas y detalles de servicios desde el backend. Esta configuración permite a los administradores realizar operaciones CRUD de manera intuitiva y eficiente, con funcionalidades avanzadas como inlines para gestionar servicios dentro de las citas.

## Archivo Principal

**Ubicación**: `apps/appointments/admin.py`

## Configuración del Admin

### Registro de Modelos

```python
from django.contrib import admin
from .models.cita import Cita
from .models.detalle_cita import DetalleCita

# Configuración de inlines
class DetalleCitaInline(admin.TabularInline):
    model = DetalleCita
    extra = 1
    # Configuración detallada...

@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    inlines = [DetalleCitaInline]
    # Configuración detallada...

@admin.register(DetalleCita)
class DetalleCitaAdmin(admin.ModelAdmin):
    # Configuración detallada...
```

---

## CitaAdmin - Configuración Completa

### Display de Lista

```python
list_display = [
    "id",
    "cliente_info",
    "fecha_cita_formateada",
    "estado",
    "total_formateado",
    "cantidad_servicios",
    "fecha_creacion",
]
```

**Propósito**: Define qué campos se muestran en la vista de lista principal.

**Vista Resultante**:
| ID | Cliente | Fecha Cita | Estado | Total | Servicios | Creada |
|----|---------|------------|--------|-------|-----------|--------|
| 1 | Juan Pérez | 20/01/2024 14:30 | Programada | $85,000 | 2 | 15/01/2024 |
| 2 | María García | 22/01/2024 16:00 | Confirmada | $120,000 | 3 | 16/01/2024 |

### Métodos Personalizados para Display

#### `cliente_info(self, obj)`

```python
def cliente_info(self, obj):
    """
    Muestra información del cliente con enlace
    """
    url = reverse("admin:clients_cliente_change", args=[obj.cliente.cliente_id])
    return format_html('<a href="{}">{}</a>', url, obj.cliente.nombre_completo)

cliente_info.short_description = "Cliente"
cliente_info.admin_order_field = "cliente__nombre"
```

**Propósito**: Muestra el nombre del cliente como enlace clickeable al registro del cliente.

#### `fecha_cita_formateada(self, obj)`

```python
def fecha_cita_formateada(self, obj):
    """
    Formatea la fecha de la cita para mejor legibilidad
    """
    return obj.fecha_cita.strftime("%d/%m/%Y %H:%M")

fecha_cita_formateada.short_description = "Fecha y Hora"
fecha_cita_formateada.admin_order_field = "fecha_cita"
```

#### `total_formateado(self, obj)`

```python
def total_formateado(self, obj):
    """
    Formatea el total con símbolo de moneda
    """
    return f"${obj.total:,.0f}"

total_formateado.short_description = "Total"
total_formateado.admin_order_field = "total"
```

#### `cantidad_servicios(self, obj)`

```python
def cantidad_servicios(self, obj):
    """
    Cuenta la cantidad de servicios en la cita
    """
    return obj.detalles.count()

cantidad_servicios.short_description = "# Servicios"
```

### Filtros Laterales

```python
list_filter = [
    "estado",
    "fecha_cita",
    "cliente",
    "fecha_creacion",
    "fecha_actualizacion",
]
```

**Funcionalidad**:

- **Por Estado**: Filtrar por estado de la cita
- **Por Fecha de Cita**: Filtros temporales de citas
- **Por Cliente**: Filtrar por cliente específico
- **Por Fecha de Creación**: Filtros de creación
- **Por Fecha de Actualización**: Filtros de última modificación

**Panel Lateral**:

```
FILTROS
├── Por estado
│   ├── Programada (45)
│   ├── Confirmada (23)
│   ├── En Proceso (8)
│   ├── Completada (89)
│   └── Cancelada (12)
├── Por fecha cita
│   ├── Hoy (12)
│   ├── Esta semana (34)
│   ├── Este mes (89)
│   └── Este año (177)
├── Por cliente
│   ├── Juan Pérez (5)
│   ├── María García (3)
│   └── [Más opciones...]
└── Por fecha creación
    ├── Hoy (3)
    └── [Más opciones...]
```

### Búsqueda

```python
search_fields = [
    "cliente__nombre",
    "cliente__apellido",
    "cliente__telefono",
    "observaciones",
]
```

**Funcionalidad**: Permite buscar por:

- Nombre del cliente
- Apellido del cliente
- Teléfono del cliente
- Observaciones de la cita

**Ejemplo de Búsquedas**:

```
"Juan"          # Busca clientes con nombre Juan
"3001234567"    # Busca por teléfono
"manicure"      # Busca en observaciones
```

### Ordenamiento

```python
ordering = ["-fecha_cita"]
```

**Propósito**: Ordena las citas por fecha de cita (más recientes primero).

### Configuración de Formulario

```python
fields = [
    ("cliente", "fecha_cita"),
    "estado",
    "observaciones",
]

readonly_fields = ["total", "fecha_creacion", "fecha_actualizacion"]
```

**Layout del Formulario**:

```
┌─────────────────────────────────────┐
│ Cliente: [Select] Fecha: [DateTime] │
├─────────────────────────────────────┤
│ Estado: [Select]                    │
├─────────────────────────────────────┤
│ Observaciones: [TextArea]           │
├─────────────────────────────────────┤
│ Total: $85,000 (Solo lectura)       │
│ Creada: 15/01/2024 10:30           │
│ Actualizada: 15/01/2024 10:30      │
└─────────────────────────────────────┘
```

### Configuración de Lista

```python
list_per_page = 25
list_max_show_all = 100
list_editable = ["estado"]
```

**Configuraciones**:

- **Paginación**: 25 citas por página
- **Mostrar todo**: Máximo 100 elementos
- **Edición rápida**: Campo estado editable desde la lista

---

## DetalleCitaInline - Configuración

### Configuración Básica

```python
class DetalleCitaInline(admin.TabularInline):
    model = DetalleCita
    extra = 1
    min_num = 0
    max_num = 10
    can_delete = True
```

**Parámetros**:

- **extra**: 1 fila vacía adicional para agregar servicios
- **min_num**: Mínimo 0 servicios (puede no tener servicios)
- **max_num**: Máximo 10 servicios por cita
- **can_delete**: Permite eliminar servicios

### Campos Mostrados

```python
fields = [
    "servicio",
    "cantidad",
    "precio",
    "subtotal_readonly",
]

readonly_fields = ["subtotal_readonly"]
```

**Vista Inline**:

| Servicio         | Cantidad | Precio   | Subtotal |
| ---------------- | -------- | -------- | -------- |
| Manicure Clásico | 1        | $45,000  | $45,000  |
| Pedicure Spa     | 1        | $40,000  | $40,000  |
| [Nuevo servicio] | [1]      | [Precio] | [Auto]   |

### Métodos Personalizados Inline

#### `subtotal_readonly(self, obj)`

```python
def subtotal_readonly(self, obj):
    """
    Muestra el subtotal calculado (solo lectura)
    """
    if obj.pk:
        return f"${obj.subtotal:,.0f}"
    return "-"

subtotal_readonly.short_description = "Subtotal"
```

### Configuraciones Avanzadas

```python
autocomplete_fields = ["servicio"]
raw_id_fields = []

def get_formset(self, request, obj=None, **kwargs):
    """
    Personaliza el formset para validaciones adicionales
    """
    formset = super().get_formset(request, obj, **kwargs)

    # Validaciones personalizadas aquí

    return formset
```

---

## DetalleCitaAdmin - Configuración Independiente

### Display de Lista

```python
list_display = [
    "id",
    "cita_info",
    "servicio_info",
    "cantidad",
    "precio_formateado",
    "subtotal_formateado",
]
```

**Vista Resultante**:
| ID | Cita | Servicio | Cantidad | Precio | Subtotal |
|----|------|----------|----------|---------|----------|
| 1 | Cita #1 - Juan Pérez | Manicure Clásico | 1 | $45,000 | $45,000 |
| 2 | Cita #1 - Juan Pérez | Pedicure Spa | 1 | $40,000 | $40,000 |

### Métodos Personalizados

#### `cita_info(self, obj)`

```python
def cita_info(self, obj):
    """
    Muestra información de la cita con enlace
    """
    url = reverse("admin:appointments_cita_change", args=[obj.cita.id])
    return format_html(
        '<a href="{}">Cita #{} - {}</a>',
        url,
        obj.cita.id,
        obj.cita.cliente.nombre_completo
    )

cita_info.short_description = "Cita"
cita_info.admin_order_field = "cita"
```

#### `servicio_info(self, obj)`

```python
def servicio_info(self, obj):
    """
    Muestra información del servicio
    """
    return f"{obj.servicio.nombre} (${obj.servicio.precio:,.0f})"

servicio_info.short_description = "Servicio"
servicio_info.admin_order_field = "servicio__nombre"
```

### Filtros y Búsqueda

```python
list_filter = [
    "cita__estado",
    "servicio",
    "cita__fecha_cita",
]

search_fields = [
    "cita__cliente__nombre",
    "cita__cliente__apellido",
    "servicio__nombre",
]
```

---

## Acciones Personalizadas

### Acciones para Citas

```python
actions = ["marcar_como_completada", "marcar_como_cancelada", "confirmar_citas"]

def marcar_como_completada(self, request, queryset):
    """
    Marca las citas seleccionadas como completadas
    """
    updated = queryset.filter(
        estado__in=['programada', 'confirmada', 'en_proceso']
    ).update(estado='completada')

    self.message_user(
        request,
        f"{updated} citas marcadas como completadas."
    )

marcar_como_completada.short_description = "Marcar como completadas"

def marcar_como_cancelada(self, request, queryset):
    """
    Marca las citas seleccionadas como canceladas
    """
    updated = queryset.filter(
        estado__in=['programada', 'confirmada']
    ).update(estado='cancelada')

    self.message_user(
        request,
        f"{updated} citas canceladas."
    )

marcar_como_cancelada.short_description = "Cancelar citas"

def confirmar_citas(self, request, queryset):
    """
    Confirma las citas programadas
    """
    updated = queryset.filter(estado='programada').update(estado='confirmada')

    self.message_user(
        request,
        f"{updated} citas confirmadas."
    )

confirmar_citas.short_description = "Confirmar citas"
```

### Acciones para Detalles

```python
def aplicar_descuento(self, request, queryset):
    """
    Aplica un descuento del 10% a los servicios seleccionados
    """
    for detalle in queryset:
        detalle.precio = detalle.precio * 0.9
        detalle.save()

    self.message_user(
        request,
        f"Descuento aplicado a {queryset.count()} servicios."
    )

aplicar_descuento.short_description = "Aplicar descuento 10%"
```

## Validaciones en el Admin

### Validaciones de Cita

```python
def save_model(self, request, obj, form, change):
    """
    Validaciones adicionales antes de guardar
    """
    # Validar fecha futura para citas nuevas
    if not change and obj.fecha_cita <= timezone.now():
        raise ValidationError("La fecha de la cita debe ser futura")

    # Validar cliente activo
    if not obj.cliente.activo:
        raise ValidationError("No se pueden crear citas para clientes inactivos")

    super().save_model(request, obj, form, change)
```

### Validaciones de DetalleCita

```python
def save_formset(self, request, form, formset, change):
    """
    Validaciones para el formset de detalles
    """
    instances = formset.save(commit=False)

    for instance in instances:
        # Validar precio no negativo
        if instance.precio <= 0:
            raise ValidationError("El precio debe ser mayor a cero")

        # Validar cantidad positiva
        if instance.cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor a cero")

        instance.save()

    formset.save_m2m()

    # Recalcular total de la cita
    if hasattr(form.instance, 'actualizar_total'):
        form.instance.actualizar_total()
```

## Permisos y Seguridad

### Permisos por Grupo

```python
def has_change_permission(self, request, obj=None):
    """
    Personalizar permisos de edición
    """
    if obj and obj.estado == 'completada':
        # Solo superusuarios pueden editar citas completadas
        return request.user.is_superuser

    return super().has_change_permission(request, obj)

def has_delete_permission(self, request, obj=None):
    """
    Personalizar permisos de eliminación
    """
    if obj and obj.estado in ['completada', 'cancelada']:
        # No permitir eliminar citas finalizadas
        return False

    return super().has_delete_permission(request, obj)
```

### Filtros por Usuario

```python
def get_queryset(self, request):
    """
    Filtrar citas según el usuario
    """
    qs = super().get_queryset(request)

    if request.user.is_superuser:
        return qs

    # Los empleados solo ven citas de los últimos 30 días
    if request.user.groups.filter(name='Empleados').exists():
        fecha_limite = timezone.now() - timedelta(days=30)
        return qs.filter(fecha_cita__gte=fecha_limite)

    return qs
```

## Configuraciones de Interfaz

### CSS y JavaScript Personalizados

```python
class Media:
    css = {
        'all': ('admin/css/appointments.css',)
    }
    js = ('admin/js/appointments.js',)
```

### Personalización de Formularios

```python
def get_form(self, request, obj=None, **kwargs):
    """
    Personalizar formulario según el contexto
    """
    form = super().get_form(request, obj, **kwargs)

    # Filtrar clientes activos
    form.base_fields['cliente'].queryset = Cliente.objects.filter(activo=True)

    # Si es edición, validar estado
    if obj:
        if obj.estado in ['completada', 'cancelada']:
            # Hacer solo lectura algunos campos
            form.base_fields['cliente'].disabled = True
            form.base_fields['fecha_cita'].disabled = True

    return form
```

## Reportes y Estadísticas

### Vista de Resumen

```python
def changelist_view(self, request, extra_context=None):
    """
    Agregar estadísticas al listado
    """
    extra_context = extra_context or {}

    # Estadísticas generales
    total_citas = Cita.objects.count()
    citas_hoy = Cita.objects.filter(fecha_cita__date=timezone.now().date()).count()
    ingresos_mes = Cita.objects.filter(
        fecha_cita__month=timezone.now().month,
        estado='completada'
    ).aggregate(total=Sum('total'))['total'] or 0

    extra_context.update({
        'total_citas': total_citas,
        'citas_hoy': citas_hoy,
        'ingresos_mes': ingresos_mes,
    })

    return super().changelist_view(request, extra_context)
```

## URLs del Admin

### URLs Generadas Automáticamente

```
/admin/appointments/cita/                    # Lista de citas
/admin/appointments/cita/add/                # Agregar cita
/admin/appointments/cita/1/change/           # Editar cita
/admin/appointments/cita/1/delete/           # Eliminar cita
/admin/appointments/cita/1/history/          # Historial de cita

/admin/appointments/detallecita/             # Lista de detalles
/admin/appointments/detallecita/add/         # Agregar detalle
/admin/appointments/detallecita/1/change/    # Editar detalle
```

## Consideraciones de Rendimiento

### Optimizaciones

```python
def get_queryset(self, request):
    """
    Optimizar consultas con select_related y prefetch_related
    """
    return super().get_queryset(request).select_related(
        'cliente'
    ).prefetch_related(
        'detalles__servicio'
    )
```

### Autocomplete

```python
autocomplete_fields = ['cliente']

class ClienteAdmin(admin.ModelAdmin):
    search_fields = ['nombre', 'apellido', 'telefono']
```

Esta configuración del panel de administración proporciona una interfaz completa y eficiente para gestionar citas y servicios, con validaciones robustas y una experiencia de usuario optimizada para los administradores del sistema.
