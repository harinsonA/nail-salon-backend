# Documentación de Serializers - Servicio

## Visión General

Los serializers son el componente clave que convierte entre objetos Python (modelos Django) y formatos de datos como JSON. La aplicación services utiliza dos serializers especializados para diferentes casos de uso, optimizando así la transferencia de datos y la experiencia del usuario.

## Archivo Principal

**Ubicación**: `apps/services/serializers/servicio_serializer.py`

## Serializers Disponibles

### 1. ServicioSerializer (Completo)

### 2. ServicioListSerializer (Simplificado)

---

## ServicioSerializer

### Propósito

Serializer principal para operaciones CRUD completas. Incluye todos los campos del modelo, validaciones personalizadas y campos computados.

### Definición

```python
class ServicioSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Servicio
    """

    # Añadir campo 'id' para compatibilidad con API REST estándar
    id = serializers.IntegerField(source="servicio_id", read_only=True)
    duracion_estimada_horas = serializers.SerializerMethodField()
    precio_formateado = serializers.SerializerMethodField()

    class Meta:
        model = Servicio
        fields = [
            "id",
            "servicio_id",
            "nombre_servicio",
            "precio",
            "precio_formateado",
            "descripcion",
            "duracion_estimada",
            "duracion_estimada_horas",
            "activo",
            "categoria",
            "imagen",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "servicio_id",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
```

### Campos del Serializer

#### Campos de Solo Lectura

| Campo                     | Tipo             | Fuente        | Descripción                    |
| ------------------------- | ---------------- | ------------- | ------------------------------ |
| `id`                      | IntegerField     | `servicio_id` | Alias REST estándar para el ID |
| `servicio_id`             | AutoField        | Modelo        | ID primario original           |
| `precio_formateado`       | SerializerMethod | Método        | Precio con formato de moneda   |
| `duracion_estimada_horas` | SerializerMethod | Método        | Duración en formato legible    |
| `fecha_creacion`          | DateTimeField    | Modelo        | Timestamp creación (auto)      |
| `fecha_actualizacion`     | DateTimeField    | Modelo        | Timestamp actualización (auto) |

#### Campos Editables

| Campo               | Tipo          | Validaciones                     | Descripción                    |
| ------------------- | ------------- | -------------------------------- | ------------------------------ |
| `nombre_servicio`   | CharField     | Requerido, único, max 200 chars  | Nombre del servicio            |
| `precio`            | DecimalField  | Requerido, >= 0, max 10 dígitos  | Precio del servicio            |
| `descripcion`       | TextField     | Opcional, puede ser nulo         | Descripción del servicio       |
| `duracion_estimada` | DurationField | Opcional, formato válido         | Duración estimada del servicio |
| `activo`            | BooleanField  | Opcional, default True           | Estado del servicio            |
| `categoria`         | CharField     | Opcional, max 100 chars          | Categoría del servicio         |
| `imagen`            | ImageField    | Opcional, upload_to="servicios/" | Imagen del servicio            |

### Métodos de SerializerMethodField

#### get_duracion_estimada_horas

```python
def get_duracion_estimada_horas(self, obj):
    """
    Convertir duración a formato legible
    """
    if obj.duracion_estimada:
        total_seconds = obj.duracion_estimada.total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        return f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
    return "No especificado"
```

**Ejemplos de Output**:

- `timedelta(minutes=60)` → `"1h 0m"`
- `timedelta(minutes=90)` → `"1h 30m"`
- `timedelta(minutes=45)` → `"45m"`
- `None` → `"No especificado"`

#### get_precio_formateado

```python
def get_precio_formateado(self, obj):
    """
    Formatear precio con símbolo de moneda
    """
    return f"${obj.precio:,.2f}"
```

**Ejemplos de Output**:

- `25000.00` → `"$25,000.00"`
- `1500.50` → `"$1,500.50"`
- `35000` → `"$35,000.00"`

### Validaciones Personalizadas

#### Validación de Nombre Único

```python
def validate_nombre_servicio(self, value):
    """
    Validar que el nombre del servicio sea único
    """
    if Servicio.objects.filter(nombre_servicio=value).exists():
        if self.instance and self.instance.nombre_servicio == value:
            return value
        raise serializers.ValidationError("Ya existe un servicio con este nombre.")
    return value
```

**Características**:

- Verifica unicidad del nombre del servicio
- Permite mantener el mismo nombre en actualizaciones
- Mensaje de error personalizado en español

#### Validación de Precio

```python
def validate_precio(self, value):
    """
    Validar que el precio sea mayor o igual a 0
    """
    if value < 0:
        raise serializers.ValidationError("El precio debe ser mayor o igual a 0.")
    return value
```

**Características**:

- Asegura que el precio no sea negativo
- Complementa la validación del modelo
- Mensaje claro en español

#### Validación de Duración

