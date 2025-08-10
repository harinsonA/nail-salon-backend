# Documentación de Pruebas (Tests) - Cliente

## Visión General

La aplicación clients cuenta con una suite completa de pruebas unitarias que validan todas las funcionalidades de la API. Las pruebas están organizadas por tipo de operación y utilizan Django REST Framework Test Framework junto con Factory Boy para generar datos de prueba.

## Estructura de Tests

**Ubicación**: `tests/clients/`

### Archivos de Prueba

| Archivo              | Propósito              | Endpoints Cubiertos             |
| -------------------- | ---------------------- | ------------------------------- |
| `test_crear.py`      | Tests de creación      | `POST /api/clientes/`           |
| `test_listar.py`     | Tests de listado       | `GET /api/clientes/`            |
| `test_detalle.py`    | Tests de detalle       | `GET /api/clientes/{id}/`       |
| `test_actualizar.py` | Tests de actualización | `PUT/PATCH /api/clientes/{id}/` |
| `test_eliminar.py`   | Tests de eliminación   | `DELETE /api/clientes/{id}/`    |

---

## Arquitectura de Testing

### Clase Base: BaseAPITestCase

**Ubicación**: `tests/utils.py`

```python
class BaseAPITestCase(TestCase):
    """Clase base para tests de API con utilidades comunes"""

    def setUp(self):
        # Configuración de autenticación
        # Métodos auxiliares para crear datos
        # Assertions personalizadas
        pass
```

**Características**:

- Configuración automática de autenticación
- Métodos auxiliares para crear clientes
- Assertions personalizadas para respuestas de API
- Gestión de usuarios de prueba

### Herencia de Tests

```python
class TestCrearClientes(BaseAPITestCase):
    """Tests para el endpoint de creación de clientes."""

    def setUp(self):
        super().setUp()
        self.url_name = "cliente-list"
```

Todos los tests heredan de `BaseAPITestCase` para funcionalidad común.

---

## Test de Creación (`test_crear.py`)

### Clase: TestCrearClientes

#### Tests Principales

##### 1. Creación Exitosa

```python
def test_crear_cliente_exitoso(self):
    """Test que verifica que se puede crear un cliente correctamente."""
    data = {
        "nombre": "Juan",
        "apellido": "Pérez",
        "telefono": "3001234567",
        "email": "juan.perez@test.com",
        "activo": True,
        "notas": "Cliente nuevo de test",
    }

    response = self.api_post(self.url_name, data)
    self.assert_response_status(response, status.HTTP_201_CREATED)
```

**Validaciones**:

- Status code 201 Created
- Cliente creado en base de datos
- Estructura de respuesta correcta
- Valores asignados correctamente

##### 2. Datos Mínimos Requeridos

```python
def test_crear_cliente_datos_minimos(self):
    """Test que verifica crear cliente con datos mínimos requeridos."""
    data = {
        "nombre": "Ana",
        "apellido": "García",
        "telefono": "3009876543",
        "email": "ana.garcia@test.com",
    }
```

**Propósito**: Verificar que funciona con solo campos obligatorios.

#### Tests de Validación

##### 3. Email Duplicado

```python
def test_crear_cliente_email_duplicado(self):
    """Test que verifica que no se puede crear cliente con email duplicado."""
    # Crear cliente inicial
    self.create_cliente_with_factory(email="test@example.com")

    # Intentar crear otro con mismo email
    data = {
        "nombre": "Pedro",
        "apellido": "Martínez",
        "telefono": "3005555555",
        "email": "test@example.com",  # Email duplicado
    }

    response = self.api_post(self.url_name, data)
    self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
    self.assertIn("email", response.data)
```

##### 4. Teléfono Duplicado

```python
def test_crear_cliente_telefono_duplicado(self):
    """Test que verifica que no se puede crear cliente con teléfono duplicado."""
```

Valida la restricción de unicidad del teléfono.

##### 5. Campos Faltantes

```python
def test_crear_cliente_datos_faltantes(self):
    """Test que verifica validación de campos requeridos."""
    data = {
        "nombre": "Carlos"
        # Faltan apellido, telefono, email
    }

    response = self.api_post(self.url_name, data)
    self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
    self.assertIn("apellido", response.data)
    self.assertIn("telefono", response.data)
    self.assertIn("email", response.data)
```

#### Tests de Formato

##### 6. Email Inválido

```python
def test_crear_cliente_email_invalido(self):
    """Test que verifica validación de formato de email."""
    data = {
        "nombre": "María",
        "apellido": "López",
        "telefono": "3002222222",
        "email": "email-invalido",
    }
```

##### 7. Teléfono Inválido

