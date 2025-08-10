# Documentación del Panel de Administración - Cliente

## Visión General

El panel de administración de Django para la aplicación clients proporciona una interfaz web completa para gestionar clientes desde el backend. Esta configuración permite a los administradores realizar operaciones CRUD de manera intuitiva y eficiente.

## Archivo Principal

**Ubicación**: `apps/clients/admin.py`

## Configuración del Admin

### Registro del Modelo

```python
from django.contrib import admin
from .models.cliente import Cliente

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    # Configuración detallada...
```

El decorador `@admin.register(Cliente)` registra automáticamente el modelo con la configuración personalizada.

---

## ClienteAdmin - Configuración Completa

### Display de Lista

```python
list_display = [
    "cliente_id",
    "nombre",
    "apellido",
    "telefono",
    "email",
    "fecha_registro",
    "activo",
]
```

**Propósito**: Define qué campos se muestran en la vista de lista principal.

**Vista Resultante**:
| ID | Nombre | Apellido | Teléfono | Email | Fecha Registro | Activo |
|----|--------|----------|----------|-------|----------------|--------|
| 1 | Juan | Pérez | 3001234567 | juan@email.com | 2024-01-15 | ✓ |
| 2 | María | García | 3009876543 | maria@email.com | 2024-01-16 | ✓ |

### Filtros Laterales

```python
list_filter = ["activo", "fecha_registro", "fecha_creacion"]
```

**Funcionalidad**:

- **Por Activo**: Filtrar clientes activos/inactivos
- **Por Fecha de Registro**: Filtros por día, semana, mes, año
- **Por Fecha de Creación**: Filtros temporales de creación

**Panel Lateral**:

```
FILTROS
├── Por activo
│   ├── Sí (120)
│   └── No (15)
├── Por fecha registro
│   ├── Hoy (5)
│   ├── Esta semana (23)
│   ├── Este mes (87)
│   └── Este año (135)
└── Por fecha creación
    ├── Hoy (5)
    └── [Más opciones...]
```

### Búsqueda

```python
search_fields = ["nombre", "apellido", "telefono", "email"]
```

**Características**:

- Búsqueda por múltiples campos simultáneamente
- Búsqueda parcial (contiene)
- Case-insensitive
- Barra de búsqueda en la parte superior

**Ejemplos de Búsqueda**:

- `"Juan"` → Busca en nombre y apellido
- `"3001234567"` → Busca en teléfono
- `"@gmail.com"` → Busca en email

### Ordenamiento

```python
ordering = ["-fecha_registro"]
```

**Comportamiento**:

- Orden por defecto: Más recientes primero
- Columnas clicables para ordenar dinámicamente
- Indicadores visuales de orden actual

---

## Campos de Solo Lectura

### Configuración Base

```python
readonly_fields = [
    "cliente_id",
    "fecha_registro",
    "fecha_creacion",
    "fecha_actualizacion",
]
```

### Configuración Dinámica

```python
def get_readonly_fields(self, request, obj=None):
    if obj:  # Editando un objeto existente
        return self.readonly_fields
    return ["cliente_id", "fecha_creacion", "fecha_actualizacion"]
```

**Lógica**:

- **Creando nuevo cliente**: Solo algunos campos readonly
- **Editando cliente existente**: Más campos readonly
- Previene modificación accidental de datos críticos

---

## Organización con Fieldsets

```python
fieldsets = (
    (
        "Información Personal",
        {"fields": ("nombre", "apellido", "telefono", "email")},
    ),
    (
        "Estado y Notas",
        {"fields": ("activo", "notas")}
    ),
    (
        "Información del Sistema",
        {
            "fields": (
                "cliente_id",
                "fecha_registro",
                "fecha_creacion",
                "fecha_actualizacion",
            ),
            "classes": ("collapse",),
        },
    ),
)
```

### Resultado Visual

**Sección 1: Información Personal** (Siempre visible)

```
┌─ Información Personal ────────────────────┐
│ Nombre: [Juan          ]                  │
│ Apellido: [Pérez       ]                  │
│ Teléfono: [3001234567  ]                  │
│ Email: [juan@email.com ]                  │
└───────────────────────────────────────────┘
```

**Sección 2: Estado y Notas** (Siempre visible)

```
┌─ Estado y Notas ──────────────────────────┐
│ Activo: [✓]                               │
│ Notas: [Cliente frecuente, prefiere       │
│         citas en la mañana               ]│
└───────────────────────────────────────────┘
```

**Sección 3: Información del Sistema** (Colapsible)

