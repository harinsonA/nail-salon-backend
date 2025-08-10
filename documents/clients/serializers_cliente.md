# Documentación de Serializers - Cliente

## Visión General

Los serializers son el componente clave que convierte entre objetos Python (modelos Django) y formatos de datos como JSON. La aplicación clients utiliza dos serializers especializados para diferentes casos de uso, optimizando así la transferencia de datos y la experiencia del usuario.

## Archivo Principal

**Ubicación**: `apps/clients/serializers/cliente_serializer.py`

## Serializers Disponibles

### 1. ClienteSerializer (Completo)

### 2. ClienteListSerializer (Simplificado)

---

## ClienteSerializer

### Propósito

Serializer principal para operaciones CRUD completas. Incluye todos los campos del modelo y validaciones personalizadas.

### Definición

```python
class ClienteSerializer(serializers.ModelViewSet):
    """
    Serializer para el modelo Cliente
    """

    # Añadir campo 'id' para compatibilidad con API REST estándar
    id = serializers.IntegerField(source="cliente_id", read_only=True)
    # Añadir campo nombre_completo como propiedad
    nombre_completo = serializers.ReadOnlyField()

    class Meta:
        model = Cliente
        fields = [
            "id",
            "cliente_id",
            "nombre",
            "apellido",
            "nombre_completo",
            "telefono",
            "email",
            "fecha_registro",
            "activo",
            "notas",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "cliente_id",
            "nombre_completo",
            "fecha_registro",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
```

### Campos del Serializer

#### Campos de Solo Lectura

| Campo                 | Tipo          | Fuente       | Descripción                    |
| --------------------- | ------------- | ------------ | ------------------------------ |
| `id`                  | IntegerField  | `cliente_id` | Alias REST estándar para el ID |
| `cliente_id`          | AutoField     | Modelo       | ID primario original           |
| `nombre_completo`     | ReadOnlyField | Propiedad    | Nombre + apellido concatenado  |
| `fecha_registro`      | DateField     | Modelo       | Fecha de registro (auto)       |
| `fecha_creacion`      | DateTimeField | Modelo       | Timestamp creación (auto)      |
| `fecha_actualizacion` | DateTimeField | Modelo       | Timestamp actualización (auto) |

#### Campos Editables

| Campo      | Tipo         | Validaciones                    | Descripción          |
| ---------- | ------------ | ------------------------------- | -------------------- |
| `nombre`   | CharField    | Requerido, max 100 chars        | Nombre del cliente   |
| `apellido` | CharField    | Requerido, max 100 chars        | Apellido del cliente |
| `telefono` | CharField    | Requerido, único, formato       | Número telefónico    |
| `email`    | EmailField   | Requerido, único, formato email | Correo electrónico   |
| `activo`   | BooleanField | Opcional, default True          | Estado del cliente   |
| `notas`    | TextField    | Opcional, puede ser nulo        | Notas adicionales    |

### Validaciones Personalizadas

#### Validación de Email

```python
def validate_email(self, value):
    """
    Validar que el email sea único
    """
    if Cliente.objects.filter(email=value).exists():
        if self.instance and self.instance.email == value:
            return value
        raise serializers.ValidationError("Ya existe un cliente con este email.")
    return value
```

**Características**:

- Verifica unicidad del email
- Permite mantener el mismo email en actualizaciones
- Mensaje de error personalizado en español

#### Validación de Teléfono

```python
def validate_telefono(self, value):
    """
    Validar formato del teléfono
    """
    if not value.replace("+", "").replace("-", "").replace(" ", "").isdigit():
        raise serializers.ValidationError(
            "El teléfono debe contener solo números, espacios, guiones o el símbolo +."
        )
    return value
```

**Características**:

- Permite números, espacios, guiones y símbolo +
- Remueve caracteres especiales para validación
- Formato flexible para diferentes tipos de números

### Ejemplo de Uso - Serialización

#### Entrada (Modelo Cliente)

```python
cliente = Cliente.objects.get(pk=1)
serializer = ClienteSerializer(cliente)
```

#### Salida (JSON)

```json
{
  "id": 1,
  "cliente_id": 1,
  "nombre": "Juan",
  "apellido": "Pérez",
  "nombre_completo": "Juan Pérez",
  "telefono": "3001234567",
  "email": "juan.perez@email.com",
  "fecha_registro": "2024-01-15",
  "activo": true,
  "notas": "Cliente frecuente",
  "fecha_creacion": "2024-01-15T09:00:00Z",
  "fecha_actualizacion": "2024-01-15T09:00:00Z"
}
```

