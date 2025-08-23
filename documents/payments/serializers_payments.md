# Documentación de Serializers - Payments App

## Visión General

Los serializers de la aplicación payments están diseñados para manejar la serialización/deserialización de datos del modelo `Pago`, proporcionando diferentes niveles de detalle según el contexto de uso. Utilizan Django REST Framework para conversión automática entre objetos Python y formatos JSON.

## Archivos de Serializers

### Estructura de Archivos

```
apps/payments/serializers/
├── __init__.py
├── pago_serializer.py        # Serializer principal para pagos
└── utils.py                  # Utilidades y campos personalizados
```

## Serializer Principal (`pago_serializer.py`)

### Imports y Dependencias

```python
from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from apps.payments.models import Pago
from apps.appointments.models import Cita
from apps.clients.models import Cliente
from apps.authentication.models import User
from utils.choices import MetodoPago, EstadoPago
```

## PagoSerializer (Serializer Completo)

### Definición de Clase

```python
class PagoSerializer(serializers.ModelSerializer):
    """
    Serializer completo para el modelo Pago
    Usado para operaciones de detalle, actualización y respuestas completas
    """

    # Campos calculados
    pago_id = serializers.IntegerField(source='id', read_only=True)
    monto_formateado = serializers.SerializerMethodField()
    es_pago_completo = serializers.SerializerMethodField()

    # Información expandida de la cita
    cita_info = serializers.SerializerMethodField()

    # Campos de auditoría (solo lectura)
    fecha_creacion = serializers.DateTimeField(read_only=True)
    fecha_actualizacion = serializers.DateTimeField(read_only=True)
    creado_por = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Pago
        fields = [
            'id',
            'pago_id',
            'cita',
            'cita_info',
            'fecha_pago',
            'monto_total',
            'monto_formateado',
            'metodo_pago',
            'estado_pago',
            'referencia_pago',
            'notas_pago',
            'es_pago_completo',
            'fecha_creacion',
            'fecha_actualizacion',
            'creado_por'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_actualizacion', 'creado_por']
```

### Métodos del Serializer

#### `get_monto_formateado(self, obj)`

```python
def get_monto_formateado(self, obj):
    """
    Formatear el monto con separadores de miles y símbolo de moneda
    """
    if obj.monto_total:
        # Formatear con separadores de miles
        monto_str = f"{obj.monto_total:,.0f}".replace(',', '.')
        return f"${monto_str}"
    return "$0"
```

**Propósito**: Proporciona una representación amigable del monto para mostrar en interfaces de usuario.

**Ejemplos**:

- `25000.00` → `"$25.000"`
- `125500.00` → `"$125.500"`
- `0.00` → `"$0"`

#### `get_es_pago_completo(self, obj)`

```python
def get_es_pago_completo(self, obj):
    """
    Determinar si el pago cubre el monto total de la cita
    """
    if obj.cita and obj.monto_total:
        return obj.monto_total >= obj.cita.monto_total
    return False
```

**Propósito**: Indica si el pago cubre completamente el costo de la cita.

**Lógica**:

- Compara `monto_total` del pago con `monto_total` de la cita
- Retorna `True` si el pago es igual o mayor al costo de la cita
- Retorna `False` si es un pago parcial o hay datos faltantes

#### `get_cita_info(self, obj)`

```python
def get_cita_info(self, obj):
    """
    Obtener información expandida de la cita asociada
    """
    if obj.cita:
        return {
            'cita_id': obj.cita.id,
            'fecha_cita': obj.cita.fecha_cita,
            'cliente_nombre': obj.cita.cliente.nombre_completo if obj.cita.cliente else None,
            'estado_cita': obj.cita.estado_cita,
            'monto_total_cita': str(obj.cita.monto_total)
        }
    return None
```

**Propósito**: Proporciona información contextual de la cita sin requerir consultas adicionales.

**Campos Incluidos**:

- `cita_id`: ID de la cita
- `fecha_cita`: Fecha y hora de la cita
- `cliente_nombre`: Nombre completo del cliente
- `estado_cita`: Estado actual de la cita
- `monto_total_cita`: Monto total de la cita

### Validaciones del Serializer

#### `validate_monto_total(self, value)`

