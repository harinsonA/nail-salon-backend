# Documentación de Admin - Payments App

## Visión General

La configuración del Django Admin para la aplicación payments proporciona una interfaz administrativa completa para gestionar pagos. Incluye filtros avanzados, búsquedas, acciones personalizadas y una presentación optimizada para facilitar la administración de pagos del salón de uñas.

## Archivo Principal

**Ubicación**: `apps/payments/admin.py`

## Configuración del Admin

### Imports y Dependencias

```python
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from django.utils import timezone
from django.urls import reverse
from django.http import HttpResponse
import csv
from apps.payments.models import Pago
from utils.choices import MetodoPago, EstadoPago
```

## PagoAdmin - Clase Principal

### Configuración Base

```python
@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    """
    Administración de pagos en Django Admin
    """

    # Campos mostrados en la lista
    list_display = [
        'pago_id_display',
        'cita_info_display',
        'cliente_nombre_display',
        'fecha_pago_display',
        'monto_formateado_display',
        'metodo_pago_display',
        'estado_pago_display',
        'referencia_pago',
        'fecha_creacion_display'
    ]

    # Campos filtrables en el sidebar
    list_filter = [
        'estado_pago',
        'metodo_pago',
        ('fecha_pago', admin.DateFieldListFilter),
        ('fecha_creacion', admin.DateFieldListFilter),
        'cita__estado_cita',
        ('monto_total', admin.SimpleListFilter),
    ]

    # Campos de búsqueda
    search_fields = [
        'id',
        'referencia_pago',
        'notas_pago',
        'cita__id',
        'cita__cliente__nombre',
        'cita__cliente__apellido',
        'cita__cliente__telefono',
    ]

    # Ordenamiento por defecto
    ordering = ['-fecha_pago', '-fecha_creacion']

    # Campos de solo lectura
    readonly_fields = [
        'id',
        'fecha_creacion',
        'fecha_actualizacion',
        'creado_por',
        'pago_completo_display',
        'dias_desde_pago',
    ]

    # Número de elementos por página
    list_per_page = 25
    list_max_show_all = 100

    # Paginación
    show_full_result_count = True

    # Campos editables directamente en la lista
    list_editable = ['estado_pago']

    # Enlaces clickeables
    list_display_links = ['pago_id_display', 'cita_info_display']

    # Campos incluidos en el formulario
    fields = [
        'cita',
        'fecha_pago',
        'monto_total',
        'metodo_pago',
        'estado_pago',
        'referencia_pago',
        'notas_pago',
        'id',
        'pago_completo_display',
        'dias_desde_pago',
        'fecha_creacion',
        'fecha_actualizacion',
        'creado_por',
    ]

    # Organización de campos en fieldsets
    fieldsets = [
        ('Información Básica', {
            'fields': ['cita', 'fecha_pago', 'monto_total']
        }),
        ('Detalles del Pago', {
            'fields': ['metodo_pago', 'estado_pago', 'referencia_pago'],
            'classes': ['wide']
        }),
        ('Observaciones', {
            'fields': ['notas_pago'],
            'classes': ['collapse']
        }),
        ('Información del Sistema', {
            'fields': [
                'id',
                'pago_completo_display',
                'dias_desde_pago',
                'fecha_creacion',
                'fecha_actualizacion',
                'creado_por'
            ],
            'classes': ['collapse']
        }),
    ]

    # Filtros de fecha rápidos
    date_hierarchy = 'fecha_pago'

    # Acciones disponibles
    actions = [
        'marcar_como_pagado',
        'marcar_como_pendiente',
        'exportar_a_csv',
        'generar_reporte_pagos',
    ]
```

### Métodos de Visualización

#### `pago_id_display(self, obj)`

```python
def pago_id_display(self, obj):
    """
    Mostrar ID del pago con enlace al detalle
    """
    url = reverse('admin:payments_pago_change', args=[obj.pk])
    return format_html('<a href="{}">Pago #{}</a>', url, obj.id)

pago_id_display.short_description = 'ID Pago'
pago_id_display.admin_order_field = 'id'
```