```
▼ Información del Sistema
┌───────────────────────────────────────────┐
│ ID Cliente: 1                             │
│ Fecha registro: 15 de enero de 2024       │
│ Fecha creación: 15 de enero de 2024 09:00 │
│ Última actualización: 15 de enero 09:30   │
└───────────────────────────────────────────┘
```

---

## Funcionalidades del Admin

### Acciones en Lote

Django Admin proporciona acciones por defecto:

#### Eliminar en Lote

```python
# Acción por defecto de Django
def delete_selected(modeladmin, request, queryset):
    # Elimina múltiples clientes seleccionados
```

#### Acciones Personalizadas (Extensión Futura)

```python
def activar_clientes(modeladmin, request, queryset):
    """Activar múltiples clientes"""
    count = queryset.update(activo=True)
    modeladmin.message_user(
        request,
        f"{count} clientes activados correctamente."
    )

def desactivar_clientes(modeladmin, request, queryset):
    """Desactivar múltiples clientes"""
    count = queryset.update(activo=False)
    modeladmin.message_user(
        request,
        f"{count} clientes desactivados correctamente."
    )

# Registro de acciones
activar_clientes.short_description = "Activar clientes seleccionados"
desactivar_clientes.short_description = "Desactivar clientes seleccionados"

class ClienteAdmin(admin.ModelAdmin):
    # ... configuración existente ...
    actions = [activar_clientes, desactivar_clientes]
```

### Navegación y Enlaces

#### Breadcrumbs

```
Inicio › Clients › Clientes › Juan Pérez
```

#### Enlaces Relacionados

- Ver en sitio (si está configurado)
- Historial de cambios
- Eliminar objeto

---

## Validaciones en el Admin

### Validaciones del Modelo

El admin utiliza automáticamente las validaciones del modelo:

```python
# Del modelo Cliente
telefono = models.CharField(
    max_length=20,
    validators=[validate_telefono],
    unique=True
)
email = models.EmailField(unique=True)
```

### Manejo de Errores

**Errores de Unicidad**:

```
❌ Cliente con este Email ya existe.
❌ Cliente con este Telefono ya existe.
```

**Errores de Validación**:

```
❌ Introduce una dirección de correo electrónico válida.
❌ Este campo no puede estar en blanco.
```

---

## Permisos y Seguridad

### Permisos por Defecto

Django Admin maneja automáticamente:

| Permiso      | Codename         | Descripción                      |
| ------------ | ---------------- | -------------------------------- |
| **Ver**      | `view_cliente`   | Puede ver la lista y detalles    |
| **Agregar**  | `add_cliente`    | Puede crear nuevos clientes      |
| **Cambiar**  | `change_cliente` | Puede editar clientes existentes |
| **Eliminar** | `delete_cliente` | Puede eliminar clientes          |

### Verificación de Permisos

```python
# En las vistas del admin
def has_view_permission(self, request, obj=None):
    return request.user.has_perm('clients.view_cliente')

def has_change_permission(self, request, obj=None):
    return request.user.has_perm('clients.change_cliente')
```

### Configuración de Permisos Personalizada

```python
class ClienteAdmin(admin.ModelAdmin):
    # ... configuración existente ...

    def has_delete_permission(self, request, obj=None):
        # Solo superusuarios pueden eliminar clientes
        return request.user.is_superuser

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Usuarios normales solo ven clientes activos
        return qs.filter(activo=True)
```

---

## Personalización Visual

### CSS Personalizado

```python
class ClienteAdmin(admin.ModelAdmin):
    # ... configuración existente ...

    class Media:
        css = {
            'all': ('admin/css/cliente_admin.css',)
        }
        js = ('admin/js/cliente_admin.js',)
```

### Templates Personalizados

```python
class ClienteAdmin(admin.ModelAdmin):
    # Template personalizado para el formulario de cambio
    change_form_template = 'admin/clients/cliente/change_form.html'

    # Template personalizado para la lista
    change_list_template = 'admin/clients/cliente/change_list.html'
```

---

## Optimización de Performance

### Optimización de Queries

```python
class ClienteAdmin(admin.ModelAdmin):
    # ... configuración existente ...

    def get_queryset(self, request):
        return super().get_queryset(request).select_related().prefetch_related()

    # Optimizar búsquedas
    search_fields = [
        "nombre", "apellido",
        "telefono", "email"
    ]

    # Limitar resultados por página
    list_per_page = 25
    list_max_show_all = 100
```

### Caché de Consultas