```python
def validate_monto_total(self, value):
    """
    Validar que el monto sea positivo y mayor a cero
    """
    if value <= 0:
        raise serializers.ValidationError("El monto debe ser mayor a cero")

    if value > Decimal('9999999.99'):
        raise serializers.ValidationError("El monto excede el límite máximo permitido")

    return value
```

**Validaciones Aplicadas**:

- Monto debe ser positivo
- Monto debe ser mayor a cero
- Monto no puede exceder 9,999,999.99

#### `validate_metodo_pago(self, value)`

```python
def validate_metodo_pago(self, value):
    """
    Validar que el método de pago sea válido
    """
    metodos_validos = [choice[0] for choice in MetodoPago.CHOICES]
    if value not in metodos_validos:
        raise serializers.ValidationError(
            f"Método de pago inválido. Opciones válidas: {', '.join(metodos_validos)}"
        )
    return value
```

**Validaciones Aplicadas**:

- Verifica que el método esté en las opciones predefinidas
- Proporciona mensaje de error con opciones válidas

#### `validate_estado_pago(self, value)`

```python
def validate_estado_pago(self, value):
    """
    Validar que el estado de pago sea válido
    """
    estados_validos = [choice[0] for choice in EstadoPago.CHOICES]
    if value not in estados_validos:
        raise serializers.ValidationError(
            f"Estado de pago inválido. Opciones válidas: {', '.join(estados_validos)}"
        )
    return value
```

#### `validate_cita(self, value)`

```python
def validate_cita(self, value):
    """
    Validar que la cita exista y esté en estado válido para pagos
    """
    if not value:
        raise serializers.ValidationError("La cita es requerida")

    try:
        cita = Cita.objects.get(id=value.id)
    except Cita.DoesNotExist:
        raise serializers.ValidationError("La cita especificada no existe")

    if cita.estado_cita == 'CANCELADA':
        raise serializers.ValidationError("No se puede crear un pago para una cita cancelada")

    return value
```

**Validaciones Aplicadas**:

- Verifica que la cita exista
- Impide crear pagos para citas canceladas
- Valida la integridad referencial

#### `validate(self, attrs)`

```python
def validate(self, attrs):
    """
    Validaciones a nivel de objeto
    """
    # Validar que la fecha de pago no sea futura
    fecha_pago = attrs.get('fecha_pago')
    if fecha_pago and fecha_pago > timezone.now():
        raise serializers.ValidationError({
            'fecha_pago': 'La fecha de pago no puede ser futura'
        })

    # Validar monto vs cita si se proporciona
    cita = attrs.get('cita')
    monto_total = attrs.get('monto_total')

    if cita and monto_total:
        if monto_total > cita.monto_total * Decimal('1.1'):  # 10% de tolerancia
            raise serializers.ValidationError({
                'monto_total': f'El monto no puede exceder significativamente el costo de la cita (${cita.monto_total})'
            })

    # Validar referencia para ciertos métodos
    metodo_pago = attrs.get('metodo_pago')
    referencia_pago = attrs.get('referencia_pago')

    if metodo_pago in ['TARJETA', 'TRANSFERENCIA'] and not referencia_pago:
        raise serializers.ValidationError({
            'referencia_pago': f'La referencia es requerida para pagos con {metodo_pago}'
        })

    return attrs
```

**Validaciones Complejas**:

- Fecha de pago no puede ser futura
- Monto no puede exceder significativamente el costo de la cita
- Referencia requerida para tarjetas y transferencias

## PagoListSerializer (Serializer para Listados)

### Definición Optimizada

```python
class PagoListSerializer(serializers.ModelSerializer):
    """
    Serializer optimizado para listados de pagos
    Incluye menos campos para mejorar performance
    """

    pago_id = serializers.IntegerField(source='id', read_only=True)
    monto_formateado = serializers.SerializerMethodField()

    # Información básica de la cita
    cliente_nombre = serializers.CharField(source='cita.cliente.nombre_completo', read_only=True)
    fecha_cita = serializers.DateTimeField(source='cita.fecha_cita', read_only=True)

    class Meta:
        model = Pago
        fields = [
            'id',
            'pago_id',
            'cita',
            'cliente_nombre',
            'fecha_cita',
            'fecha_pago',
            'monto_total',
            'monto_formateado',
            'metodo_pago',
            'estado_pago',
            'notas_pago',
            'referencia_pago',
            'fecha_creacion',
            'fecha_actualizacion'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_actualizacion']

    def get_monto_formateado(self, obj):
        """Formatear monto para listados"""
        if obj.monto_total:
            return f"${obj.monto_total:,.0f}".replace(',', '.')
        return "$0"
```