### Ejemplo de Uso - Deserialización

#### Entrada (JSON)

```json
{
  "nombre": "María",
  "apellido": "García",
  "telefono": "3009876543",
  "email": "maria@email.com",
  "notas": "Cliente nueva"
}
```

#### Proceso

```python
serializer = ClienteSerializer(data=datos_json)
if serializer.is_valid():
    cliente = serializer.save()
else:
    print(serializer.errors)
```

---

## ClienteListSerializer

### Propósito

Serializer optimizado para listados de clientes. Incluye menos campos para mejorar la performance en consultas que retornan múltiples registros.

### Definición

```python
class ClienteListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listas de clientes
    """

    # Añadir campo 'id' para compatibilidad con API REST estándar
    id = serializers.IntegerField(source="cliente_id", read_only=True)
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = Cliente
        fields = [
            "id",
            "cliente_id",
            "nombre",
            "apellido",
            "nombre_completo",
            "telefono",
            "email",
            "fecha_registro",
            "activo",
            "notas",
        ]

    def get_nombre_completo(self, obj):
        return f"{obj.nombre} {obj.apellido}"
```

### Diferencias con ClienteSerializer

| Aspecto              | ClienteSerializer                    | ClienteListSerializer          |
| -------------------- | ------------------------------------ | ------------------------------ |
| **Campos Incluidos** | 11 campos                            | 10 campos                      |
| **Timestamps**       | Incluye fecha_creacion/actualizacion | No incluye timestamps          |
| **Uso Principal**    | Detalle, creación, actualización     | Listados optimizados           |
| **Performance**      | Normal                               | Optimizada                     |
| **Nombre Completo**  | ReadOnlyField (propiedad)            | SerializerMethodField (método) |

### Campos Incluidos

- ✅ Información básica (nombre, apellido, teléfono, email)
- ✅ Estado y fecha de registro
- ✅ Notas
- ❌ Timestamps de creación y actualización

### Método Personalizado

```python
def get_nombre_completo(self, obj):
    return f"{obj.nombre} {obj.apellido}"
```

**Propósito**: Genera el nombre completo usando un método en lugar de una propiedad del modelo.

---

## Campos Especiales

### Campo ID Dual

```python
id = serializers.IntegerField(source="cliente_id", read_only=True)
```

**Propósito**:

- Proporciona compatibilidad con estándares REST que esperan un campo `id`
- Mantiene `cliente_id` para compatibilidad interna
- Ambos campos apuntan al mismo valor

### Campo Nombre Completo

#### En ClienteSerializer

```python
nombre_completo = serializers.ReadOnlyField()
```

Utiliza la propiedad `nombre_completo` del modelo.

#### En ClienteListSerializer

```python
nombre_completo = serializers.SerializerMethodField()

def get_nombre_completo(self, obj):
    return f"{obj.nombre} {obj.apellido}"
```

Calcula el nombre completo en el serializer.

---

## Validaciones Avanzadas

### Validación de Unicidad

#### Email Único

```python
def validate_email(self, value):
    queryset = Cliente.objects.filter(email=value)

    # En actualización, excluir el objeto actual
    if self.instance:
        queryset = queryset.exclude(pk=self.instance.pk)

    if queryset.exists():
        raise serializers.ValidationError(
            "Ya existe un cliente con este email."
        )
    return value
```

#### Teléfono Único (Nivel Modelo)

La unicidad del teléfono se maneja a nivel del modelo Django:

```python
telefono = models.CharField(max_length=20, unique=True)
```

### Validación de Formato

#### Teléfono

```python
def validate_telefono(self, value):
    # Remover caracteres permitidos para validación
    clean_value = value.replace("+", "").replace("-", "").replace(" ", "")

    if not clean_value.isdigit():
        raise serializers.ValidationError(
            "El teléfono debe contener solo números, espacios, guiones o el símbolo +."
        )

    # Validación adicional de longitud
    if len(clean_value) < 7:
        raise serializers.ValidationError(
            "El teléfono debe tener al menos 7 dígitos."
        )

    return value
```

---

## Manejo de Errores

### Errores de Validación

#### Estructura de Error

```json
{
  "email": ["Ya existe un cliente con este email."],
  "telefono": [
    "El teléfono debe contener solo números, espacios, guiones o el símbolo +."
  ],
  "nombre": ["Este campo es requerido."]
}
```

#### Tipos de Errores Comunes

1. **Campos Requeridos**:

   ```json
   {
     "nombre": ["Este campo es requerido."]
   }
   ```