```python
def validate_duracion_estimada(self, value):
    """
    Validar duración estimada
    """
    if value and value.total_seconds() <= 0:
        raise serializers.ValidationError(
            "La duración estimada debe ser mayor a 0."
        )
    return value
```

**Características**:

- Valida que la duración sea positiva si se especifica
- Permite valores None (opcional)
- Validación en nivel de serializer

#### Validación de Formato de Duración

```python
def to_internal_value(self, data):
    """
    Validar formato de duración antes del parsing
    """
    if "duracion_estimada" in data and isinstance(
        data.get("duracion_estimada"), str
    ):
        duracion_str = data["duracion_estimada"]
        if ":" in duracion_str:
            parts = duracion_str.split(":")
            if len(parts) >= 2:
                try:
                    minutes = int(parts[1]) if len(parts) > 1 else 0
                    seconds = int(parts[2]) if len(parts) > 2 else 0
                    if minutes > 59 or seconds > 59:
                        raise serializers.ValidationError({
                            "duracion_estimada": "Formato de duración inválido. Los minutos y segundos deben ser menores a 60."
                        })
                except ValueError:
                    raise serializers.ValidationError({
                        "duracion_estimada": "Formato de duración inválido."
                    })
    return super().to_internal_value(data)
```

**Características**:

- Valida formato de entrada antes del procesamiento
- Acepta formato HH:MM:SS
- Valida rangos de minutos y segundos

### Ejemplo de Uso - Serialización

#### Entrada (Modelo Servicio)

```python
servicio = Servicio.objects.get(pk=1)
serializer = ServicioSerializer(servicio)
```

#### Salida (JSON)

```json
{
  "id": 1,
  "servicio_id": 1,
  "nombre_servicio": "Manicure Básico",
  "precio": "25000.00",
  "precio_formateado": "$25,000.00",
  "descripcion": "Manicure estándar con esmaltado básico",
  "duracion_estimada": "01:00:00",
  "duracion_estimada_horas": "1h 0m",
  "activo": true,
  "categoria": "Manicure",
  "imagen": null,
  "fecha_creacion": "2024-01-15T09:00:00Z",
  "fecha_actualizacion": "2024-01-15T09:00:00Z"
}
```

### Ejemplo de Uso - Deserialización

#### Entrada (JSON)

```json
{
  "nombre_servicio": "Pedicure Premium",
  "precio": "40000.00",
  "descripcion": "Pedicure completo con tratamiento especial",
  "duracion_estimada": "02:00:00",
  "categoria": "Pedicure"
}
```

#### Proceso

```python
serializer = ServicioSerializer(data=datos_json)
if serializer.is_valid():
    servicio = serializer.save()
else:
    print(serializer.errors)
```

---

## ServicioListSerializer

### Propósito

Serializer optimizado para listados de servicios. Incluye menos campos para mejorar la performance en consultas que retornan múltiples registros.

### Definición

```python
class ServicioListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listas de servicios
    """

    # Añadir campo 'id' para compatibilidad con API REST estándar
    id = serializers.IntegerField(source="servicio_id", read_only=True)
    precio_formateado = serializers.SerializerMethodField()
    duracion_estimada_horas = serializers.SerializerMethodField()

    class Meta:
        model = Servicio
        fields = [
            "id",
            "servicio_id",
            "nombre_servicio",
            "precio",
            "precio_formateado",
            "descripcion",
            "duracion_estimada",
            "duracion_estimada_horas",
            "categoria",
            "activo",
        ]
```

### Diferencias con ServicioSerializer

| Aspecto              | ServicioSerializer                   | ServicioListSerializer          |
| -------------------- | ------------------------------------ | ------------------------------- |
| **Campos Incluidos** | 12 campos                            | 10 campos                       |
| **Timestamps**       | Incluye fecha_creacion/actualizacion | No incluye timestamps           |
| **Imagen**           | Incluye campo imagen                 | No incluye imagen               |
| **Validaciones**     | Validaciones completas               | Sin validaciones personalizadas |
| **Uso Principal**    | Detalle, creación, actualización     | Listados optimizados            |
| **Performance**      | Normal                               | Optimizada                      |

### Campos Incluidos

- ✅ Información básica (nombre, precio, descripción)
- ✅ Estado y categoría
- ✅ Duración estimada
- ✅ Campos computados (precio_formateado, duracion_estimada_horas)
- ❌ Timestamps de creación y actualización
- ❌ Campo imagen

---

## Campos Especiales

### Campo ID Dual

```python
id = serializers.IntegerField(source="servicio_id", read_only=True)
```

**Propósito**:

- Proporciona compatibilidad con estándares REST que esperan un campo `id`
- Mantiene `servicio_id` para compatibilidad interna
- Ambos campos apuntan al mismo valor

### Campos Computados

#### Precio Formateado

Proporciona el precio en formato legible con símbolo de moneda y separadores de miles:

- Facilita la presentación en interfaces de usuario
- Mantiene el precio original para cálculos
- Formato consistente en toda la aplicación

