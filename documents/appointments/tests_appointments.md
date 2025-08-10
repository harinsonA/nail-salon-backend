# Documentación de Pruebas (Tests) - Appointments

## Visión General

La aplicación appointments cuenta con una suite completa de pruebas unitarias que validan todas las funcionalidades de la API. Las pruebas están organizadas por tipo de operación y utilizan Django REST Framework Test Framework junto con Factory Boy para generar datos de prueba realistas para citas y servicios.

## Estructura de Tests

**Ubicación**: `tests/appointments/`

### Archivos de Prueba

| Archivo                    | Propósito                  | Endpoints Cubiertos          |
| -------------------------- | -------------------------- | ---------------------------- |
| `test_crear_citas.py`      | Tests de creación de citas | `POST /api/citas/`           |
| `test_listar_citas.py`     | Tests de listado de citas  | `GET /api/citas/`            |
| `test_detalle_citas.py`    | Tests de detalle de citas  | `GET /api/citas/{id}/`       |
| `test_actualizar_citas.py` | Tests de actualización     | `PUT/PATCH /api/citas/{id}/` |
| `test_eliminar_citas.py`   | Tests de eliminación       | `DELETE /api/citas/{id}/`    |

### Cobertura de Tests

**Total de Tests**: 79
**Distribución**:

- **Crear Citas**: 14 tests
- **Listar Citas**: 19 tests
- **Detalle Citas**: 8 tests
- **Actualizar Citas**: 18 tests
- **Eliminar Citas**: 20 tests

---

## Arquitectura de Testing

### Clase Base: BaseAPITestCase

**Ubicación**: `tests/utils.py`

```python
class BaseAPITestCase(TestCase):
    """Clase base para tests de API con utilidades comunes"""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
```

**Características**:

- Configuración automática de autenticación
- Factory para generar requests
- Cliente autenticado para pruebas
- Métodos auxiliares para crear datos de prueba
- Assertions personalizadas para respuestas de API

### Herencia de Tests

```python
class TestCrearCitas(BaseAPITestCase):
    """Tests para el endpoint de creación de citas."""

    def setUp(self):
        super().setUp()
        self.url_name = "cita-list"
        self.url = reverse(self.url_name)

        # Crear datos base para tests
        self.cliente = ClienteFactory()
        self.servicio = ServicioFactory()
```

Todos los tests heredan de `BaseAPITestCase` para funcionalidad común.

---

## Test de Creación (`test_crear_citas.py`)

### Clase: TestCrearCitas

#### Tests Principales

##### 1. Creación Exitosa

```python
def test_crear_cita_exitosa(self):
    """Test que verifica que se puede crear una cita correctamente."""
    data = {
        "cliente_id": self.cliente.cliente_id,
        "fecha_cita": "2024-12-31T15:00:00Z",
        "observaciones": "Cita para manicure y pedicure"
    }

    response = self.client.post(self.url, data)

    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    self.assertEqual(Cita.objects.count(), 1)

    cita = Cita.objects.first()
    self.assertEqual(cita.cliente, self.cliente)
    self.assertEqual(cita.estado, "programada")
    self.assertEqual(cita.observaciones, data["observaciones"])
```

##### 2. Validación de Cliente Inexistente

```python
def test_crear_cita_cliente_inexistente(self):
    """Test que verifica que no se puede crear una cita con cliente inexistente."""
    data = {
        "cliente_id": 99999,
        "fecha_cita": "2024-12-31T15:00:00Z",
        "observaciones": "Test"
    }

    response = self.client.post(self.url, data)

    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertIn("cliente_id", response.data)
    self.assertEqual(Cita.objects.count(), 0)
```

##### 3. Validación de Cliente Inactivo

```python
def test_crear_cita_cliente_inactivo(self):
    """Test que verifica que no se puede crear cita para cliente inactivo."""
    cliente_inactivo = ClienteFactory(activo=False)

    data = {
        "cliente_id": cliente_inactivo.cliente_id,
        "fecha_cita": "2024-12-31T15:00:00Z",
        "observaciones": "Test"
    }

    response = self.client.post(self.url, data)

    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertIn("cliente_id", response.data)
```

##### 4. Validación de Fecha Pasada

```python
def test_crear_cita_fecha_pasada(self):
    """Test que verifica que no se puede crear cita con fecha pasada."""
    fecha_pasada = timezone.now() - timedelta(days=1)

    data = {
        "cliente_id": self.cliente.cliente_id,
        "fecha_cita": fecha_pasada.isoformat(),
        "observaciones": "Test"
    }

    response = self.client.post(self.url, data)

    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertIn("fecha_cita", response.data)
```

