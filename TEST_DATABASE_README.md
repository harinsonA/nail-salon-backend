# Sistema de Tests con Base de Datos Existente

Este proyecto está configurado para usar una base de datos PostgreSQL existente para tests (`test_manicuredb`) en lugar de crear bases de datos temporales.

## Configuración Inicial

### 1. Crear la Base de Datos de Test

Ejecuta el script de configuración **una sola vez**:

```bash
python setup_test_db.py
```

Este script:

- Crea la base de datos `test_manicuredb` si no existe
- Aplica todas las migraciones para crear las tablas
- Configura el entorno de test

### 2. Verificar Configuración

La configuración incluye:

- **Base de datos de test**: `test_manicuredb`
- **Credenciales**: Las mismas que la base principal
- **Router personalizado**: `utils.db_router.TestDatabaseRouter`
- **Test Runner**: `utils.test_runner.ExistingDatabaseTestRunner`

## Uso

### Ejecutar Tests

```bash
# Ejecutar todos los tests
python manage.py test

# Ejecutar tests específicos
python manage.py test tests.test_models_with_existing_db

# Ejecutar con verbosidad
python manage.py test --verbosity=2
```

### Características del Sistema

1. **Base de Datos Persistente**:

   - La base `test_manicuredb` no se crea/destruye en cada ejecución
   - Solo se limpian los datos, manteniendo la estructura

2. **Limpieza Automática**:

   - Al inicio de cada ejecución se borran todos los datos
   - Se preservan tablas, índices y constraints
   - Cada test inicia con datos limpios

3. **Aislamiento**:
   - Los tests no afectan la base de datos principal (`manicuredb`)
   - Cada test corre en su propia transacción

## Estructura de Archivos

```
nail-salon-backend/
├── utils/
│   ├── db_router.py          # Router para dirigir operaciones de test
│   └── test_runner.py        # TestRunner personalizado
├── tests/
│   ├── __init__.py
│   └── test_models_with_existing_db.py  # Ejemplos de tests
├── setup_test_db.py          # Script de configuración inicial
└── nail_salon_api/
    └── settings.py           # Configuración actualizada
```

## Configuración en settings.py

```python
# Bases de datos
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "manicuredb",
        # ... otras configuraciones
    },
    "test_db": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "test_manicuredb",
        # ... mismas credenciales
    }
}

# Router y test runner
DATABASE_ROUTERS = ['utils.db_router.TestDatabaseRouter']
TEST_RUNNER = 'utils.test_runner.ExistingDatabaseTestRunner'
```

## Ejemplo de Test

```python
from django.test import TestCase
from apps.clients.models import Cliente

class ClienteTest(TestCase):
    def test_crear_cliente(self):
        cliente = Cliente.objects.create(
            nombre_completo='Test User',
            telefono='3001234567'
        )
        self.assertEqual(cliente.nombre_completo, 'Test User')
```

## Ventajas de este Enfoque

1. **Velocidad**: No se crea/destruye base de datos en cada ejecución
2. **Realismo**: Tests corren contra PostgreSQL real, no SQLite
3. **Debugging**: La base de datos persiste para inspección manual
4. **CI/CD**: Fácil configuración en pipelines de integración continua

## Mantenimiento

### Limpiar Base de Test Manualmente

Si necesitas limpiar completamente la base de test:

```python
from utils.test_runner import ExistingDatabaseTestRunner
runner = ExistingDatabaseTestRunner()
runner.clean_test_database()
```

### Recrear Base de Test

Si necesitas recrear la base desde cero:

1. Eliminar base manualmente: `DROP DATABASE test_manicuredb;`
2. Ejecutar nuevamente: `python setup_test_db.py`

## Troubleshooting

### Error de Conexión

- Verificar que PostgreSQL esté corriendo
- Confirmar credenciales en variables de entorno

### Tablas Faltantes

- Re-ejecutar: `python setup_test_db.py`
- Verificar que las migraciones estén aplicadas

### Tests Lentos

- La primera ejecución puede ser más lenta
- Ejecuciones subsecuentes son más rápidas

## Compatibilidad

- ✅ Django 4.2+
- ✅ PostgreSQL 12+
- ✅ Python 3.8+
- ✅ Pipelines CI/CD