**Optimizaciones**:

- Menos campos para reducir tamaño de respuesta
- Información de cliente directamente en la consulta
- Sin información expandida de cita

## PagoCreateSerializer (Serializer para Creación)

### Campos Específicos para Creación

```python
class PagoCreateSerializer(serializers.ModelSerializer):
    """
    Serializer específico para crear pagos
    Incluye validaciones adicionales y valores por defecto
    """

    # Campos con valores por defecto
    fecha_pago = serializers.DateTimeField(required=False)
    estado_pago = serializers.ChoiceField(
        choices=EstadoPago.CHOICES,
        default='PENDIENTE',
        required=False
    )

    class Meta:
        model = Pago
        fields = [
            'cita',
            'fecha_pago',
            'monto_total',
            'metodo_pago',
            'estado_pago',
            'referencia_pago',
            'notas_pago'
        ]

    def validate(self, attrs):
        """
        Validaciones específicas para creación
        """
        # Asignar fecha actual si no se proporciona
        if 'fecha_pago' not in attrs:
            attrs['fecha_pago'] = timezone.now()

        # Validar que no existan pagos duplicados para la misma cita
        cita = attrs.get('cita')
        if cita:
            pagos_existentes = Pago.objects.filter(
                cita=cita,
                estado_pago__in=['PENDIENTE', 'PAGADO']
            )

            # Calcular total de pagos existentes
            total_pagado = sum(p.monto_total for p in pagos_existentes)
            nuevo_monto = attrs.get('monto_total', 0)

            if total_pagado + nuevo_monto > cita.monto_total * Decimal('1.05'):  # 5% tolerancia
                raise serializers.ValidationError({
                    'monto_total': f'El total de pagos excedería el costo de la cita. Ya pagado: ${total_pagado}'
                })

        return super().validate(attrs)

    def create(self, validated_data):
        """
        Crear pago con lógica adicional
        """
        # El usuario creador se asigna en la vista
        return super().create(validated_data)
```

**Características Específicas**:

- Fecha automática si no se proporciona
- Estado por defecto: PENDIENTE
- Validación de pagos duplicados
- Control de límites de pago por cita

## Campos Personalizados

### MontoField (Campo Personalizado)

```python
# En apps/payments/serializers/utils.py

class MontoField(serializers.DecimalField):
    """
    Campo personalizado para manejar montos monetarios
    """

    def __init__(self, **kwargs):
        kwargs.setdefault('max_digits', 10)
        kwargs.setdefault('decimal_places', 2)
        kwargs.setdefault('min_value', Decimal('0.01'))
        kwargs.setdefault('max_value', Decimal('9999999.99'))
        super().__init__(**kwargs)

    def to_representation(self, value):
        """
        Convertir a representación string sin notación científica
        """
        if value is None:
            return None
        return str(value)

    def to_internal_value(self, data):
        """
        Convertir desde string a Decimal
        """
        if isinstance(data, str):
            # Limpiar formato (remover $, comas, etc.)
            data = data.replace('$', '').replace(',', '').replace('.', '', data.count('.') - 1)

        return super().to_internal_value(data)
```

### MetodoPagoField (Campo de Elección)

```python
class MetodoPagoField(serializers.ChoiceField):
    """
    Campo personalizado para métodos de pago
    """

    def __init__(self, **kwargs):
        kwargs['choices'] = MetodoPago.CHOICES
        super().__init__(**kwargs)

    def to_representation(self, value):
        """
        Incluir descripción legible junto con el valor
        """
        if value:
            for choice_value, choice_label in MetodoPago.CHOICES:
                if choice_value == value:
                    return {
                        'value': value,
                        'label': choice_label
                    }
        return value
```

## Serializers de Solo Lectura

### PagoReadOnlySerializer

