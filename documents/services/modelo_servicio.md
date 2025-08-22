# Documentación del Modelo Servicio

## Visión General

El modelo `Servicio` es la entidad principal de la aplicación services y representa la información de los servicios ofrecidos por el salón de uñas. Este modelo almacena todos los datos necesarios para la gestión de servicios, incluyendo precios, descripciones, duración estimada y categorización.

## Definición del Modelo

**Archivo**: `apps/services/models/servicio.py`

```python
class Servicio(models.Model):
    servicio_id = models.AutoField(primary_key=True)
    nombre_servicio = models.CharField(max_length=200)
    precio = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[validate_precio_positivo]
    )
    descripcion = models.TextField(blank=True, null=True)
    duracion_estimada = models.DurationField(
        validators=[validate_duracion_positiva], blank=True, null=True
    )
    activo = models.BooleanField(default=True)
    categoria = models.CharField(max_length=100, blank=True)
    imagen = models.ImageField(upload_to="servicios/", blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
```

## Campos del Modelo

### Campos Principales

| Campo               | Tipo          | Descripción                    | Restricciones                           |
| ------------------- | ------------- | ------------------------------ | --------------------------------------- |
| `servicio_id`       | AutoField     | Identificador único (PK)       | Primary Key, Auto-incrementable         |
| `nombre_servicio`   | CharField     | Nombre del servicio            | Máximo 200 caracteres, requerido        |
| `precio`            | DecimalField  | Precio del servicio            | 10 dígitos, 2 decimales, > 0, requerido |
| `descripcion`       | TextField     | Descripción del servicio       | Opcional, puede ser nulo                |
| `duracion_estimada` | DurationField | Duración estimada del servicio | Opcional, debe ser > 0 si se especifica |

### Campos de Clasificación

| Campo       | Tipo         | Descripción            | Restricciones                    |
| ----------- | ------------ | ---------------------- | -------------------------------- |
| `activo`    | BooleanField | Estado del servicio    | Por defecto True                 |
| `categoria` | CharField    | Categoría del servicio | Máximo 100 caracteres, opcional  |
| `imagen`    | ImageField   | Imagen del servicio    | Opcional, upload_to="servicios/" |

### Campos de Gestión

| Campo                 | Tipo          | Descripción                    | Restricciones          |
| --------------------- | ------------- | ------------------------------ | ---------------------- |
| `fecha_creacion`      | DateTimeField | Timestamp de creación          | Auto-asignado al crear |
| `fecha_actualizacion` | DateTimeField | Timestamp última actualización | Auto-actualizado       |

## Validaciones

### Validación de Precio

El campo precio utiliza el validador personalizado `validate_precio_positivo` (definido en `utils.validators`):

```python
def validate_precio_positivo(value):
    if value <= 0:
        raise ValidationError("El precio debe ser mayor que cero.")
```

**Características**:

- Precio debe ser mayor a 0
- Acepta hasta 2 decimales
- Máximo 10 dígitos totales (incluyendo decimales)
- Campo obligatorio

### Validación de Duración

El campo duracion_estimada utiliza el validador personalizado `validate_duracion_positiva`:

```python
def validate_duracion_positiva(value):
    if value and value.total_seconds() <= 0:
        raise ValidationError("La duración debe ser mayor que cero.")
```

**Características**:

- Si se especifica, debe ser mayor a 0
- Acepta formato timedelta (HH:MM:SS)
- Campo opcional (puede ser None)

## Meta Configuración

```python
class Meta:
    app_label = "services"
    db_table = "servicios"
    verbose_name = "Servicio"
    verbose_name_plural = "Servicios"
    ordering = ["nombre_servicio"]
```

### Explicación de Meta

- **app_label**: Identifica la aplicación para Django
- **db_table**: Nombre de la tabla en la base de datos
- **verbose_name**: Nombre legible singular
- **verbose_name_plural**: Nombre legible plural
- **ordering**: Ordenamiento por defecto (alfabético por nombre)

## Métodos del Modelo

### `__str__(self)`

```python
def __str__(self):
    return self.nombre_servicio
```

Representación en cadena del objeto, muestra el nombre del servicio.

### `id` (Property)

```python
@property
def id(self):
    """Alias para servicio_id para compatibilidad con tests y API estándar"""
    return self.servicio_id
```

Propiedad que proporciona un alias para `servicio_id`, facilitando la compatibilidad con estándares REST que esperan un campo `id`.

### `duracion_en_minutos` (Property)

```python
@property
def duracion_en_minutos(self):
    """Retorna la duración en minutos"""
    if self.duracion_estimada:
        return int(self.duracion_estimada.total_seconds() / 60)
    return 0
```

Propiedad que convierte la duración de timedelta a minutos enteros.

### `get_precio_formateado(self)`

```python
def get_precio_formateado(self):
    """Retorna el precio formateado como string"""
    return f"${self.precio:,.0f}"
```

Método que formatea el precio con símbolo de moneda y separadores de miles.

**Ejemplo**: `25000` → `"$25,000"`

## Relaciones

### Relaciones Actuales

Actualmente el modelo Servicio no tiene relaciones explícitas definidas.

### Relaciones Futuras (Implícitas)

1. **Con DetalleCita**: Un servicio puede ser usado en múltiples detalles de citas

   - Relación: OneToMany (Servicio -> DetalleCita)
   - Campo esperado en DetalleCita: `servicio = ForeignKey(Servicio)`

2. **Con HistorialServicios**: Un servicio puede tener múltiples registros de historial

   - Relación: OneToMany (Servicio -> HistorialServicios)