```python
from django.core.cache import cache

class ClienteAdmin(admin.ModelAdmin):
    # ... configuración existente ...

    def changelist_view(self, request, extra_context=None):
        # Implementar caché para vistas pesadas
        cache_key = f"admin_clientes_stats_{request.user.pk}"
        stats = cache.get(cache_key)

        if not stats:
            stats = {
                'total': Cliente.objects.count(),
                'activos': Cliente.objects.filter(activo=True).count(),
            }
            cache.set(cache_key, stats, 300)  # 5 minutos

        extra_context = extra_context or {}
        extra_context['stats'] = stats

        return super().changelist_view(request, extra_context)
```

---

## Casos de Uso Comunes

### 1. Búsqueda Rápida de Cliente

**Escenario**: Recepcionista busca cliente por teléfono

**Pasos**:

1. Acceder a Admin → Clients → Clientes
2. Usar barra de búsqueda: `"3001234567"`
3. Resultado inmediato con información del cliente

### 2. Actualización Masiva de Estado

**Escenario**: Desactivar clientes inactivos

**Pasos**:

1. Filtrar por fecha de registro antigua
2. Seleccionar múltiples clientes
3. Aplicar acción "Desactivar clientes seleccionados"

### 3. Revisión de Información

**Escenario**: Verificar datos de cliente antes de cita

**Pasos**:

1. Buscar cliente por nombre
2. Revisar información en fieldsets organizados
3. Actualizar notas si es necesario

---

## Integración con el Sistema

### Logs de Auditoría

Django Admin registra automáticamente:

```python
# Tabla: django_admin_log
# Registra todas las acciones de admin:
# - Qué usuario hizo el cambio
# - Qué objeto fue modificado
# - Qué tipo de acción (agregar/cambiar/eliminar)
# - Cuándo se hizo el cambio
```

### Notificaciones

```python
from django.contrib import messages

class ClienteAdmin(admin.ModelAdmin):
    # ... configuración existente ...

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if change:
            messages.success(
                request,
                f"Cliente {obj.nombre_completo} actualizado correctamente."
            )
        else:
            messages.success(
                request,
                f"Cliente {obj.nombre_completo} creado correctamente."
            )
```

---

## Configuración de Acceso

### URLs del Admin

```python
# En nail_salon_api/urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    # ... otras URLs
]
```

**URLs Resultantes**:

```
http://localhost:8000/admin/                     # Panel principal
http://localhost:8000/admin/clients/             # App clients
http://localhost:8000/admin/clients/cliente/     # Lista de clientes
http://localhost:8000/admin/clients/cliente/1/   # Editar cliente ID 1
http://localhost:8000/admin/clients/cliente/add/ # Agregar cliente
```

### Configuración del Site

```python
# En apps/clients/apps.py o en settings
from django.contrib import admin

admin.site.site_header = "Nail Salon - Administración"
admin.site.site_title = "Nail Salon Admin"
admin.site.index_title = "Panel de Administración"
```

---

## Mejores Prácticas

### 1. Organización Visual

- Usar fieldsets para agrupar campos relacionados
- Colapsar información técnica por defecto
- Mostrar solo campos relevantes en list_display

### 2. Performance

- Configurar list_per_page apropiadamente
- Optimizar search_fields
- Implementar select_related para relaciones

### 3. Seguridad

- Configurar permisos granulares
- Validar datos en modelo y admin
- Registrar acciones importantes

### 4. Usabilidad

- Proporcionar filtros útiles
- Configurar ordenamiento intuitivo
- Incluir campos de búsqueda relevantes

---

## Extensiones Futuras

### 1. Acciones Personalizadas

```python
def exportar_clientes_excel(modeladmin, request, queryset):
    """Exportar clientes seleccionados a Excel"""
    # Implementación de exportación
    pass

def enviar_notificacion_email(modeladmin, request, queryset):
    """Enviar notificación por email a clientes"""
    # Implementación de notificaciones
    pass
```

### 2. Widgets Personalizados

```python
from django import forms

class ClienteAdminForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = '__all__'
        widgets = {
            'notas': forms.Textarea(attrs={'rows': 4, 'cols': 80}),
            'telefono': forms.TextInput(attrs={'placeholder': '3001234567'}),
        }

class ClienteAdmin(admin.ModelAdmin):
    form = ClienteAdminForm
    # ... resto de configuración
```

### 3. Inline de Modelos Relacionados

```python
# Para cuando existan relaciones con otros modelos
class CitaInline(admin.TabularInline):
    model = Cita
    extra = 0
    readonly_fields = ['fecha_cita', 'estado']

class ClienteAdmin(admin.ModelAdmin):
    # ... configuración existente ...
    inlines = [CitaInline]
```
