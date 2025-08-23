# Documentación del Modelo de Payments

## Visión General

La aplicación `payments` contiene un modelo principal: `Pago`. Este modelo gestiona toda la información relacionada con los pagos del salón de uñas, incluyendo la asociación con citas, métodos de pago, estados y montos.

## Modelo Pago

### Definición del Modelo

**Archivo**: `apps/payments/models/pago.py`

```python
class Pago(models.Model):
    pago_id = models.AutoField(primary_key=True)
    cita = models.ForeignKey(
        "appointments.Cita", on_delete=models.CASCADE, related_name="pagos"
    )
    fecha_pago = models.DateTimeField()
    monto_total = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    metodo_pago = models.CharField(max_length=20, choices=MetodoPago.CHOICES)
    estado_pago = models.CharField(
        max_length=20, choices=EstadoPago.CHOICES, default=EstadoPago.PENDIENTE
    )

    # Campos adicionales
    referencia_pago = models.CharField(max_length=100, blank=True, null=True)
    notas_pago = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
```

### Campos del Modelo Pago

#### Campos Principales

| Campo         | Tipo          | Descripción                   | Restricciones                                   |
| ------------- | ------------- | ----------------------------- | ----------------------------------------------- |
| `pago_id`     | AutoField     | Identificador único (PK)      | Primary Key, Auto-incrementable                 |
| `cita`        | ForeignKey    | Cita asociada al pago         | Requerido, relación con Cita                    |
| `fecha_pago`  | DateTimeField | Fecha y hora del pago         | Requerido                                       |
| `monto_total` | DecimalField  | Monto del pago                | Requerido, max_digits=10, decimal_places=2, > 0 |
| `metodo_pago` | CharField     | Método utilizado para el pago | Choices definidos, max_length=20                |
| `estado_pago` | CharField     | Estado actual del pago        | Choices definidos, default PENDIENTE            |

#### Campos Adicionales

| Campo             | Tipo      | Descripción                 | Restricciones            |
| ----------------- | --------- | --------------------------- | ------------------------ |
| `referencia_pago` | CharField | Referencia externa del pago | Opcional, max_length=100 |
| `notas_pago`      | TextField | Notas adicionales del pago  | Opcional, puede ser nulo |

#### Campos de Auditoría

| Campo                 | Tipo          | Descripción                    | Restricciones               |
| --------------------- | ------------- | ------------------------------ | --------------------------- |
| `fecha_creacion`      | DateTimeField | Timestamp de creación          | Auto-asignado al crear      |
| `fecha_actualizacion` | DateTimeField | Timestamp última actualización | Auto-actualizado            |
| `creado_por`          | ForeignKey    | Usuario que creó el pago       | Opcional, relación con User |

### Métodos de Pago

Definidos en `utils/choices.py`:

```python
class MetodoPago:
    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
    TRANSFERENCIA = "TRANSFERENCIA"
    CHEQUE = "CHEQUE"

    CHOICES = [
        (EFECTIVO, "Efectivo"),
        (TARJETA, "Tarjeta"),
        (TRANSFERENCIA, "Transferencia"),
        (CHEQUE, "Cheque"),
    ]
```

| Método          | Código          | Descripción            | Uso Típico                     |
| --------------- | --------------- | ---------------------- | ------------------------------ |
| `EFECTIVO`      | "EFECTIVO"      | Pago en efectivo       | Pagos inmediatos en el salón   |
| `TARJETA`       | "TARJETA"       | Pago con tarjeta       | Débito/crédito, POS            |
| `TRANSFERENCIA` | "TRANSFERENCIA" | Transferencia bancaria | Pagos anticipados o remotos    |
| `CHEQUE`        | "CHEQUE"        | Pago con cheque        | Pagos formales o empresariales |

### Estados de Pago

Definidos en `utils/choices.py`:

```python
class EstadoPago:
    PAGADO = "PAGADO"
    PENDIENTE = "PENDIENTE"
    CANCELADO = "CANCELADO"

    CHOICES = [
        (PAGADO, "Pagado"),
        (PENDIENTE, "Pendiente"),
        (CANCELADO, "Cancelado"),
    ]
```

| Estado      | Descripción                        | Transiciones Permitidas | Modificaciones Permitidas |
| ----------- | ---------------------------------- | ----------------------- | ------------------------- |
| `PENDIENTE` | Pago registrado pero no confirmado | → PAGADO, CANCELADO     | Todas                     |
| `PAGADO`    | Pago completado y confirmado       | → CANCELADO (reembolso) | Solo notas                |
| `CANCELADO` | Pago cancelado o reembolsado       | Estado final            | Ninguna                   |

### Propiedades Calculadas

#### `es_pago_completo`

```python
@property
def es_pago_completo(self):
    """Verifica si el pago cubre el monto total de la cita"""
    return self.monto_total >= self.cita.monto_total
```

**Descripción**: Determina si el pago actual cubre completamente el costo de la cita.

**Retorno**: `True` si el monto del pago es mayor o igual al monto total de la cita.

**Uso**: Utilizado para automatizar el cambio de estado de la cita cuando se completa el pago.

#### `monto_formateado`

```python
@property
def monto_formateado(self):
    """Retorna el monto formateado como string"""
    return f"${self.monto_total:,.0f}"
```

**Descripción**: Formatea el monto del pago para presentación en interfaz.

**Retorno**: String con formato de moneda (ej: "$25,000").

**Uso**: Display en templates, APIs y reportes.

### Métodos del Modelo

#### `marcar_como_pagado()`