#### `cita_info_display(self, obj)`

```python
def cita_info_display(self, obj):
    """
    Mostrar información de la cita con enlace
    """
    if obj.cita:
        url = reverse('admin:appointments_cita_change', args=[obj.cita.pk])
        fecha_cita = obj.cita.fecha_cita.strftime('%d/%m/%Y %H:%M')
        return format_html(
            '<a href="{}">Cita #{} - {}</a>',
            url,
            obj.cita.id,
            fecha_cita
        )
    return '-'

cita_info_display.short_description = 'Cita'
cita_info_display.admin_order_field = 'cita__fecha_cita'
```

#### `cliente_nombre_display(self, obj)`

```python
def cliente_nombre_display(self, obj):
    """
    Mostrar nombre del cliente con enlace
    """
    if obj.cita and obj.cita.cliente:
        cliente = obj.cita.cliente
        url = reverse('admin:clients_cliente_change', args=[cliente.pk])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            cliente.nombre_completo
        )
    return '-'

cliente_nombre_display.short_description = 'Cliente'
cliente_nombre_display.admin_order_field = 'cita__cliente__nombre'
```

#### `fecha_pago_display(self, obj)`

```python
def fecha_pago_display(self, obj):
    """
    Mostrar fecha de pago formateada con iconos
    """
    if obj.fecha_pago:
        fecha = obj.fecha_pago.strftime('%d/%m/%Y %H:%M')

        # Agregar icono según proximidad
        dias_diff = (timezone.now().date() - obj.fecha_pago.date()).days

        if dias_diff == 0:
            icon = '🟢'  # Hoy
        elif dias_diff <= 7:
            icon = '🟡'  # Esta semana
        elif dias_diff <= 30:
            icon = '🟠'  # Este mes
        else:
            icon = '🔴'  # Más antiguo

        return format_html('{} {}', icon, fecha)
    return '-'

fecha_pago_display.short_description = 'Fecha Pago'
fecha_pago_display.admin_order_field = 'fecha_pago'
```

#### `monto_formateado_display(self, obj)`

```python
def monto_formateado_display(self, obj):
    """
    Mostrar monto formateado con color según el valor
    """
    if obj.monto_total:
        monto_str = f"${obj.monto_total:,.0f}".replace(',', '.')

        # Color según el monto
        if obj.monto_total >= 100000:
            color = '#d32f2f'  # Rojo para montos altos
            weight = 'bold'
        elif obj.monto_total >= 50000:
            color = '#f57c00'  # Naranja para montos medios
            weight = 'bold'
        else:
            color = '#388e3c'  # Verde para montos normales
            weight = 'normal'

        return format_html(
            '<span style="color: {}; font-weight: {}">{}</span>',
            color,
            weight,
            monto_str
        )
    return '$0'

monto_formateado_display.short_description = 'Monto'
monto_formateado_display.admin_order_field = 'monto_total'
```

#### `metodo_pago_display(self, obj)`

```python
def metodo_pago_display(self, obj):
    """
    Mostrar método de pago con icono
    """
    iconos = {
        'EFECTIVO': '💵',
        'TARJETA': '💳',
        'TRANSFERENCIA': '🏦',
        'CHEQUE': '📋'
    }

    icon = iconos.get(obj.metodo_pago, '❓')
    label = dict(MetodoPago.CHOICES).get(obj.metodo_pago, obj.metodo_pago)

    return format_html('{} {}', icon, label)

metodo_pago_display.short_description = 'Método'
metodo_pago_display.admin_order_field = 'metodo_pago'
```

#### `estado_pago_display(self, obj)`