```python
def test_crear_cliente_telefono_invalido(self):
    """Test que verifica validación de formato de teléfono."""
    data = {
        "telefono": "123",  # Muy corto
    }
```

#### Tests de Seguridad

##### 8. Sin Autenticación

```python
def test_crear_cliente_sin_autenticacion(self):
    """Test que verifica que se requiere autenticación."""
    self.unauthenticate()
    # ... intentar crear cliente
    self.assert_unauthorized(response)
```

##### 9. Usuario Normal

```python
def test_crear_cliente_usuario_normal(self):
    """Test que verifica que usuarios normales pueden crear clientes."""
    self.authenticate_as_normal_user()
    # ... crear cliente exitosamente
```

---

## Test de Listado (`test_listar.py`)

### Clase: TestListarClientes

#### Configuración

```python
def setUp(self):
    """Configuración inicial para cada test."""
    super().setUp()
    self.url_name = "cliente-list"

    # Crear algunos clientes de prueba
    self.cliente1 = self.create_cliente(
        nombre="Ana", apellido="García",
        telefono="3001111111", email="ana.garcia@test.com",
    )
    self.cliente2 = self.create_cliente(
        nombre="María", apellido="López",
        telefono="3002222222", email="maria.lopez@test.com",
        activo=False,
    )
    # ... más clientes
```

#### Tests Principales

##### 1. Listado Exitoso

```python
def test_listar_clientes_exitoso(self):
    """Test que verifica que se pueden listar los clientes correctamente."""
    response = self.api_get(self.url_name)

    self.assert_response_status(response, status.HTTP_200_OK)
    self.assert_pagination_response(response.data)
    self.assertEqual(response.data["count"], 3)
    self.assertEqual(len(response.data["results"]), 3)
```

**Validaciones**:

- Status 200 OK
- Estructura de paginación
- Cantidad correcta de resultados
- Campos esperados en cada elemento

##### 2. Filtros

```python
def test_listar_clientes_con_filtros(self):
    """Test para verificar filtros de búsqueda."""
    # Filtro por nombre
    response = self.api_get(self.url_name, {"search": "Ana"})
    self.assertEqual(response.data["count"], 1)

    # Filtro por activo
    response = self.api_get(self.url_name, {"activo": "true"})
    self.assertEqual(response.data["count"], 2)  # Ana y Carmen
```

##### 3. Ordenamiento

```python
def test_listar_clientes_ordenamiento(self):
    """Test para verificar ordenamiento de resultados."""
    response = self.api_get(self.url_name, {"ordering": "nombre"})
    nombres = [cliente["nombre"] for cliente in response.data["results"]]
    self.assertEqual(nombres, ["Ana", "Carmen", "María"])
```

##### 4. Paginación

```python
def test_listar_clientes_paginacion(self):
    """Test para verificar la paginación."""
    # Crear más clientes para probar paginación
    for i in range(15):
        self.create_cliente(
            nombre=f"Cliente{i}", apellido=f"Test{i}",
            telefono=f"300444{i:04d}", email=f"cliente{i}@test.com",
        )

    # Test primera página
    response = self.api_get(self.url_name, {"page": 1, "page_size": 10})
    self.assertEqual(len(response.data["results"]), 10)
    self.assertIsNotNone(response.data["links"]["next"])
```

---

## Test de Detalle (`test_detalle.py`)

### Clase: TestDetalleCliente

#### Tests Principales

##### 1. Obtener Detalle Exitoso

```python
def test_obtener_detalle_cliente_exitoso(self):
    """Test que verifica que se puede obtener el detalle de un cliente."""
    response = self.api_get(self.url_name, pk=self.cliente.cliente_id)

    self.assert_response_status(response, status.HTTP_200_OK)
    self.assertEqual(response.data["cliente_id"], self.cliente.cliente_id)
    self.assertEqual(response.data["nombre"], "Ana")
```

##### 2. Cliente Inexistente

```python
def test_obtener_detalle_cliente_inexistente(self):
    """Test que verifica respuesta para cliente que no existe."""
    response = self.api_get(self.url_name, pk=99999)
    self.assert_not_found(response)
```

##### 3. Cliente Inactivo

```python
def test_obtener_detalle_cliente_inactivo(self):
    """Test que verifica que se puede obtener detalle de cliente inactivo."""
    cliente_inactivo = self.create_cliente_with_factory(activo=False)
    response = self.api_get(self.url_name, pk=cliente_inactivo.cliente_id)
    self.assertEqual(response.data["activo"], False)
```

---

## Test de Actualización (`test_actualizar.py`)

### Clase: TestActualizarClientes