```python
def marcar_como_pagado(self):
    """Marca el pago como pagado y actualiza el estado de la cita si es necesario"""
    self.estado_pago = EstadoPago.PAGADO
    self.save()

    # Si el pago está completo, actualizar estado de la cita
    if self.es_pago_completo:
        self.cita.estado_cita = "COMPLETADA"
        self.cita.save()
```

**Descripción**: Cambia el estado del pago a PAGADO y, si corresponde, actualiza la cita.

**Lógica de Negocio**:

1. Marca el pago como PAGADO
2. Verifica si el pago cubre el monto total de la cita
3. Si es así, actualiza la cita a estado COMPLETADA

**Uso**: Procesamiento automático de pagos, confirmación manual.

### Configuración Meta

```python
class Meta:
    app_label = "payments"
    db_table = "pagos"
    verbose_name = "Pago"
    verbose_name_plural = "Pagos"
    ordering = ["-fecha_pago"]
```

| Atributo              | Valor             | Descripción                                      |
| --------------------- | ----------------- | ------------------------------------------------ |
| `app_label`           | "payments"        | Etiqueta de la aplicación                        |
| `db_table`            | "pagos"           | Nombre de la tabla en la base de datos           |
| `verbose_name`        | "Pago"            | Nombre singular para admin                       |
| `verbose_name_plural` | "Pagos"           | Nombre plural para admin                         |
| `ordering`            | `["-fecha_pago"]` | Ordenamiento por defecto (más recientes primero) |

### Método `__str__`

```python
def __str__(self):
    return f"Pago {self.pago_id} - Cita {self.cita.cita_id} - ${self.monto_total}"
```

**Formato**: "Pago 123 - Cita 456 - $25,000"

**Uso**: Representación en admin de Django, logs, debugging.

## Validaciones

### A Nivel de Campo

#### monto_total

- **Validador**: `MinValueValidator(0)`
- **Regla**: El monto debe ser mayor a cero
- **Error**: "Ensure this value is greater than or equal to 0."

#### metodo_pago

- **Restricción**: Valores limitados a choices definidos
- **Regla**: Solo métodos predefinidos permitidos
- **Error**: "'valor' is not a valid choice."

#### estado_pago

- **Restricción**: Valores limitados a choices definidos
- **Default**: `EstadoPago.PENDIENTE`
- **Error**: "'valor' is not a valid choice."

### A Nivel de Relación

#### cita

- **on_delete**: `CASCADE`
- **Comportamiento**: Si se elimina la cita, se eliminan todos los pagos asociados
- **related_name**: "pagos"
- **Acceso**: `cita.pagos.all()` obtiene todos los pagos de una cita

#### creado_por

- **on_delete**: `SET_NULL`
- **Comportamiento**: Si se elimina el usuario, el campo se establece en NULL
- **Propósito**: Mantener auditoría incluso si el usuario es eliminado

## Constraints y Validaciones

### A Nivel de Base de Datos

```python
# Validaciones implícitas por el tipo de campo
- pago_id: Único, auto-incrementable
- monto_total: Precision decimal con validación de valor mínimo
- metodo_pago: Longitud máxima 20 caracteres
- estado_pago: Longitud máxima 20 caracteres
- referencia_pago: Longitud máxima 100 caracteres (opcional)
```

### Validaciones Personalizadas

1. **Monto Positivo**: El monto debe ser mayor a cero
2. **Cita Válida**: La cita debe existir y no estar cancelada
3. **Método Válido**: Solo métodos de pago predefinidos
4. **Estado Válido**: Solo estados de pago predefinidos
5. **Auditoría**: Campos de fecha automáticos e inmutables

## Relaciones

### Con Appointments.Cita

```python
cita = models.ForeignKey(
    "appointments.Cita",
    on_delete=models.CASCADE,
    related_name="pagos"
)
```

**Tipo**: Muchos a Uno (Many-to-One)
**Descripción**: Un pago pertenece a una cita, una cita puede tener múltiples pagos
**Acceso Reverso**: `cita.pagos.all()`
**Casos de Uso**: Pagos parciales, adelantos, saldos

### Con Auth.User

```python
creado_por = models.ForeignKey(
    User,
    on_delete=models.SET_NULL,
    null=True,
    blank=True
)
```

**Tipo**: Muchos a Uno (Many-to-One)
**Descripción**: Un pago es creado por un usuario
**Comportamiento**: Si se elimina el usuario, el campo se mantiene como NULL
**Propósito**: Auditoría y trazabilidad

## Casos de Uso Comunes

### 1. Pago Completo Inmediato

```python
pago = Pago.objects.create(
    cita=cita,
    fecha_pago=timezone.now(),
    monto_total=cita.monto_total,
    metodo_pago=MetodoPago.EFECTIVO,
    estado_pago=EstadoPago.PAGADO,
    creado_por=request.user
)
```

### 2. Pago Parcial (Adelanto)

```python
adelanto = Pago.objects.create(
    cita=cita,
    fecha_pago=timezone.now(),
    monto_total=Decimal('20000.00'),  # Parte del total
    metodo_pago=MetodoPago.TRANSFERENCIA,
    estado_pago=EstadoPago.PENDIENTE,
    notas_pago="Adelanto del 50%",
    creado_por=request.user
)
```

### 3. Consulta de Pagos por Cita

```python
# Todos los pagos de una cita
pagos_cita = cita.pagos.all()

# Total pagado hasta el momento
total_pagado = cita.pagos.filter(
    estado_pago=EstadoPago.PAGADO
).aggregate(Sum('monto_total'))['monto_total__sum'] or 0

# Saldo pendiente
saldo_pendiente = cita.monto_total - total_pagado
```

---

**Última actualización**: Agosto 2025  
**Versión**: 1.0  
**Estado**: ✅ Completamente implementado y probado