```python
def estado_pago_display(self, obj):
    """
    Mostrar estado de pago con color y badge
    """
    colores = {
        'PENDIENTE': '#ff9800',  # Naranja
        'PAGADO': '#4caf50',     # Verde
        'CANCELADO': '#f44336'   # Rojo
    }

    color = colores.get(obj.estado_pago, '#9e9e9e')
    label = dict(EstadoPago.CHOICES).get(obj.estado_pago, obj.estado_pago)

    return format_html(
        '<span style="background-color: {}; color: white; padding: 2px 8px; '
        'border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
        color,
        label
    )

estado_pago_display.short_description = 'Estado'
estado_pago_display.admin_order_field = 'estado_pago'
```

#### `fecha_creacion_display(self, obj)`

```python
def fecha_creacion_display(self, obj):
    """
    Mostrar fecha de creación con tiempo relativo
    """
    if obj.fecha_creacion:
        fecha = obj.fecha_creacion.strftime('%d/%m/%Y %H:%M')

        # Calcular tiempo relativo
        diff = timezone.now() - obj.fecha_creacion

        if diff.days == 0:
            if diff.seconds < 3600:
                minutos = diff.seconds // 60
                relativo = f'{minutos}m'
            else:
                horas = diff.seconds // 3600
                relativo = f'{horas}h'
        else:
            relativo = f'{diff.days}d'

        return format_html('{}<br><small style="color: #666;">{}</small>', fecha, relativo)
    return '-'

fecha_creacion_display.short_description = 'Creado'
fecha_creacion_display.admin_order_field = 'fecha_creacion'
```

### Campos de Solo Lectura Calculados

#### `pago_completo_display(self, obj)`

```python
def pago_completo_display(self, obj):
    """
    Indicar si el pago cubre completamente la cita
    """
    if obj.cita and obj.monto_total:
        es_completo = obj.monto_total >= obj.cita.monto_total

        if es_completo:
            return format_html(
                '<span style="color: #4caf50; font-weight: bold;">✓ Completo</span>'
            )
        else:
            porcentaje = (obj.monto_total / obj.cita.monto_total) * 100
            return format_html(
                '<span style="color: #ff9800; font-weight: bold;">⚠ Parcial ({}%)</span>',
                int(porcentaje)
            )
    return '-'

pago_completo_display.short_description = 'Cobertura'
```

#### `dias_desde_pago(self, obj)`

```python
def dias_desde_pago(self, obj):
    """
    Calcular días transcurridos desde el pago
    """
    if obj.fecha_pago:
        dias = (timezone.now().date() - obj.fecha_pago.date()).days

        if dias == 0:
            return 'Hoy'
        elif dias == 1:
            return 'Ayer'
        else:
            return f'{dias} días'
    return '-'

dias_desde_pago.short_description = 'Antigüedad'
```

## Filtros Personalizados

### MontoFilter

```python
class MontoFilter(admin.SimpleListFilter):
    """
    Filtro personalizado para rangos de monto
    """
    title = 'Rango de Monto'
    parameter_name = 'monto_rango'

    def lookups(self, request, model_admin):
        return [
            ('bajo', 'Hasta $25,000'),
            ('medio', '$25,001 - $50,000'),
            ('alto', '$50,001 - $100,000'),
            ('muy_alto', 'Más de $100,000'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'bajo':
            return queryset.filter(monto_total__lte=25000)
        elif self.value() == 'medio':
            return queryset.filter(monto_total__gt=25000, monto_total__lte=50000)
        elif self.value() == 'alto':
            return queryset.filter(monto_total__gt=50000, monto_total__lte=100000)
        elif self.value() == 'muy_alto':
            return queryset.filter(monto_total__gt=100000)
        return queryset
```

### EstadoCitaFilter

```python
class EstadoCitaFilter(admin.SimpleListFilter):
    """
    Filtro por estado de la cita asociada
    """
    title = 'Estado de Cita'
    parameter_name = 'estado_cita'

    def lookups(self, request, model_admin):
        return [
            ('programada', 'Programada'),
            ('confirmada', 'Confirmada'),
            ('en_proceso', 'En Proceso'),
            ('completada', 'Completada'),
            ('cancelada', 'Cancelada'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(cita__estado_cita=self.value().upper())
        return queryset
```