#### Tests de Validación

##### 5. Campos Requeridos

```python
def test_crear_cita_campos_requeridos(self):
    """Test que verifica que todos los campos requeridos estén presentes."""
    # Test sin cliente_id
    data = {"fecha_cita": "2024-12-31T15:00:00Z"}
    response = self.client.post(self.url, data)
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertIn("cliente_id", response.data)

    # Test sin fecha_cita
    data = {"cliente_id": self.cliente.cliente_id}
    response = self.client.post(self.url, data)
    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertIn("fecha_cita", response.data)
```

##### 6. Formato de Fecha Inválido

```python
def test_crear_cita_formato_fecha_invalido(self):
    """Test que verifica validación de formato de fecha."""
    data = {
        "cliente_id": self.cliente.cliente_id,
        "fecha_cita": "fecha-invalida",
        "observaciones": "Test"
    }

    response = self.client.post(self.url, data)

    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertIn("fecha_cita", response.data)
```

---

## Test de Listado (`test_listar_citas.py`)

### Clase: TestListarCitas

#### Tests Principales

##### 1. Listado Exitoso

```python
def test_listar_citas_exitoso(self):
    """Test que verifica que se pueden listar las citas correctamente."""
    # Crear múltiples citas
    CitaFactory.create_batch(3, cliente=self.cliente)

    response = self.client.get(self.url)

    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(len(response.data["results"]), 3)
    self.assertIn("count", response.data)
    self.assertIn("results", response.data)
```

##### 2. Paginación

```python
def test_listar_citas_paginacion(self):
    """Test que verifica que la paginación funciona correctamente."""
    CitaFactory.create_batch(25, cliente=self.cliente)

    response = self.client.get(self.url)

    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(len(response.data["results"]), 20)  # Page size default
    self.assertIsNotNone(response.data["next"])
    self.assertIsNone(response.data["previous"])
```

##### 3. Filtro por Estado

```python
def test_filtrar_por_estado(self):
    """Test que verifica el filtrado por estado."""
    CitaFactory(estado="programada", cliente=self.cliente)
    CitaFactory(estado="completada", cliente=self.cliente)
    CitaFactory(estado="cancelada", cliente=self.cliente)

    # Filtrar por programada
    response = self.client.get(self.url, {"estado": "programada"})
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(len(response.data["results"]), 1)
    self.assertEqual(response.data["results"][0]["estado"], "programada")
```

##### 4. Filtro por Cliente

```python
def test_filtrar_por_cliente(self):
    """Test que verifica el filtrado por cliente."""
    cliente2 = ClienteFactory()
    CitaFactory(cliente=self.cliente)
    CitaFactory(cliente=cliente2)

    response = self.client.get(self.url, {"cliente": self.cliente.cliente_id})

    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(len(response.data["results"]), 1)
    self.assertEqual(
        response.data["results"][0]["cliente"]["id"],
        self.cliente.cliente_id
    )
```

##### 5. Búsqueda de Texto

```python
def test_busqueda_texto(self):
    """Test que verifica la búsqueda por texto."""
    CitaFactory(observaciones="Manicure especial", cliente=self.cliente)
    CitaFactory(observaciones="Pedicure normal", cliente=self.cliente)

    response = self.client.get(self.url, {"search": "manicure"})

    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(len(response.data["results"]), 1)
    self.assertIn("Manicure", response.data["results"][0]["observaciones"])
```

##### 6. Ordenamiento

```python
def test_ordenamiento(self):
    """Test que verifica el ordenamiento de citas."""
    fecha1 = timezone.now() + timedelta(days=1)
    fecha2 = timezone.now() + timedelta(days=2)

    cita1 = CitaFactory(fecha_cita=fecha2, cliente=self.cliente)
    cita2 = CitaFactory(fecha_cita=fecha1, cliente=self.cliente)

    # Ordenar por fecha ascendente
    response = self.client.get(self.url, {"ordering": "fecha_cita"})

    self.assertEqual(response.status_code, status.HTTP_200_OK)
    results = response.data["results"]
    self.assertEqual(results[0]["id"], cita2.id)
    self.assertEqual(results[1]["id"], cita1.id)
```

---

## Test de Detalle (`test_detalle_citas.py`)

### Clase: TestDetalleCitas

#### Tests Principales

##### 1. Detalle Exitoso

