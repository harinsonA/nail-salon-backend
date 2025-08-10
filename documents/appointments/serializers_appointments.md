# Documentación de Serializers - Appointments

## Visión General

Los serializers son el componente clave que convierte entre objetos Python (modelos Django) y formatos de datos como JSON. La aplicación appointments utiliza serializers especializados para diferentes casos de uso, optimizando así la transferencia de datos y la experiencia del usuario en la gestión de citas y servicios.

## Archivos Principales

**Ubicación**: `apps/appointments/serializers/`

- `cita_serializer.py` - Serializers para el modelo Cita
- `detalle_cita_serializer.py` - Serializer para el modelo DetalleCita

## Serializers Disponibles

### Cita Serializers

1. **CitaSerializer** (Completo) - Para operaciones CRUD con todos los campos
2. **CitaListSerializer** (Simplificado) - Para listados optimizados

### DetalleCita Serializers

3. **DetalleCitaSerializer** (Completo) - Para gestión de servicios en citas

---

## CitaSerializer

### Propósito

Serializer principal para operaciones CRUD completas de citas. Incluye todos los campos del modelo, validaciones personalizadas y relaciones anidadas con cliente y detalles de servicios.

### Definición

```python
class CitaSerializer(serializers.ModelSerializer):
    """
    Serializer completo para el modelo Cita
    """

    # Campo cliente anidado con información básica
    cliente = ClienteSerializer(read_only=True)

    # Campo para recibir ID del cliente en creación/actualización
    cliente_id = serializers.IntegerField(write_only=True)

    # Detalles de servicios anidados
    detalles = DetalleCitaSerializer(many=True, read_only=True)

    # Campo calculado de total formateado
    total_formateado = serializers.SerializerMethodField()

    class Meta:
        model = Cita
        fields = [
            "id",
            "cliente",
            "cliente_id",
            "fecha_cita",
            "estado",
            "total",
            "total_formateado",
            "observaciones",
            "fecha_creacion",
            "fecha_actualizacion",
            "detalles"
        ]
        read_only_fields = [
            "id",
            "total",
            "fecha_creacion",
            "fecha_actualizacion"
        ]
```

### Campos del Serializer

#### Campos de Solo Lectura

| Campo                 | Tipo                  | Fuente   | Descripción                      |
| --------------------- | --------------------- | -------- | -------------------------------- |
| `id`                  | AutoField             | Modelo   | ID primario de la cita           |
| `cliente`             | ClienteSerializer     | Relación | Información completa del cliente |
| `total`               | DecimalField          | Modelo   | Total calculado automáticamente  |
| `total_formateado`    | SerializerMethod      | Método   | Total formateado para mostrar    |
| `fecha_creacion`      | DateTimeField         | Modelo   | Timestamp creación (auto)        |
| `fecha_actualizacion` | DateTimeField         | Modelo   | Timestamp actualización (auto)   |
| `detalles`            | DetalleCitaSerializer | Relación | Lista de servicios en la cita    |

#### Campos Editables

| Campo           | Tipo          | Validaciones             | Descripción                 |
| --------------- | ------------- | ------------------------ | --------------------------- |
| `cliente_id`    | IntegerField  | Requerido, debe existir  | ID del cliente (write-only) |
| `fecha_cita`    | DateTimeField | Requerida, formato ISO   | Fecha y hora de la cita     |
| `estado`        | CharField     | Choices predefinidos     | Estado actual de la cita    |
| `observaciones` | TextField     | Opcional, max 1000 chars | Notas adicionales           |

### Métodos Personalizados

#### `get_total_formateado(self, obj)`

```python
def get_total_formateado(self, obj):
    """
    Retorna el total formateado con símbolo de moneda
    """
    return f"${obj.total:,.0f}"
```

**Propósito**: Formatea el total para mostrar en la interfaz con símbolo de pesos colombianos.

#### `validate_cliente_id(self, value)`

```python
def validate_cliente_id(self, value):
    """
    Validar que el cliente existe y está activo
    """
    try:
        cliente = Cliente.objects.get(pk=value)
        if not cliente.activo:
            raise serializers.ValidationError("El cliente no está activo")
        return value
    except Cliente.DoesNotExist:
        raise serializers.ValidationError("El cliente no existe")
```

**Propósito**: Valida que el cliente existe y está en estado activo.

#### `validate_fecha_cita(self, value)`

```python
def validate_fecha_cita(self, value):
    """
    Validar que la fecha de la cita sea futura
    """
    if value <= timezone.now():
        raise serializers.ValidationError("La fecha de la cita debe ser futura")
    return value
```

**Propósito**: Asegura que las citas solo se puedan programar para fechas futuras.

#### `validate(self, attrs)`

```python
def validate(self, attrs):
    """
    Validaciones a nivel de instancia
    """
    if self.instance and self.instance.estado in ['completada', 'cancelada']:
        # Solo permitir cambios en observaciones para citas finalizadas
        campos_permitidos = {'observaciones'}
        campos_cambiados = set(attrs.keys())
        if not campos_cambiados.issubset(campos_permitidos):
            raise serializers.ValidationError(
                "Solo se pueden modificar las observaciones en citas completadas o canceladas"
            )

    return attrs
```