## Acciones Personalizadas

### `marcar_como_pagado(self, request, queryset)`

```python
def marcar_como_pagado(self, request, queryset):
    """
    Acción para marcar pagos seleccionados como pagados
    """
    # Filtrar solo pagos pendientes
    pagos_pendientes = queryset.filter(estado_pago='PENDIENTE')

    if not pagos_pendientes.exists():
        self.message_user(
            request,
            'No hay pagos pendientes en la selección',
            level='warning'
        )
        return

    # Actualizar estados
    updated = pagos_pendientes.update(estado_pago='PAGADO')

    # Mensaje de confirmación
    self.message_user(
        request,
        f'{updated} pago(s) marcado(s) como pagado(s)',
        level='success'
    )

marcar_como_pagado.short_description = 'Marcar como PAGADO'
```

### `marcar_como_pendiente(self, request, queryset)`

```python
def marcar_como_pendiente(self, request, queryset):
    """
    Acción para marcar pagos como pendientes
    """
    # Excluir pagos cancelados
    pagos_modificables = queryset.exclude(estado_pago='CANCELADO')

    if not pagos_modificables.exists():
        self.message_user(
            request,
            'No hay pagos modificables en la selección',
            level='warning'
        )
        return

    updated = pagos_modificables.update(estado_pago='PENDIENTE')

    self.message_user(
        request,
        f'{updated} pago(s) marcado(s) como pendiente(s)',
        level='success'
    )

marcar_como_pendiente.short_description = 'Marcar como PENDIENTE'
```

### `exportar_a_csv(self, request, queryset)`

```python
def exportar_a_csv(self, request, queryset):
    """
    Exportar pagos seleccionados a CSV
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="pagos_export.csv"'

    writer = csv.writer(response)

    # Encabezados
    writer.writerow([
        'ID Pago',
        'ID Cita',
        'Cliente',
        'Fecha Pago',
        'Monto',
        'Método',
        'Estado',
        'Referencia',
        'Notas'
    ])

    # Datos
    for pago in queryset.select_related('cita__cliente'):
        writer.writerow([
            pago.id,
            pago.cita.id if pago.cita else '',
            pago.cita.cliente.nombre_completo if pago.cita and pago.cita.cliente else '',
            pago.fecha_pago.strftime('%d/%m/%Y %H:%M') if pago.fecha_pago else '',
            pago.monto_total,
            dict(MetodoPago.CHOICES).get(pago.metodo_pago, pago.metodo_pago),
            dict(EstadoPago.CHOICES).get(pago.estado_pago, pago.estado_pago),
            pago.referencia_pago or '',
            pago.notas_pago or ''
        ])

    return response

exportar_a_csv.short_description = 'Exportar a CSV'
```

### `generar_reporte_pagos(self, request, queryset)`

```python
def generar_reporte_pagos(self, request, queryset):
    """
    Generar reporte estadístico de pagos seleccionados
    """
    # Calcular estadísticas
    total_pagos = queryset.count()
    total_monto = queryset.aggregate(Sum('monto_total'))['monto_total__sum'] or 0
    promedio_monto = total_monto / total_pagos if total_pagos > 0 else 0

    # Estadísticas por estado
    stats_estado = queryset.values('estado_pago').annotate(
        count=Count('id'),
        total=Sum('monto_total')
    )

    # Estadísticas por método
    stats_metodo = queryset.values('metodo_pago').annotate(
        count=Count('id'),
        total=Sum('monto_total')
    )

    # Crear mensaje de reporte
    mensaje = f"""
    REPORTE DE PAGOS SELECCIONADOS:

    Total de pagos: {total_pagos}
    Monto total: ${total_monto:,.0f}
    Promedio por pago: ${promedio_monto:,.0f}

    Por Estado:
    """

    for stat in stats_estado:
        estado_label = dict(EstadoPago.CHOICES).get(stat['estado_pago'], stat['estado_pago'])
        mensaje += f"  {estado_label}: {stat['count']} pagos - ${stat['total']:,.0f}\n"

    mensaje += "\nPor Método:\n"
    for stat in stats_metodo:
        metodo_label = dict(MetodoPago.CHOICES).get(stat['metodo_pago'], stat['metodo_pago'])
        mensaje += f"  {metodo_label}: {stat['count']} pagos - ${stat['total']:,.0f}\n"

    self.message_user(request, mensaje)

generar_reporte_pagos.short_description = 'Generar reporte estadístico'
```