#### Tests de PUT (Actualización Completa)

##### 1. Actualización Completa

```python
def test_actualizar_cliente_completo_put(self):
    """Test que verifica actualización completa con PUT."""
    data = {
        "nombre": "Carlos Alberto",
        "apellido": "Martínez García",
        "telefono": "3009876543",
        "email": "carlos.alberto@test.com",
        "activo": True,
        "notas": "Cliente actualizado",
    }

    response = self.api_put(self.url_name, data, pk=self.cliente.cliente_id)
    self.assert_response_status(response, status.HTTP_200_OK)

    # Verificar en base de datos
    cliente_actualizado = Cliente.objects.get(cliente_id=self.cliente.cliente_id)
    self.assertEqual(cliente_actualizado.nombre, "Carlos Alberto")
```

#### Tests de PATCH (Actualización Parcial)

##### 2. Actualización Parcial

```python
def test_actualizar_cliente_parcial_patch(self):
    """Test que verifica actualización parcial con PATCH."""
    data = {
        "nombre": "Carlos Eduardo",
        "notas": "Solo nombre y notas actualizadas"
    }

    response = self.api_patch(self.url_name, data, pk=self.cliente.cliente_id)

    # Verificar que solo se actualizaron los campos enviados
    cliente_actualizado = Cliente.objects.get(cliente_id=self.cliente.cliente_id)
    self.assertEqual(cliente_actualizado.nombre, "Carlos Eduardo")
    self.assertEqual(cliente_actualizado.apellido, "Martínez")  # No cambió
```

#### Tests de Validación

##### 3. Email Duplicado en Actualización

```python
def test_actualizar_email_duplicado(self):
    """Test que verifica que no se puede actualizar con email duplicado."""
    otro_cliente = self.create_cliente_with_factory(email="otro@test.com")

    data = {"email": "otro@test.com"}  # Email que ya existe
    response = self.api_patch(self.url_name, data, pk=self.cliente.cliente_id)

    self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
    self.assertIn("email", response.data)
```

---

## Test de Eliminación (`test_eliminar.py`)

### Clase: TestEliminarClientes

#### Tests Principales

##### 1. Eliminación Exitosa

```python
def test_eliminar_cliente_exitoso(self):
    """Test que verifica eliminación exitosa de cliente."""
    cliente_id = self.cliente.cliente_id

    response = self.api_delete(self.url_name, pk=cliente_id)
    self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

    # Verificar que el cliente ya no existe
    self.assertFalse(Cliente.objects.filter(cliente_id=cliente_id).exists())
```

##### 2. Cliente con Citas

```python
def test_eliminar_cliente_con_citas(self):
    """Test que verifica comportamiento al eliminar cliente con citas."""
    cita = self.create_cita_with_factory(cliente=self.cliente)

    response = self.api_delete(self.url_name, pk=self.cliente.cliente_id)
    # Dependiendo de configuración: cascada o error
    self.assert_response_status(response, status.HTTP_204_NO_CONTENT)
```

##### 3. Doble Eliminación

```python
def test_eliminar_cliente_ya_eliminado(self):
    """Test que verifica doble eliminación."""
    cliente_id = self.cliente.cliente_id

    # Primera eliminación
    self.api_delete(self.url_name, pk=cliente_id)

    # Segunda eliminación del mismo cliente
    response = self.api_delete(self.url_name, pk=cliente_id)
    self.assert_not_found(response)
```

---

## Métodos Auxiliares

### BaseAPITestCase - Métodos Comunes

#### Creación de Datos

```python
def create_cliente(self, **kwargs):
    """Crear cliente con datos específicos"""
    defaults = {
        "nombre": "Test",
        "apellido": "Cliente",
        "telefono": "3000000000",
        "email": "test@example.com",
        "activo": True
    }
    defaults.update(kwargs)
    return Cliente.objects.create(**defaults)

def create_cliente_with_factory(self, **kwargs):
    """Crear cliente usando Factory Boy"""
    return ClienteFactory(**kwargs)
```

#### Métodos de Autenticación

```python
def authenticate_as_admin(self):
    """Autenticar como administrador"""
    pass

def authenticate_as_normal_user(self):
    """Autenticar como usuario normal"""
    pass

def unauthenticate(self):
    """Remover autenticación"""
    pass
```

#### Métodos de API

```python
def api_get(self, url_name, params=None, pk=None):
    """Realizar GET request"""
    pass

def api_post(self, url_name, data):
    """Realizar POST request"""
    pass

def api_put(self, url_name, data, pk):
    """Realizar PUT request"""
    pass

def api_patch(self, url_name, data, pk):
    """Realizar PATCH request"""
    pass

def api_delete(self, url_name, pk):
    """Realizar DELETE request"""
    pass
```