```python
def test_detalle_cita_exitoso(self):
    """Test que verifica que se puede obtener el detalle de una cita."""
    cita = CitaFactory(cliente=self.cliente)
    DetalleCitaFactory(cita=cita, servicio=self.servicio)

    url = reverse("cita-detail", kwargs={"pk": cita.id})
    response = self.client.get(url)

    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(response.data["id"], cita.id)
    self.assertIn("cliente", response.data)
    self.assertIn("detalles", response.data)
    self.assertEqual(len(response.data["detalles"]), 1)
```

##### 2. Cita Inexistente

```python
def test_detalle_cita_inexistente(self):
    """Test que verifica el comportamiento con cita inexistente."""
    url = reverse("cita-detail", kwargs={"pk": 99999})
    response = self.client.get(url)

    self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
```

##### 3. Estructura de Respuesta

```python
def test_estructura_respuesta_detalle(self):
    """Test que verifica la estructura de la respuesta de detalle."""
    cita = CitaFactory(cliente=self.cliente)

    url = reverse("cita-detail", kwargs={"pk": cita.id})
    response = self.client.get(url)

    self.assertEqual(response.status_code, status.HTTP_200_OK)

    # Verificar campos principales
    required_fields = [
        "id", "cliente", "fecha_cita", "estado", "total",
        "observaciones", "fecha_creacion", "fecha_actualizacion", "detalles"
    ]

    for field in required_fields:
        self.assertIn(field, response.data)
```

---

## Test de Actualización (`test_actualizar_citas.py`)

### Clase: TestActualizarCitas

#### Tests Principales

##### 1. Actualización PUT Exitosa

```python
def test_actualizar_cita_put_exitoso(self):
    """Test que verifica la actualización completa con PUT."""
    cita = CitaFactory(cliente=self.cliente)

    data = {
        "cliente_id": self.cliente.cliente_id,
        "fecha_cita": (timezone.now() + timedelta(days=5)).isoformat(),
        "estado": "confirmada",
        "observaciones": "Cita actualizada"
    }

    url = reverse("cita-detail", kwargs={"pk": cita.id})
    response = self.client.put(url, data)

    self.assertEqual(response.status_code, status.HTTP_200_OK)

    cita.refresh_from_db()
    self.assertEqual(cita.estado, "confirmada")
    self.assertEqual(cita.observaciones, "Cita actualizada")
```

##### 2. Actualización PATCH Exitosa

```python
def test_actualizar_cita_patch_exitoso(self):
    """Test que verifica la actualización parcial con PATCH."""
    cita = CitaFactory(estado="programada", cliente=self.cliente)

    data = {"estado": "confirmada"}

    url = reverse("cita-detail", kwargs={"pk": cita.id})
    response = self.client.patch(url, data)

    self.assertEqual(response.status_code, status.HTTP_200_OK)

    cita.refresh_from_db()
    self.assertEqual(cita.estado, "confirmada")
```

##### 3. Validación Estado Completada

```python
def test_no_actualizar_cita_completada(self):
    """Test que verifica que no se puede actualizar una cita completada."""
    cita = CitaFactory(estado="completada", cliente=self.cliente)

    data = {"estado": "cancelada"}

    url = reverse("cita-detail", kwargs={"pk": cita.id})
    response = self.client.patch(url, data)

    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertIn("error", response.data)
```

##### 4. Validación Estado Cancelada

```python
def test_no_actualizar_cita_cancelada(self):
    """Test que verifica que no se puede actualizar una cita cancelada."""
    cita = CitaFactory(estado="cancelada", cliente=self.cliente)

    data = {"observaciones": "Intento de actualización"}

    url = reverse("cita-detail", kwargs={"pk": cita.id})
    response = self.client.patch(url, data)

    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertIn("error", response.data)
```

---

## Test de Eliminación (`test_eliminar_citas.py`)

### Clase: TestEliminarCitas

#### Tests Principales

##### 1. Eliminación Exitosa

```python
def test_eliminar_cita_exitosa(self):
    """Test que verifica que se puede eliminar una cita programada."""
    cita = CitaFactory(estado="programada", cliente=self.cliente)

    url = reverse("cita-detail", kwargs={"pk": cita.id})
    response = self.client.delete(url)

    self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    self.assertEqual(Cita.objects.count(), 0)
```

##### 2. No Eliminar Cita Completada

```python
def test_no_eliminar_cita_completada(self):
    """Test que verifica que no se puede eliminar una cita completada."""
    cita = CitaFactory(estado="completada", cliente=self.cliente)

    url = reverse("cita-detail", kwargs={"pk": cita.id})
    response = self.client.delete(url)

    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    self.assertIn("error", response.data)
    self.assertEqual(Cita.objects.count(), 1)
```