## Configuración Avanzada

### Optimización de Consultas

```python
def get_queryset(self, request):
    """
    Optimizar consultas con select_related y prefetch_related
    """
    queryset = super().get_queryset(request)
    return queryset.select_related(
        'cita',
        'cita__cliente',
        'cita__servicio',
        'creado_por'
    )
```

### Personalización del Formulario

```python
def get_form(self, request, obj=None, **kwargs):
    """
    Personalizar el formulario según el usuario y contexto
    """
    form = super().get_form(request, obj, **kwargs)

    # Limitar opciones de cita para usuarios no administradores
    if not request.user.is_superuser:
        form.base_fields['cita'].queryset = form.base_fields['cita'].queryset.filter(
            estado_cita__in=['PROGRAMADA', 'CONFIRMADA']
        )

    # Asignar valores por defecto
    if not obj:  # Nuevo objeto
        form.base_fields['fecha_pago'].initial = timezone.now()
        form.base_fields['estado_pago'].initial = 'PENDIENTE'

    return form
```

### Validaciones Adicionales

```python
def save_model(self, request, obj, form, change):
    """
    Validaciones adicionales antes de guardar
    """
    # Asignar usuario creador si es nuevo
    if not change:
        obj.creado_por = request.user

    # Validar reglas de negocio
    if obj.estado_pago == 'PAGADO' and obj.cita:
        if obj.monto_total < obj.cita.monto_total:
            messages.error(
                request,
                'Un pago no puede marcarse como PAGADO si no cubre el costo total de la cita'
            )
            return

    super().save_model(request, obj, form, change)
```

## Permisos y Seguridad

### Control de Acceso

```python
def has_change_permission(self, request, obj=None):
    """
    Controlar permisos de modificación
    """
    # Solo el creador o administradores pueden modificar
    if obj and not request.user.is_superuser:
        return obj.creado_por == request.user

    return super().has_change_permission(request, obj)

def has_delete_permission(self, request, obj=None):
    """
    Controlar permisos de eliminación
    """
    # No se pueden eliminar pagos completados
    if obj and obj.estado_pago == 'PAGADO':
        return False

    return super().has_delete_permission(request, obj)
```

### Auditoría de Cambios

```python
def log_change(self, request, object, message):
    """
    Registrar cambios con información adicional
    """
    # Agregar información del contexto
    if hasattr(object, 'cita') and object.cita:
        message = f"{message} (Cita #{object.cita.id})"

    super().log_change(request, object, message)
```

## Integración con Otras Apps

### Enlaces a Apps Relacionadas

```python
def response_change(self, request, obj):
    """
    Redirigir a apps relacionadas después de cambios
    """
    response = super().response_change(request, obj)

    # Si se guarda y continúa editando, agregar enlaces útiles
    if '_continue' in request.POST:
        messages.info(
            request,
            format_html(
                'Enlaces relacionados: <a href="{}">Ver Cita</a> | <a href="{}">Ver Cliente</a>',
                reverse('admin:appointments_cita_change', args=[obj.cita.pk]) if obj.cita else '#',
                reverse('admin:clients_cliente_change', args=[obj.cita.cliente.pk]) if obj.cita and obj.cita.cliente else '#'
            )
        )

    return response
```

---

**Última actualización**: Agosto 2025  
**Versión**: 1.0  
**Estado**: ✅ Completamente configurado y funcional