#### Duración en Formato Legible

Convierte `timedelta` a formato humano legible:

- `01:30:00` → `"1h 30m"`
- `00:45:00` → `"45m"`
- `null` → `"No especificado"`

---

## Manejo de Errores

### Errores de Validación

#### Estructura de Error

```json
{
  "nombre_servicio": ["Ya existe un servicio con este nombre."],
  "precio": ["El precio debe ser mayor o igual a 0."],
  "duracion_estimada": ["Formato de duración inválido."]
}
```

#### Tipos de Errores Comunes

1. **Campos Requeridos**:

   ```json
   {
     "nombre_servicio": ["Este campo es requerido."],
     "precio": ["Este campo es requerido."]
   }
   ```

2. **Formato Inválido**:

   ```json
   {
     "precio": ["Un número válido es requerido."],
     "duracion_estimada": ["Formato de duración inválido."]
   }
   ```

3. **Unicidad Violada**:

   ```json
   {
     "nombre_servicio": ["Ya existe un servicio con este nombre."]
   }
   ```

4. **Validaciones de Negocio**:
   ```json
   {
     "precio": ["El precio debe ser mayor o igual a 0."],
     "duracion_estimada": ["La duración estimada debe ser mayor a 0."]
   }
   ```

---

## Optimizaciones de Performance

### Selección de Serializer

```python
def get_serializer_class(self):
    """En ServicioViewSet"""
    if self.action == "list":
        return ServicioListSerializer  # Menos campos = más rápido
    return ServicioSerializer
```

### Campos Computados Eficientes

Los métodos `get_precio_formateado` y `get_duracion_estimada_horas` son eficientes porque:

- No realizan consultas adicionales a la base de datos
- Utilizan solo datos ya cargados en memoria
- Formatean datos de manera simple

---

## Extensibilidad

### Agregando Validaciones Personalizadas

```python
def validate(self, attrs):
    """
    Validación a nivel de objeto
    """
    # Validación cruzada de campos
    if attrs.get('precio', 0) > 100000 and not attrs.get('descripcion'):
        raise serializers.ValidationError(
            "Servicios premium (>$100,000) requieren descripción detallada."
        )

    return attrs
```

### Campos Computados Adicionales

```python
class ServicioSerializer(serializers.ModelSerializer):
    # ... campos existentes ...

    precio_usd = serializers.SerializerMethodField()
    popularidad = serializers.SerializerMethodField()

    def get_precio_usd(self, obj):
        # Conversión a USD (tasa del día)
        tasa_cambio = 4000  # Ejemplo
        return round(float(obj.precio) / tasa_cambio, 2)

    def get_popularidad(self, obj):
        # Calcular popularidad basada en uso
        return obj.detalle_citas.count() if hasattr(obj, 'detalle_citas') else 0
```

---

## Testing de Serializers

### Tests de Validación

```python
def test_serializer_validacion_nombre_unico(self):
    # Crear servicio existente
    Servicio.objects.create(
        nombre_servicio="Manicure Test",
        precio=25000
    )

    # Intentar crear otro con mismo nombre
    data = {
        "nombre_servicio": "Manicure Test",
        "precio": 30000
    }

    serializer = ServicioSerializer(data=data)
    self.assertFalse(serializer.is_valid())
    self.assertIn("nombre_servicio", serializer.errors)
```

### Tests de Serialización

```python
def test_serializer_campos_computados(self):
    servicio = ServicioFactory(
        precio=25000,
        duracion_estimada=timedelta(minutes=90)
    )
    serializer = ServicioSerializer(servicio)

    self.assertEqual(serializer.data["precio_formateado"], "$25,000.00")
    self.assertEqual(serializer.data["duracion_estimada_horas"], "1h 30m")
```

---

## Configuración Global

### Settings para Serializers

```python
# En settings.py
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%SZ',
    'TIME_FORMAT': '%H:%M:%S',
    'USE_TZ': True,
}
```

### Localización

```python
# Para mensajes en español
LANGUAGE_CODE = 'es-es'
USE_I18N = True
USE_L10N = True
```

---

## Mejores Prácticas

### 1. Separación de Responsabilidades

- **ServicioSerializer**: CRUD completo con validaciones
- **ServicioListSerializer**: Listados optimizados

### 2. Validaciones Consistentes

- Validaciones de formato en el serializer
- Validaciones de negocio en el modelo o vista
- Mensajes de error en español y descriptivos

### 3. Performance

- Usar `ServicioListSerializer` para listados
- Evitar consultas N+1 en campos computados
- Caché para conversiones costosas

### 4. Compatibilidad

- Campo `id` para estándares REST
- Mantener `servicio_id` para compatibilidad interna
- Campos de solo lectura apropiados

### 5. Usabilidad

- Campos formateados para presentación
- Validaciones tempranas y claras
- Documentación de formatos aceptados