2. **Formato Inválido**:

   ```json
   {
     "email": ["Introduzca una dirección de correo electrónico válida."]
   }
   ```

3. **Unicidad Violada**:

   ```json
   {
     "email": ["Ya existe un cliente con este email."]
   }
   ```

4. **Longitud Excedida**:
   ```json
   {
     "nombre": ["Asegúrese de que este campo no tenga más de 100 caracteres."]
   }
   ```

---

## Optimizaciones de Performance

### Selección de Serializer

```python
def get_serializer_class(self):
    """En ClienteViewSet"""
    if self.action == "list":
        return ClienteListSerializer  # Menos campos = más rápido
    return ClienteSerializer
```

### Caché de Propiedades

Para optimizar el campo `nombre_completo`:

```python
# En el modelo Cliente
@cached_property
def nombre_completo(self):
    return f"{self.nombre} {self.apellido}"
```

---

## Extensibilidad

### Agregando Validaciones Personalizadas

```python
def validate(self, attrs):
    """
    Validación a nivel de objeto
    """
    # Validación cruzada de campos
    if attrs.get('activo') is False and attrs.get('notas'):
        if 'motivo' not in attrs.get('notas', '').lower():
            raise serializers.ValidationError(
                "Para desactivar un cliente, debe incluir el motivo en las notas."
            )

    return attrs
```

### Campos Computados Adicionales

```python
class ClienteSerializer(serializers.ModelSerializer):
    # ... campos existentes ...

    antiguedad_dias = serializers.SerializerMethodField()
    total_citas = serializers.SerializerMethodField()

    def get_antiguedad_dias(self, obj):
        from django.utils import timezone
        return (timezone.now().date() - obj.fecha_registro).days

    def get_total_citas(self, obj):
        # Requerirá relación con modelo Citas
        return obj.citas.count() if hasattr(obj, 'citas') else 0
```

---

## Casos de Uso

### 1. Creación de Cliente

```python
# Vista
data = request.data
serializer = ClienteSerializer(data=data)
if serializer.is_valid():
    cliente = serializer.save()
    return Response(serializer.data, status=201)
return Response(serializer.errors, status=400)
```

### 2. Actualización Parcial

```python
# Vista
cliente = get_object_or_404(Cliente, pk=pk)
serializer = ClienteSerializer(cliente, data=request.data, partial=True)
if serializer.is_valid():
    cliente = serializer.save()
    return Response(serializer.data)
return Response(serializer.errors, status=400)
```

### 3. Listado Optimizado

```python
# Vista
queryset = Cliente.objects.filter(activo=True)
serializer = ClienteListSerializer(queryset, many=True)
return Response(serializer.data)
```

---

## Testing de Serializers

### Tests de Validación

```python
def test_serializer_validacion_email_unico(self):
    # Crear cliente existente
    Cliente.objects.create(
        nombre="Juan", apellido="Pérez",
        email="juan@test.com", telefono="3001111111"
    )

    # Intentar crear otro con mismo email
    data = {
        "nombre": "Pedro", "apellido": "García",
        "email": "juan@test.com", "telefono": "3002222222"
    }

    serializer = ClienteSerializer(data=data)
    self.assertFalse(serializer.is_valid())
    self.assertIn("email", serializer.errors)
```

### Tests de Serialización

```python
def test_serializer_campos_incluidos(self):
    cliente = ClienteFactory()
    serializer = ClienteSerializer(cliente)

    expected_fields = [
        "id", "cliente_id", "nombre", "apellido",
        "nombre_completo", "telefono", "email",
        "fecha_registro", "activo", "notas",
        "fecha_creacion", "fecha_actualizacion"
    ]

    self.assertEqual(set(serializer.data.keys()), set(expected_fields))
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
    'DATE_FORMAT': '%Y-%m-%d',
    'USE_TZ': True,
}
```

### Localización

```python
# Para mensajes en español
LANGUAGE_CODE = 'es-es'
USE_I18N = True
```

---

## Mejores Prácticas

### 1. Separación de Responsabilidades

- **ClienteSerializer**: CRUD completo
- **ClienteListSerializer**: Listados optimizados

### 2. Validaciones Consistentes

- Validaciones de formato en el serializer
- Validaciones de negocio en el modelo o vista
- Mensajes de error en español

### 3. Performance

- Usar `ClienteListSerializer` para listados
- Evitar campos pesados en listados
- Caché para propiedades calculadas

### 4. Compatibilidad

- Campo `id` para estándares REST
- Mantener `cliente_id` para compatibilidad interna
- Campos de solo lectura apropiados
