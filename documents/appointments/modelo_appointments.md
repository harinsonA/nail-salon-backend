# Documentación de los Modelos de Appointments

## Visión General

La aplicación `appointments` contiene dos modelos principales: `Cita` y `DetalleCita`. Estos modelos trabajan en conjunto para gestionar todo el sistema de citas del salón de uñas, incluyendo la información de la cita y los servicios asociados a cada una.

## Modelo Cita

### Definición del Modelo

**Archivo**: `apps/appointments/models/cita.py`

```python
class Cita(models.Model):
    ESTADOS_CITA = [
        ('PENDIENTE', 'Pendiente'),
        ('CONFIRMADA', 'Confirmada'),
        ('COMPLETADA', 'Completada'),
        ('CANCELADA', 'Cancelada'),
    ]

    cita_id = models.AutoField(primary_key=True)
    cliente = models.ForeignKey('clients.Cliente', on_delete=models.CASCADE, related_name='citas')
    fecha_hora_cita = models.DateTimeField()
    estado_cita = models.CharField(max_length=20, choices=ESTADOS_CITA, default='PENDIENTE')
    observaciones = models.TextField(blank=True, null=True)

    # Campos de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
```

### Campos del Modelo Cita

#### Campos Principales

| Campo             | Tipo          | Descripción                  | Restricciones                        |
| ----------------- | ------------- | ---------------------------- | ------------------------------------ |
| `cita_id`         | AutoField     | Identificador único (PK)     | Primary Key, Auto-incrementable      |
| `cliente`         | ForeignKey    | Cliente asociado a la cita   | Requerido, relación con Cliente      |
| `fecha_hora_cita` | DateTimeField | Fecha y hora programada      | Requerido                            |
| `estado_cita`     | CharField     | Estado actual de la cita     | Choices definidos, default PENDIENTE |
| `observaciones`   | TextField     | Notas adicionales de la cita | Opcional, puede ser nulo             |

#### Campos de Auditoría

| Campo                 | Tipo          | Descripción                    | Restricciones               |
| --------------------- | ------------- | ------------------------------ | --------------------------- |
| `fecha_creacion`      | DateTimeField | Timestamp de creación          | Auto-asignado al crear      |
| `fecha_actualizacion` | DateTimeField | Timestamp última actualización | Auto-actualizado            |
| `creado_por`          | ForeignKey    | Usuario que creó la cita       | Opcional, relación con User |

### Estados de Cita

| Estado       | Descripción                             | Transiciones Permitidas       |
| ------------ | --------------------------------------- | ----------------------------- |
| `PENDIENTE`  | Estado inicial al crear la cita         | → CONFIRMADA, CANCELADA       |
| `CONFIRMADA` | Cita confirmada, lista para el servicio | → COMPLETADA, CANCELADA       |
| `COMPLETADA` | Servicio realizado exitosamente         | Estado final (no hay cambios) |
| `CANCELADA`  | Cita cancelada por cualquier motivo     | Estado final (no hay cambios) |

### Propiedades Calculadas

```python
@property
def monto_total(self):
    """Calcula el monto total de todos los servicios de la cita."""
    return self.detalles.aggregate(
        total=Sum(F('precio_acordado') * F('cantidad_servicios') * (1 - F('descuento') / 100))
    )['total'] or 0

@property
def duracion_total(self):
    """Calcula la duración total estimada de todos los servicios."""
    total_minutos = self.detalles.aggregate(
        total=Sum(F('servicio__duracion_estimada') * F('cantidad_servicios'))
    )['total'] or timedelta(0)
    return total_minutos.total_seconds() / 60

@property
def puede_ser_modificada(self):
    """Determina si la cita puede ser modificada según su estado."""
    return self.estado_cita in ['PENDIENTE', 'CONFIRMADA']

@property
def nombre_completo_cliente(self):
    """Retorna el nombre completo del cliente."""
    return f"{self.cliente.nombre} {self.cliente.apellido}"
```

### Métodos del Modelo

```python
def confirmar(self):
    """Confirma una cita pendiente."""
    if self.estado_cita == 'PENDIENTE':
        self.estado_cita = 'CONFIRMADA'
        self.save()

def cancelar(self, motivo=None):
    """Cancela una cita con motivo opcional."""
    if self.estado_cita in ['PENDIENTE', 'CONFIRMADA']:
        self.estado_cita = 'CANCELADA'
        if motivo:
            self.observaciones = f"{self.observaciones or ''}\n[CANCELADA] {motivo}".strip()
        self.save()

def completar(self, observaciones_finales=None):
    """Marca una cita como completada."""
    if self.estado_cita == 'CONFIRMADA':
        self.estado_cita = 'COMPLETADA'
        if observaciones_finales:
            self.observaciones = f"{self.observaciones or ''}\n[COMPLETADA] {observaciones_finales}".strip()
        self.save()
```

## Modelo DetalleCita

### Definición del Modelo

**Archivo**: `apps/appointments/models/detalle_cita.py`

```python
class DetalleCita(models.Model):
    detalle_cita_id = models.AutoField(primary_key=True)
    cita = models.ForeignKey(Cita, on_delete=models.CASCADE, related_name='detalles')
    servicio = models.ForeignKey('services.Servicio', on_delete=models.CASCADE)
    precio_acordado = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_servicios = models.PositiveIntegerField(default=1)
    descuento = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    notas_detalle = models.TextField(blank=True, null=True)

    # Campo de auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
```

### Campos del Modelo DetalleCita

#### Campos Principales