##### 3. Eliminación en Cascada de Detalles

```python
def test_eliminar_cita_cascada_detalles(self):
    """Test que verifica que al eliminar una cita se eliminan sus detalles."""
    cita = CitaFactory(estado="programada", cliente=self.cliente)
    DetalleCitaFactory(cita=cita, servicio=self.servicio)
    DetalleCitaFactory(cita=cita, servicio=self.servicio)

    self.assertEqual(DetalleCita.objects.count(), 2)

    url = reverse("cita-detail", kwargs={"pk": cita.id})
    response = self.client.delete(url)

    self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    self.assertEqual(Cita.objects.count(), 0)
    self.assertEqual(DetalleCita.objects.count(), 0)
```

---

## Factories para Testing

### CitaFactory

**Ubicación**: `tests/factories.py`

```python
class CitaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Cita

    cliente = factory.SubFactory(ClienteFactory)
    fecha_cita = factory.LazyFunction(
        lambda: timezone.now() + timedelta(days=random.randint(1, 30))
    )
    estado = "programada"
    observaciones = factory.Faker("text", max_nb_chars=200)
```

### DetalleCitaFactory

```python
class DetalleCitaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DetalleCita

    cita = factory.SubFactory(CitaFactory)
    servicio = factory.SubFactory(ServicioFactory)
    precio = factory.LazyAttribute(lambda obj: obj.servicio.precio)
    cantidad = 1
```

## Utilidades de Testing

### Métodos Auxiliares

```python
def crear_cita_con_servicios(self, cantidad_servicios=2):
    """Crea una cita con servicios asociados."""
    cita = CitaFactory(cliente=self.cliente)

    for _ in range(cantidad_servicios):
        servicio = ServicioFactory()
        DetalleCitaFactory(cita=cita, servicio=servicio)

    cita.actualizar_total()
    return cita

def assertCitaData(self, response_data, cita):
    """Verifica que los datos de respuesta coincidan con la cita."""
    self.assertEqual(response_data["id"], cita.id)
    self.assertEqual(response_data["estado"], cita.estado)
    self.assertEqual(response_data["cliente"]["id"], cita.cliente.cliente_id)
```

## Configuración de Base de Datos de Test

### Configuraciones Específicas

```python
# En conftest.py o settings de test
@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Permite acceso a BD para todos los tests."""
    pass

@pytest.fixture
def api_client():
    """Cliente API autenticado."""
    user = User.objects.create_user(
        username='testuser',
        password='testpass123'
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client
```

## Métricas de Cobertura

### Resultados de Cobertura

```
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
apps/appointments/models/cita.py           45      0   100%
apps/appointments/models/detalle_cita.py   25      0   100%
apps/appointments/views/cita_views.py      65      3    95%
apps/appointments/views/detalle_cita_views.py  40   2    95%
apps/appointments/serializers/             80      5    94%
-----------------------------------------------------------
TOTAL                                     255     10    96%
```

### Líneas No Cubiertas

```python
# Principalmente:
# - Casos de error de base de datos
# - Métodos de logging específicos
# - Validaciones de edge cases muy específicos
```

## Comandos de Ejecución

### Ejecutar Todos los Tests

```bash
# Todos los tests de appointments
python manage.py test tests.appointments

# Tests específicos
python manage.py test tests.appointments.test_crear_citas
python manage.py test tests.appointments.test_eliminar_citas.TestEliminarCitas.test_eliminar_cita_exitosa

# Con cobertura
coverage run --source='.' manage.py test tests.appointments
coverage report
coverage html
```

### Ejecutar con Pytest

```bash
# Con pytest (si está configurado)
pytest tests/appointments/ -v
pytest tests/appointments/test_crear_citas.py::TestCrearCitas::test_crear_cita_exitosa -v

# Con cobertura
pytest tests/appointments/ --cov=apps.appointments --cov-report=html
```

## Consideraciones de Rendimiento en Tests

### Optimizaciones

1. **Uso de Factories**: Genera datos mínimos necesarios
2. **setUp Eficiente**: Evita crear datos innecesarios en cada test
3. **Transacciones**: Los tests usan transacciones que se revierten automáticamente
4. **Base de Datos en Memoria**: Para tests rápidos

### Base de Datos de Test

```python
# En settings/test.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
```

Esta suite de pruebas proporciona una cobertura completa del 96% del código de appointments, validando todas las funcionalidades críticas de la API y garantizando la robustez del sistema.
