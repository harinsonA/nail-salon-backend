# Documentación del Modelo Cliente

## Visión General

El modelo `Cliente` es la entidad principal de la aplicación clients y representa la información de los clientes del salón de uñas. Este modelo almacena todos los datos personales y de contacto necesarios para la gestión de clientes.

## Definición del Modelo

**Archivo**: `apps/clients/models/cliente.py`

```python
class Cliente(models.Model):
    cliente_id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, validators=[validate_telefono], unique=True)
    email = models.EmailField(unique=True)
    fecha_registro = models.DateField(auto_now_add=True)

    # Campos adicionales para gestión
    activo = models.BooleanField(default=True)
    notas = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
```

## Campos del Modelo

### Campos Principales

| Campo            | Tipo       | Descripción              | Restricciones                         |
| ---------------- | ---------- | ------------------------ | ------------------------------------- |
| `cliente_id`     | AutoField  | Identificador único (PK) | Primary Key, Auto-incrementable       |
| `nombre`         | CharField  | Nombre del cliente       | Máximo 100 caracteres, requerido      |
| `apellido`       | CharField  | Apellido del cliente     | Máximo 100 caracteres, requerido      |
| `telefono`       | CharField  | Número de teléfono       | Máximo 20 caracteres, único, validado |
| `email`          | EmailField | Correo electrónico       | Formato email válido, único           |
| `fecha_registro` | DateField  | Fecha de registro        | Auto-asignado al crear                |

### Campos de Gestión

| Campo                 | Tipo          | Descripción                    | Restricciones            |
| --------------------- | ------------- | ------------------------------ | ------------------------ |
| `activo`              | BooleanField  | Estado del cliente             | Por defecto True         |
| `notas`               | TextField     | Notas adicionales              | Opcional, puede ser nulo |
| `fecha_creacion`      | DateTimeField | Timestamp de creación          | Auto-asignado al crear   |
| `fecha_actualizacion` | DateTimeField | Timestamp última actualización | Auto-actualizado         |

## Validaciones

### Validación de Teléfono

El campo teléfono utiliza el validador personalizado `validate_telefono` (definido en `utils.validators`):

- Permite números, espacios, guiones y el símbolo +
- Formato flexible para diferentes tipos de números
- Garantiza unicidad en el sistema

### Validación de Email

- Utiliza la validación nativa de Django para formato de email
- Garantiza unicidad en el sistema
- No permite emails duplicados

## Meta Configuración

```python
class Meta:
    app_label = "clients"
    db_table = "clientes"
    verbose_name = "Cliente"
    verbose_name_plural = "Clientes"
    ordering = ["-fecha_registro"]
```

### Explicación de Meta

- **app_label**: Identifica la aplicación para Django
- **db_table**: Nombre de la tabla en la base de datos
- **verbose_name**: Nombre legible singular
- **verbose_name_plural**: Nombre legible plural
- **ordering**: Ordenamiento por defecto (más recientes primero)

## Métodos del Modelo

### `__str__(self)`

```python
def __str__(self):
    return f"{self.nombre} {self.apellido}"
```

Representación en cadena del objeto, muestra nombre completo.

### `nombre_completo` (Property)

```python
@property
def nombre_completo(self):
    return f"{self.nombre} {self.apellido}"
```

Propiedad que retorna el nombre completo del cliente.

### `get_citas_activas(self)`

```python
def get_citas_activas(self):
    """Retorna las citas no canceladas del cliente"""
    return self.citas.exclude(estado_cita="CANCELADA")
```

Método que retorna las citas activas del cliente (relación inversa con el modelo Citas).

## Relaciones

### Relaciones Actuales

Actualmente el modelo Cliente no tiene relaciones explícitas definidas, pero está preparado para:

### Relaciones Futuras (Implícitas)

1. **Con Citas**: Un cliente puede tener múltiples citas

   - Relación: OneToMany (Cliente -> Citas)
   - Campo esperado en Citas: `cliente = ForeignKey(Cliente)`

2. **Con Historial de Servicios**: Un cliente puede tener múltiples servicios

   - Relación: OneToMany (Cliente -> HistorialServicios)

3. **Con Pagos**: Un cliente puede tener múltiples pagos
   - Relación: OneToMany (Cliente -> Pagos)

## Índices de Base de Datos

### Índices Implícitos

- `cliente_id`: Índice de clave primaria
- `telefono`: Índice único
- `email`: Índice único

### Índices Recomendados

Para optimización de consultas frecuentes:

```sql
-- Búsquedas por nombre y apellido
CREATE INDEX idx_cliente_nombre_apellido ON clientes(nombre, apellido);

-- Filtros por estado y fecha
CREATE INDEX idx_cliente_activo_fecha ON clientes(activo, fecha_registro);

-- Búsquedas por fecha de registro
CREATE INDEX idx_cliente_fecha_registro ON clientes(fecha_registro);
```

## Queries Comunes

### Clientes Activos

```python
clientes_activos = Cliente.objects.filter(activo=True)
```

### Búsqueda por Nombre

```python
clientes = Cliente.objects.filter(
    nombre__icontains="Juan",
    apellido__icontains="Pérez"
)
```

### Clientes Registrados Hoy

```python
from django.utils import timezone

hoy = timezone.now().date()
clientes_hoy = Cliente.objects.filter(fecha_registro=hoy)
```

### Clientes con Email Específico

```python
try:
    cliente = Cliente.objects.get(email="cliente@example.com")
except Cliente.DoesNotExist:
    cliente = None
```

## Consideraciones de Seguridad

### Datos Sensibles

- **Email**: Información de contacto sensible
- **Teléfono**: Información personal que requiere protección
- **Notas**: Pueden contener información confidencial

### Recomendaciones

1. **Encriptación**: Considerar encriptar campos sensibles
2. **Logs de Auditoría**: Registrar cambios importantes
3. **Permisos**: Implementar control de acceso granular
4. **GDPR/Protección de Datos**: Implementar derecho al olvido

## Migraciones

### Migración Inicial

La primera migración crea la tabla con todos los campos definidos:

```bash
python manage.py makemigrations clients
python manage.py migrate clients
```

### Cambios Futuros

Para modificar el modelo:

1. Actualizar el código del modelo
2. Generar migración: `python manage.py makemigrations clients`
3. Aplicar migración: `python manage.py migrate clients`

## Performance

### Optimizaciones Aplicadas

1. **Índices únicos** en email y teléfono para búsquedas rápidas
2. **Ordenamiento por defecto** optimizado
3. **Campo activo** para soft delete (mejor que eliminar físicamente)

### Consideraciones de Escala

- Para grandes volúmenes de datos, considerar particionado por fecha
- Implementar archivado de clientes inactivos antiguos
- Optimizar consultas con `select_related` y `prefetch_related` cuando sea necesario

## Casos de Uso

### Registro de Nuevo Cliente

```python
cliente = Cliente.objects.create(
    nombre="Juan",
    apellido="Pérez",
    telefono="3001234567",
    email="juan.perez@email.com",
    notas="Cliente referido por María"
)
```

### Actualización de Información

```python
cliente = Cliente.objects.get(cliente_id=1)
cliente.telefono = "3009876543"
cliente.notas = "Actualizado teléfono"
cliente.save()
```

### Desactivación de Cliente

```python
cliente = Cliente.objects.get(cliente_id=1)
cliente.activo = False
cliente.save()
```

### Búsqueda Avanzada

```python
# Clientes activos con nombre que contenga "Ana"
clientes = Cliente.objects.filter(
    activo=True,
    nombre__icontains="Ana"
).order_by('apellido')
```