```python
class PagoReadOnlySerializer(serializers.ModelSerializer):
    """
    Serializer de solo lectura para reportes y estadísticas
    """

    pago_id = serializers.IntegerField(source='id')
    cliente_nombre = serializers.CharField(source='cita.cliente.nombre_completo')
    cliente_telefono = serializers.CharField(source='cita.cliente.telefono')
    servicio_nombre = serializers.CharField(source='cita.servicio.nombre')
    monto_formateado = serializers.SerializerMethodField()
    metodo_pago_label = serializers.SerializerMethodField()
    estado_pago_label = serializers.SerializerMethodField()

    class Meta:
        model = Pago
        fields = [
            'pago_id',
            'fecha_pago',
            'monto_total',
            'monto_formateado',
            'metodo_pago',
            'metodo_pago_label',
            'estado_pago',
            'estado_pago_label',
            'cliente_nombre',
            'cliente_telefono',
            'servicio_nombre',
            'referencia_pago',
            'notas_pago'
        ]

    def get_monto_formateado(self, obj):
        return f"${obj.monto_total:,.0f}".replace(',', '.')

    def get_metodo_pago_label(self, obj):
        return dict(MetodoPago.CHOICES).get(obj.metodo_pago, obj.metodo_pago)

    def get_estado_pago_label(self, obj):
        return dict(EstadoPago.CHOICES).get(obj.estado_pago, obj.estado_pago)
```

## Uso de los Serializers

### En ViewSets

```python
# En apps/payments/views/pago_views.py

class PagoViewSet(viewsets.ModelViewSet):
    def get_serializer_class(self):
        if self.action == 'list':
            return PagoListSerializer
        elif self.action == 'create':
            return PagoCreateSerializer
        return PagoSerializer
```

### En Vistas Personalizadas

```python
# Para estadísticas
def estadisticas_view(request):
    pagos = Pago.objects.all()
    serializer = PagoReadOnlySerializer(pagos, many=True)
    return Response(serializer.data)

# Para reportes
def generar_reporte(request):
    pagos = Pago.objects.select_related('cita__cliente', 'cita__servicio')
    serializer = PagoReadOnlySerializer(pagos, many=True)
    return generar_excel(serializer.data)
```

## Validaciones Avanzadas

### Validación de Negocio

```python
def validate_business_rules(self, attrs):
    """
    Validaciones específicas del negocio
    """
    cita = attrs.get('cita')
    monto = attrs.get('monto_total')
    estado = attrs.get('estado_pago')

    # Regla: No se puede marcar como PAGADO si el monto no cubre la cita
    if estado == 'PAGADO' and cita and monto:
        if monto < cita.monto_total:
            raise serializers.ValidationError({
                'estado_pago': 'No se puede marcar como PAGADO un monto parcial'
            })

    # Regla: Los pagos de más de $100,000 requieren referencia
    if monto and monto > Decimal('100000') and not attrs.get('referencia_pago'):
        raise serializers.ValidationError({
            'referencia_pago': 'Pagos mayores a $100,000 requieren referencia'
        })

    return attrs
```

### Validación de Concurrencia

```python
def validate_concurrency(self, attrs):
    """
    Validar actualizaciones concurrentes
    """
    if self.instance:  # Solo en actualizaciones
        # Verificar que el objeto no haya sido modificado por otro usuario
        fecha_actualizacion = attrs.get('fecha_actualizacion')
        if fecha_actualizacion and fecha_actualizacion != self.instance.fecha_actualizacion:
            raise serializers.ValidationError({
                'non_field_errors': ['El pago ha sido modificado por otro usuario']
            })

    return attrs
```

## Performance y Optimizaciones

### Consultas Optimizadas

```python
# En el ViewSet
def get_queryset(self):
    return Pago.objects.select_related(
        'cita',
        'cita__cliente',
        'cita__servicio',
        'creado_por'
    ).prefetch_related(
        'cita__servicios'
    )
```

### Caching de Campos Calculados

```python
from django.core.cache import cache

def get_monto_formateado(self, obj):
    """
    Cachear formato de montos para mejor performance
    """
    cache_key = f'monto_formato_{obj.id}_{obj.monto_total}'
    formato = cache.get(cache_key)

    if formato is None:
        formato = f"${obj.monto_total:,.0f}".replace(',', '.')
        cache.set(cache_key, formato, 3600)  # 1 hora

    return formato
```

---

**Última actualización**: Agosto 2025  
**Versión**: 1.0  
**Estado**: ✅ Completamente implementado y probado