**Propósito**: Valida reglas de negocio a nivel de instancia completa.

### Estados Permitidos

```python
ESTADO_CHOICES = [
    ('programada', 'Programada'),
    ('confirmada', 'Confirmada'),
    ('en_proceso', 'En Proceso'),
    ('completada', 'Completada'),
    ('cancelada', 'Cancelada'),
]
```

---

## CitaListSerializer

### Propósito

Serializer optimizado para listados. Incluye solo los campos esenciales para mejorar el rendimiento en consultas masivas.

### Definición

```python
class CitaListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listados de citas
    """

    # Cliente con información mínima
    cliente = serializers.SerializerMethodField()

    # Total formateado para mostrar
    total_formateado = serializers.SerializerMethodField()

    # Fecha formateada
    fecha_formateada = serializers.SerializerMethodField()

    class Meta:
        model = Cita
        fields = [
            "id",
            "cliente",
            "fecha_cita",
            "fecha_formateada",
            "estado",
            "total",
            "total_formateado",
            "observaciones"
        ]
```

### Campos del Serializer

| Campo              | Tipo             | Descripción                   |
| ------------------ | ---------------- | ----------------------------- |
| `id`               | AutoField        | ID de la cita                 |
| `cliente`          | SerializerMethod | Info básica del cliente       |
| `fecha_cita`       | DateTimeField    | Fecha y hora original         |
| `fecha_formateada` | SerializerMethod | Fecha formateada para mostrar |
| `estado`           | CharField        | Estado actual                 |
| `total`            | DecimalField     | Total numérico                |
| `total_formateado` | SerializerMethod | Total con formato de moneda   |
| `observaciones`    | TextField        | Notas de la cita              |

### Métodos Personalizados

#### `get_cliente(self, obj)`

```python
def get_cliente(self, obj):
    """
    Retorna información básica del cliente
    """
    return {
        "id": obj.cliente.cliente_id,
        "nombre_completo": obj.cliente.nombre_completo,
        "telefono": obj.cliente.telefono
    }
```

#### `get_fecha_formateada(self, obj)`

```python
def get_fecha_formateada(self, obj):
    """
    Retorna la fecha en formato local colombiano
    """
    return obj.fecha_cita.strftime("%d/%m/%Y %H:%M")
```

#### `get_total_formateado(self, obj)`

```python
def get_total_formateado(self, obj):
    """
    Retorna el total formateado con símbolo de moneda
    """
    return f"${obj.total:,.0f}"
```

---

## DetalleCitaSerializer

### Propósito

Serializer para gestionar los servicios incluidos en cada cita. Maneja la relación entre citas y servicios con cantidades y precios específicos.

### Definición

```python
class DetalleCitaSerializer(serializers.ModelSerializer):
    """
    Serializer para detalles de servicios en citas
    """

    # Servicio anidado con información completa
    servicio = ServicioSerializer(read_only=True)

    # Campo para recibir ID del servicio
    servicio_id = serializers.IntegerField(write_only=True)

    # Subtotal calculado
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    # Subtotal formateado
    subtotal_formateado = serializers.SerializerMethodField()

    class Meta:
        model = DetalleCita
        fields = [
            "id",
            "cita",
            "servicio",
            "servicio_id",
            "precio",
            "cantidad",
            "subtotal",
            "subtotal_formateado"
        ]
        read_only_fields = ["id", "subtotal"]
```

### Campos del Serializer

#### Campos de Solo Lectura

| Campo                 | Tipo               | Fuente   | Descripción                       |
| --------------------- | ------------------ | -------- | --------------------------------- |
| `id`                  | AutoField          | Modelo   | ID del detalle                    |
| `servicio`            | ServicioSerializer | Relación | Información completa del servicio |
| `subtotal`            | DecimalField       | Modelo   | Cantidad × precio                 |
| `subtotal_formateado` | SerializerMethod   | Método   | Subtotal con formato de moneda    |

#### Campos Editables

| Campo         | Tipo         | Validaciones              | Descripción                    |
| ------------- | ------------ | ------------------------- | ------------------------------ |
| `cita`        | IntegerField | Requerido, debe existir   | ID de la cita asociada         |
| `servicio_id` | IntegerField | Requerido, debe existir   | ID del servicio (write-only)   |
| `precio`      | DecimalField | Requerido, > 0            | Precio del servicio en la cita |
| `cantidad`    | IntegerField | Requerido, > 0, default 1 | Cantidad del servicio          |

### Métodos Personalizados

#### `get_subtotal_formateado(self, obj)`

```python
def get_subtotal_formateado(self, obj):
    """
    Retorna el subtotal formateado con símbolo de moneda
    """
    return f"${obj.subtotal:,.0f}"
```

#### `validate_servicio_id(self, value)`

```python
def validate_servicio_id(self, value):
    """
    Validar que el servicio existe y está activo
    """
    try:
        servicio = Servicio.objects.get(pk=value)
        if not servicio.activo:
            raise serializers.ValidationError("El servicio no está activo")
        return value
    except Servicio.DoesNotExist:
        raise serializers.ValidationError("El servicio no existe")
```