| Campo                | Tipo                 | Descripción                      | Restricciones                      |
| -------------------- | -------------------- | -------------------------------- | ---------------------------------- |
| `detalle_cita_id`    | AutoField            | Identificador único (PK)         | Primary Key, Auto-incrementable    |
| `cita`               | ForeignKey           | Cita asociada al detalle         | Requerido, relación con Cita       |
| `servicio`           | ForeignKey           | Servicio a realizar              | Requerido, relación con Servicio   |
| `precio_acordado`    | DecimalField         | Precio acordado para el servicio | 10 dígitos, 2 decimales, requerido |
| `cantidad_servicios` | PositiveIntegerField | Cantidad de veces que se realiza | Entero positivo, default 1         |
| `descuento`          | DecimalField         | Descuento aplicado (porcentaje)  | 0-100%, default 0                  |
| `notas_detalle`      | TextField            | Notas específicas del servicio   | Opcional, puede ser nulo           |

#### Campos de Auditoría

| Campo            | Tipo          | Descripción           | Restricciones          |
| ---------------- | ------------- | --------------------- | ---------------------- |
| `fecha_creacion` | DateTimeField | Timestamp de creación | Auto-asignado al crear |

### Propiedades Calculadas

```python
@property
def subtotal(self):
    """Calcula el subtotal del detalle (precio * cantidad con descuento)."""
    precio_base = self.precio_acordado * self.cantidad_servicios
    descuento_aplicado = precio_base * (self.descuento / 100)
    return precio_base - descuento_aplicado

@property
def precio_unitario_con_descuento(self):
    """Calcula el precio unitario después de aplicar el descuento."""
    return self.precio_acordado * (1 - self.descuento / 100)

@property
def nombre_servicio(self):
    """Retorna el nombre del servicio asociado."""
    return self.servicio.nombre_servicio

@property
def duracion_estimada_total(self):
    """Calcula la duración total estimada para este detalle."""
    return self.servicio.duracion_estimada * self.cantidad_servicios
```

### Validaciones

```python
def clean(self):
    """Validaciones personalizadas del modelo."""
    if self.cantidad_servicios <= 0:
        raise ValidationError("La cantidad de servicios debe ser mayor a 0.")

    if self.descuento < 0 or self.descuento > 100:
        raise ValidationError("El descuento debe estar entre 0 y 100%.")

    if self.precio_acordado <= 0:
        raise ValidationError("El precio acordado debe ser mayor a 0.")
```

## Relaciones entre Modelos

### Diagrama de Relaciones

```
Cliente (clients.Cliente)
    ↓ (1:N)
Cita (appointments.Cita)
    ↓ (1:N)
DetalleCita (appointments.DetalleCita)
    ↓ (N:1)
Servicio (services.Servicio)
```

### Descripciones de Relaciones

1. **Cliente → Cita**: Un cliente puede tener múltiples citas (`related_name='citas'`)
2. **Cita → DetalleCita**: Una cita puede tener múltiples detalles de servicios (`related_name='detalles'`)
3. **Servicio → DetalleCita**: Un servicio puede estar en múltiples detalles de citas
4. **Usuario → Cita**: Un usuario puede crear múltiples citas (auditoría)

## Constraints y Validaciones

### A Nivel de Base de Datos

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=['cita', 'servicio'],
            name='unique_cita_servicio'
        ),
        models.CheckConstraint(
            check=models.Q(cantidad_servicios__gt=0),
            name='cantidad_servicios_positive'
        ),
        models.CheckConstraint(
            check=models.Q(precio_acordado__gt=0),
            name='precio_acordado_positive'
        ),
    ]
```

### Validaciones Personalizadas

1. **Fecha de Cita**: No puede ser en el pasado
2. **Cliente Activo**: Solo se pueden crear citas para clientes activos
3. **Estado de Cita**: Solo transiciones válidas permitidas
4. **Servicios Únicos**: No se puede agregar el mismo servicio dos veces a una cita
5. **Modificaciones**: Solo citas PENDIENTES y CONFIRMADAS pueden modificarse

## Señales (Signals)

```python
@receiver(post_save, sender=DetalleCita)
def actualizar_monto_cita(sender, instance, **kwargs):
    """Actualiza el monto total de la cita cuando se modifica un detalle."""
    instance.cita.save()  # Esto triggerea el recálculo de propiedades

@receiver(post_delete, sender=DetalleCita)
def actualizar_monto_cita_delete(sender, instance, **kwargs):
    """Actualiza el monto total cuando se elimina un detalle."""
    if instance.cita_id:  # Verificar que la cita aún existe
        instance.cita.save()
```

## Índices de Base de Datos

Para optimizar las consultas más comunes:

```python
class Meta:
    indexes = [
        models.Index(fields=['fecha_hora_cita']),
        models.Index(fields=['estado_cita']),
        models.Index(fields=['cliente', 'fecha_hora_cita']),
        models.Index(fields=['fecha_creacion']),
    ]
```

## Uso en QuerySets

### Consultas Comunes

```python
# Citas de hoy
hoy = timezone.now().date()
citas_hoy = Cita.objects.filter(fecha_hora_cita__date=hoy)

# Citas con monto total calculado
citas_con_monto = Cita.objects.prefetch_related('detalles__servicio')

# Citas pendientes de un cliente
citas_pendientes = Cita.objects.filter(
    cliente_id=cliente_id,
    estado_cita='PENDIENTE'
)

# Detalles con información completa
detalles_completos = DetalleCita.objects.select_related(
    'cita__cliente', 'servicio'
)
```