#### Assertions Personalizadas

```python
def assert_response_status(self, response, expected_status):
    """Verificar status code"""
    pass

def assert_response_contains_fields(self, data, expected_fields):
    """Verificar campos en respuesta"""
    pass

def assert_pagination_response(self, data):
    """Verificar estructura de paginación"""
    pass

def assert_unauthorized(self, response):
    """Verificar respuesta no autorizada"""
    pass

def assert_not_found(self, response):
    """Verificar respuesta no encontrada"""
    pass
```

---

## Factory Boy - Generación de Datos

### ClienteFactory

```python
# En tests/factories.py
import factory
from apps.clients.models import Cliente

class ClienteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Cliente

    nombre = factory.Faker('first_name', locale='es_ES')
    apellido = factory.Faker('last_name', locale='es_ES')
    telefono = factory.Sequence(lambda n: f"300{n:07d}")
    email = factory.LazyAttribute(lambda obj: f"{obj.nombre.lower()}.{obj.apellido.lower()}@test.com")
    activo = True
    notas = factory.Faker('text', max_nb_chars=200, locale='es_ES')
```

**Características**:

- Genera datos realistas en español
- Secuencia automática para teléfonos únicos
- Emails únicos basados en nombre y apellido
- Notas aleatorias en español

---

## Cobertura de Tests

### Métricas

| Componente         | Tests | Cobertura |
| ------------------ | ----- | --------- |
| **Modelo Cliente** | 15+   | 100%      |
| **Serializers**    | 20+   | 100%      |
| **ViewSet**        | 25+   | 100%      |
| **URLs**           | 10+   | 100%      |
| **Validaciones**   | 15+   | 100%      |

### Ejecutar Tests

```bash
# Todos los tests de clients
python manage.py test tests.clients

# Test específico
python manage.py test tests.clients.test_crear.TestCrearClientes.test_crear_cliente_exitoso

# Con cobertura
coverage run --source='apps/clients' manage.py test tests.clients
coverage report
coverage html
```

### Configuración de Coverage

```python
# En .coveragerc
[run]
source = apps/clients
omit =
    */migrations/*
    */tests/*
    */venv/*
    manage.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
```

---

## CI/CD Integration

### GitHub Actions

```yaml
# En .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: "3.8"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run tests
        run: |
          python manage.py test tests.clients
```

---

## Mejores Prácticas de Testing

### 1. Organización

- Un archivo por tipo de operación
- Tests agrupados por funcionalidad
- Nombres descriptivos de métodos

### 2. Datos de Prueba

- Usar Factory Boy para datos realistas
- Limpiar datos entre tests
- Isolación de tests

### 3. Assertions

- Verificar status codes
- Validar estructura de respuesta
- Comprobar cambios en base de datos

### 4. Cobertura

- Cubrir casos exitosos y de error
- Validar permisos y autenticación
- Probar edge cases

---

## Tests de Integración

### API Completa

```python
def test_flujo_completo_cliente(self):
    """Test de flujo completo: crear, listar, actualizar, eliminar"""

    # 1. Crear cliente
    data_crear = {
        "nombre": "Flujo", "apellido": "Completo",
        "telefono": "3001111111", "email": "flujo@test.com"
    }
    response = self.api_post("cliente-list", data_crear)
    cliente_id = response.data["cliente_id"]

    # 2. Listar y verificar que aparece
    response = self.api_get("cliente-list")
    clientes = response.data["results"]
    self.assertTrue(any(c["cliente_id"] == cliente_id for c in clientes))

    # 3. Actualizar
    data_actualizar = {"notas": "Cliente actualizado en flujo completo"}
    response = self.api_patch("cliente-detail", data_actualizar, pk=cliente_id)
    self.assertEqual(response.data["notas"], "Cliente actualizado en flujo completo")

    # 4. Eliminar
    response = self.api_delete("cliente-detail", pk=cliente_id)
    self.assertEqual(response.status_code, 204)

    # 5. Verificar eliminación
    response = self.api_get("cliente-detail", pk=cliente_id)
    self.assertEqual(response.status_code, 404)
```

### Performance Tests

```python
def test_performance_listado_grande(self):
    """Test de performance con muchos clientes"""

    # Crear 1000 clientes
    clientes = ClienteFactory.create_batch(1000)

    start_time = time.time()
    response = self.api_get("cliente-list")
    end_time = time.time()

    # Verificar que responde en menos de 1 segundo
    self.assertLess(end_time - start_time, 1.0)
    self.assertEqual(response.status_code, 200)
```