#### `validate_precio(self, value)`

```python
def validate_precio(self, value):
    """
    Validar que el precio sea positivo
    """
    if value <= 0:
        raise serializers.ValidationError("El precio debe ser mayor a cero")
    return value
```

#### `validate_cantidad(self, value)`

```python
def validate_cantidad(self, value):
    """
    Validar que la cantidad sea positiva
    """
    if value <= 0:
        raise serializers.ValidationError("La cantidad debe ser mayor a cero")
    return value
```

#### `validate(self, attrs)`

```python
def validate(self, attrs):
    """
    Validaciones a nivel de instancia
    """
    cita_id = attrs.get('cita')
    if cita_id:
        try:
            cita = Cita.objects.get(pk=cita_id.id if hasattr(cita_id, 'id') else cita_id)
            if cita.estado in ['completada', 'cancelada']:
                raise serializers.ValidationError(
                    "No se pueden modificar servicios en citas completadas o canceladas"
                )
        except Cita.DoesNotExist:
            raise serializers.ValidationError("La cita no existe")

    return attrs
```

#### `create(self, validated_data)`

```python
def create(self, validated_data):
    """
    Crear detalle y actualizar total de la cita
    """
    detalle = DetalleCita.objects.create(**validated_data)
    detalle.cita.actualizar_total()
    return detalle
```

#### `update(self, instance, validated_data)`

```python
def update(self, instance, validated_data):
    """
    Actualizar detalle y recalcular total de la cita
    """
    for attr, value in validated_data.items():
        setattr(instance, attr, value)
    instance.save()
    instance.cita.actualizar_total()
    return instance
```

## Validaciones Cruzadas

### Validación de Estados

Los serializers implementan validaciones que respetan las reglas de negocio:

1. **Citas completadas/canceladas**: No permiten modificaciones excepto en observaciones
2. **Servicios en citas finalizadas**: No se pueden agregar, modificar o eliminar
3. **Fechas futuras**: Las nuevas citas deben programarse para fechas futuras
4. **Clientes activos**: Solo se pueden asignar clientes en estado activo
5. **Servicios activos**: Solo se pueden agregar servicios disponibles

### Validación de Precios

```python
def validar_precio_servicio(servicio_id, precio_propuesto):
    """
    Validar que el precio no difiera significativamente del precio base
    """
    servicio = Servicio.objects.get(pk=servicio_id)
    diferencia = abs(precio_propuesto - servicio.precio) / servicio.precio

    if diferencia > 0.5:  # 50% de diferencia máxima
        raise serializers.ValidationError(
            f"El precio difiere mucho del precio base (${servicio.precio})"
        )
```

## Optimizaciones de Rendimiento

### Select Related en Serializers

```python
# En CitaSerializer - optimiza consultas de cliente
def to_representation(self, instance):
    # Evita N+1 queries usando select_related en ViewSet
    return super().to_representation(instance)

# En DetalleCitaSerializer - optimiza consultas de servicio
def to_representation(self, instance):
    # Evita N+1 queries usando select_related en ViewSet
    return super().to_representation(instance)
```

### Campos Calculados Eficientes

Los campos como `total_formateado`, `subtotal_formateado` y `fecha_formateada` se calculan a nivel de serializer para evitar lógica en el frontend, manteniendo la responsabilidad de formato en el backend.

## Consideraciones de Versionado

Los serializers están diseñados para ser retrocompatibles:

1. **Campos nuevos**: Se agregan como opcionales
2. **Campos eliminados**: Se mantienen como deprecated antes de eliminar
3. **Cambios de formato**: Se mantienen alias para compatibilidad
4. **Validaciones**: Se implementan de forma progresiva

## Ejemplo de Uso

### Crear Cita Completa

```python
# Datos de entrada
data = {
    "cliente_id": 1,
    "fecha_cita": "2024-01-25T15:00:00Z",
    "observaciones": "Cita para manicure y pedicure"
}

# Serializar y validar
serializer = CitaSerializer(data=data)
if serializer.is_valid():
    cita = serializer.save()

    # Agregar servicios
    detalle_data = {
        "cita": cita.id,
        "servicio_id": 1,
        "precio": "45000.00",
        "cantidad": 1
    }

    detalle_serializer = DetalleCitaSerializer(data=detalle_data)
    if detalle_serializer.is_valid():
        detalle_serializer.save()
```

### Respuesta JSON Típica

```json
{
  "id": 1,
  "cliente": {
    "id": 1,
    "nombre_completo": "Juan Pérez",
    "telefono": "3001234567",
    "email": "juan@email.com"
  },
  "fecha_cita": "2024-01-25T15:00:00Z",
  "estado": "programada",
  "total": "45000.00",
  "total_formateado": "$45,000",
  "observaciones": "Cita para manicure y pedicure",
  "fecha_creacion": "2024-01-15T10:30:00Z",
  "fecha_actualizacion": "2024-01-15T10:30:00Z",
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
      "subtotal": "45000.00",
      "subtotal_formateado": "$45,000"
    }
  ]
}
```