3. **Con Categorias**: Futura normalización de categorías
   - Relación: ForeignKey (Servicio -> Categoria)

## Índices de Base de Datos

### Índices Implícitos

- `servicio_id`: Índice de clave primaria
- `nombre_servicio`: Índice para ordenamiento por defecto

### Índices Recomendados

Para optimización de consultas frecuentes:

```sql
-- Búsquedas por categoría
CREATE INDEX idx_servicio_categoria ON servicios(categoria);

-- Filtros por estado y precio
CREATE INDEX idx_servicio_activo_precio ON servicios(activo, precio);

-- Búsquedas por estado activo
CREATE INDEX idx_servicio_activo ON servicios(activo);

-- Búsquedas por rango de precios
CREATE INDEX idx_servicio_precio ON servicios(precio);
```

## Queries Comunes

### Servicios Activos

```python
servicios_activos = Servicio.objects.filter(activo=True)
```

### Búsqueda por Nombre

```python
servicios = Servicio.objects.filter(nombre_servicio__icontains="Manicure")
```

### Servicios por Categoría

```python
servicios_manicure = Servicio.objects.filter(categoria="Manicure")
```

### Servicios por Rango de Precio

```python
servicios_premium = Servicio.objects.filter(precio__gte=50000)
servicios_economicos = Servicio.objects.filter(precio__lt=30000)
```

### Servicios con Duración Específica

```python
from datetime import timedelta

servicios_rapidos = Servicio.objects.filter(
    duracion_estimada__lte=timedelta(minutes=60)
)
```

### Servicios Ordenados por Precio

```python
servicios_baratos = Servicio.objects.order_by('precio')
servicios_caros = Servicio.objects.order_by('-precio')
```

## Consideraciones de Seguridad

### Datos Sensibles

- **Precio**: Información comercial que puede requerir permisos especiales para modificar
- **Imagen**: Archivos subidos que requieren validación

### Recomendaciones

1. **Validación de Imágenes**: Validar tipo y tamaño de archivos
2. **Permisos de Precio**: Controlar quién puede modificar precios
3. **Auditoría**: Los campos de fecha permiten tracking de cambios
4. **Backup**: Información crítica del negocio

## Migraciones

### Migración Inicial

La primera migración crea la tabla con todos los campos definidos:

```bash
python manage.py makemigrations services
python manage.py migrate services
```

### Migraciones Aplicadas

1. **0001_initial.py**: Creación inicial del modelo
2. **0002_alter_servicio_descripcion.py**: Descripción opcional
3. **0003_alter_servicio_duracion_estimada.py**: Duración opcional

### Migración para Campos Opcionales

```python
# 0002_alter_servicio_descripcion.py
operations = [
    migrations.AlterField(
        model_name='servicio',
        name='descripcion',
        field=models.TextField(blank=True, null=True),
    ),
]

# 0003_alter_servicio_duracion_estimada.py
operations = [
    migrations.AlterField(
        model_name='servicio',
        name='duracion_estimada',
        field=models.DurationField(blank=True, null=True, validators=[validate_duracion_positiva]),
    ),
]
```

## Performance

### Optimizaciones Aplicadas

1. **Índice en clave primaria** para acceso rápido por ID
2. **Ordenamiento por defecto** optimizado por nombre
3. **Campo activo** para soft filtering
4. **Propiedades calculadas** para formateo

### Consideraciones de Escala

- Para catálogos grandes, considerar paginación
- Caché de servicios más consultados
- Índices compuestos para filtros complejos
- Optimización de consultas con `select_related` cuando se agreguen relaciones

## Casos de Uso

### Registro de Nuevo Servicio

```python
servicio = Servicio.objects.create(
    nombre_servicio="Manicure Francesa",
    precio=35000,
    descripcion="Manicure clásica con diseño francés",
    duracion_estimada=timedelta(hours=1, minutes=30),
    categoria="Manicure",
    activo=True
)
```

### Actualización de Precio

```python
servicio = Servicio.objects.get(servicio_id=1)
servicio.precio = 40000
servicio.save()
```

### Desactivación de Servicio

```python
servicio = Servicio.objects.get(servicio_id=1)
servicio.activo = False
servicio.save()
```

### Búsqueda Avanzada

```python
# Servicios activos de manicure con precio menor a $40,000
servicios = Servicio.objects.filter(
    activo=True,
    categoria__icontains="Manicure",
    precio__lt=40000
).order_by('precio')
```

### Cálculo de Estadísticas

```python
from django.db.models import Avg, Min, Max, Count

stats = Servicio.objects.filter(activo=True).aggregate(
    precio_promedio=Avg('precio'),
    precio_minimo=Min('precio'),
    precio_maximo=Max('precio'),
    total_servicios=Count('servicio_id')
)
```

## Datos de Ejemplo

### Servicios de Manicure

```python
manicure_basico = Servicio.objects.create(
    nombre_servicio="Manicure Básico",
    precio=25000,
    descripcion="Limado, cutículas y esmaltado básico",
    duracion_estimada=timedelta(minutes=60),
    categoria="Manicure"
)

manicure_francesa = Servicio.objects.create(
    nombre_servicio="Manicure Francesa",
    precio=35000,
    descripcion="Manicure con diseño francés clásico",
    duracion_estimada=timedelta(minutes=90),
    categoria="Manicure"
)
```

### Servicios de Pedicure

```python
pedicure_completo = Servicio.objects.create(
    nombre_servicio="Pedicure Completo",
    precio=40000,
    descripcion="Pedicure con tratamiento completo y masaje",
    duracion_estimada=timedelta(hours=2),
    categoria="Pedicure"
)
```
