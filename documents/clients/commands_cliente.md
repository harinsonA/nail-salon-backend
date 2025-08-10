# Documentación de Comandos de Gestión - Cliente

## Visión General

La aplicación clients incluye varios comandos personalizados de Django que facilitan tareas administrativas y de gestión de la base de datos. Estos comandos están ubicados en la carpeta `management/commands/` y proporcionan funcionalidades específicas para el mantenimiento del sistema.

## Estructura de Comandos

**Ubicación**: `apps/clients/management/commands/`

### Comandos Disponibles

| Comando              | Archivo                 | Propósito                             |
| -------------------- | ----------------------- | ------------------------------------- |
| `dbstatus`           | `dbstatus.py`           | Verificar estado de la base de datos  |
| `makemigrations_all` | `makemigrations_all.py` | Crear migraciones para todas las apps |
| `migrate_all`        | `migrate_all.py`        | Aplicar migraciones a todas las apps  |
| `sync_test_db`       | `sync_test_db.py`       | Sincronizar base de datos de pruebas  |

---

## Comando: dbstatus

### Propósito

Verifica el estado actual de la base de datos, incluyendo conexiones, tablas existentes, y estado de migraciones.

### Archivo: `dbstatus.py`

```python
from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps

class Command(BaseCommand):
    help = 'Verificar estado de la base de datos'

    def handle(self, *args, **options):
        # Verificar conexión a la base de datos
        self.verificar_conexion()

        # Verificar tablas existentes
        self.verificar_tablas()

        # Verificar estado de migraciones
        self.verificar_migraciones()
```

### Uso

```bash
python manage.py dbstatus
```

### Salida Esperada

```
=== ESTADO DE LA BASE DE DATOS ===

✓ Conexión a la base de datos: OK
✓ Total de tablas: 15

=== TABLAS DE LA APLICACIÓN CLIENTS ===
✓ clientes - Existe (120 registros)

=== ESTADO DE MIGRACIONES ===
✓ clients: 0001_initial - Aplicada
✓ clients: 0002_add_notas_field - Aplicada
✓ clients: 0003_add_activo_field - Aplicada

=== RESUMEN ===
Total aplicaciones: 5
Migraciones pendientes: 0
Estado general: ✓ CORRECTO
```

### Funcionalidades

#### 1. Verificación de Conexión

```python
def verificar_conexion(self):
    """Verifica que la conexión a la base de datos esté funcionando"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            self.stdout.write(
                self.style.SUCCESS("✓ Conexión a la base de datos: OK")
            )
    except Exception as e:
        self.stdout.write(
            self.style.ERROR(f"✗ Error de conexión: {e}")
        )
```

#### 2. Verificación de Tablas

```python
def verificar_tablas(self):
    """Lista todas las tablas y verifica las específicas de clients"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
        """, [connection.settings_dict['NAME']])

        tablas = [row[0] for row in cursor.fetchall()]

        # Verificar tabla de clientes
        if 'clientes' in tablas:
            count = Cliente.objects.count()
            self.stdout.write(
                self.style.SUCCESS(f"✓ clientes - Existe ({count} registros)")
            )
```

#### 3. Estado de Migraciones

```python
def verificar_migraciones(self):
    """Verifica el estado de las migraciones"""
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

    if plan:
        self.stdout.write(
            self.style.WARNING(f"⚠ Migraciones pendientes: {len(plan)}")
        )
        for migration, backwards in plan:
            self.stdout.write(f"  - {migration}")
    else:
        self.stdout.write(
            self.style.SUCCESS("✓ Todas las migraciones aplicadas")
        )
```

---

## Comando: makemigrations_all

### Propósito

Crea migraciones para todas las aplicaciones del proyecto de manera automática.

### Uso

```bash
python manage.py makemigrations_all
```

### Funcionalidades

```python
def handle(self, *args, **options):
    """Crear migraciones para todas las apps"""

    apps_to_migrate = [
        'clients',
        'appointments',
        'services',
        'payments',
        'settings',
        'authentication'
    ]

    for app_name in apps_to_migrate:
        self.stdout.write(f"\n=== Creando migraciones para {app_name} ===")

        try:
            call_command('makemigrations', app_name, verbosity=1)
            self.stdout.write(
                self.style.SUCCESS(f"✓ Migraciones creadas para {app_name}")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ Error en {app_name}: {e}")
            )
```

### Opciones Adicionales

```bash
# Crear migraciones con nombre personalizado
python manage.py makemigrations_all --name="major_update"

# Crear migraciones vacías
python manage.py makemigrations_all --empty

# Modo dry-run (simular sin crear)
python manage.py makemigrations_all --dry-run
```

---

## Comando: migrate_all

### Propósito

Aplica todas las migraciones pendientes en el orden correcto.

### Uso

```bash
python manage.py migrate_all
```

### Funcionalidades

```python
def handle(self, *args, **options):
    """Aplicar todas las migraciones pendientes"""

    # Orden específico para evitar problemas de dependencias
    migration_order = [
        'contenttypes',
        'auth',
        'authentication',
        'clients',
        'services',
        'appointments',
        'payments',
        'settings'
    ]

    for app_name in migration_order:
        self.stdout.write(f"\n=== Migrando {app_name} ===")

        try:
            call_command('migrate', app_name, verbosity=1)
            self.stdout.write(
                self.style.SUCCESS(f"✓ {app_name} migrado correctamente")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"✗ Error migrando {app_name}: {e}")
            )
            break  # Detener si hay error
```

### Verificación Post-Migración

```python
def verificar_post_migracion(self):
    """Verificar que las migraciones se aplicaron correctamente"""

    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

    if not plan:
        self.stdout.write(
            self.style.SUCCESS("\n✓ Todas las migraciones aplicadas correctamente")
        )

        # Verificar integridad de datos
        self.verificar_integridad_datos()
    else:
        self.stdout.write(
            self.style.WARNING(f"\n⚠ Quedan {len(plan)} migraciones pendientes")
        )
```

---

## Comando: sync_test_db

### Propósito

Sincroniza la base de datos de pruebas con la estructura de la base de datos principal.

### Uso

```bash
python manage.py sync_test_db
```

### Funcionalidades

```python
def handle(self, *args, **options):
    """Sincronizar base de datos de pruebas"""

    # Configurar base de datos de pruebas
    self.configurar_test_db()

    # Aplicar migraciones a test DB
    self.migrar_test_db()

    # Crear datos de prueba básicos
    self.crear_datos_prueba()

    # Verificar sincronización
    self.verificar_sincronizacion()
```

#### Configuración de Test DB

```python
def configurar_test_db(self):
    """Configurar conexión a base de datos de pruebas"""

    test_db_settings = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'nail_salon_test',
        'USER': 'test_user',
        'PASSWORD': 'test_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }

    # Verificar que la DB de pruebas existe
    self.verificar_test_db_existe(test_db_settings)
```

#### Creación de Datos de Prueba

```python
def crear_datos_prueba(self):
    """Crear datos básicos para pruebas"""

    # Cambiar a base de datos de pruebas
    from django.db import connections

    test_db = connections['test']

    with test_db.cursor() as cursor:
        # Crear clientes de prueba
        clientes_test = [
            ('Juan', 'Pérez', '3001111111', 'juan@test.com'),
            ('María', 'García', '3002222222', 'maria@test.com'),
            ('Carlos', 'López', '3003333333', 'carlos@test.com'),
        ]

        for nombre, apellido, telefono, email in clientes_test:
            Cliente.objects.using('test').create(
                nombre=nombre,
                apellido=apellido,
                telefono=telefono,
                email=email,
                activo=True
            )

        self.stdout.write(
            self.style.SUCCESS(f"✓ Creados {len(clientes_test)} clientes de prueba")
        )
```

---

## Configuración Base de Comandos

### Clase Base Común

```python
# En utils/base_command.py
from django.core.management.base import BaseCommand
from django.db import connection
from django.core.management import call_command

class BaseClientCommand(BaseCommand):
    """Clase base para comandos de la aplicación clients"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.success_count = 0
        self.error_count = 0

    def log_success(self, message):
        """Registrar mensaje de éxito"""
        self.success_count += 1
        self.stdout.write(self.style.SUCCESS(f"✓ {message}"))

    def log_error(self, message):
        """Registrar mensaje de error"""
        self.error_count += 1
        self.stdout.write(self.style.ERROR(f"✗ {message}"))

    def log_warning(self, message):
        """Registrar mensaje de advertencia"""
        self.stdout.write(self.style.WARNING(f"⚠ {message}"))

    def print_summary(self):
        """Imprimir resumen de ejecución"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("RESUMEN DE EJECUCIÓN")
        self.stdout.write("="*50)
        self.log_success(f"Operaciones exitosas: {self.success_count}")

        if self.error_count > 0:
            self.log_error(f"Errores encontrados: {self.error_count}")
        else:
            self.log_success("Sin errores")
```

---

## Uso en Desarrollo

### Flujo Típico de Desarrollo

```bash
# 1. Verificar estado inicial
python manage.py dbstatus

# 2. Crear nuevas migraciones tras cambios en modelos
python manage.py makemigrations_all

# 3. Aplicar migraciones
python manage.py migrate_all

# 4. Verificar estado final
python manage.py dbstatus

# 5. Sincronizar DB de pruebas si es necesario
python manage.py sync_test_db
```

### Scripts de Automatización

```bash
#!/bin/bash
# deploy.sh - Script de despliegue

echo "=== INICIANDO DESPLIEGUE ==="

# Verificar estado inicial
python manage.py dbstatus

# Aplicar migraciones
python manage.py migrate_all

# Verificar estado final
python manage.py dbstatus

# Ejecutar pruebas
python manage.py test tests.clients

echo "=== DESPLIEGUE COMPLETADO ==="
```

---

## Comandos Avanzados (Extensiones Futuras)

### Comando: backup_clientes

```python
class Command(BaseCommand):
    help = 'Crear backup de datos de clientes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            choices=['json', 'csv', 'excel'],
            default='json',
            help='Formato del backup'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Archivo de salida'
        )

    def handle(self, *args, **options):
        format_type = options['format']
        output_file = options['output'] or f'backup_clientes_{timezone.now().strftime("%Y%m%d_%H%M%S")}.{format_type}'

        if format_type == 'json':
            self.backup_json(output_file)
        elif format_type == 'csv':
            self.backup_csv(output_file)
        elif format_type == 'excel':
            self.backup_excel(output_file)
```

### Comando: restore_clientes

```python
class Command(BaseCommand):
    help = 'Restaurar datos de clientes desde backup'

    def add_arguments(self, parser):
        parser.add_argument(
            'backup_file',
            type=str,
            help='Archivo de backup a restaurar'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular restauración sin aplicar cambios'
        )

    def handle(self, *args, **options):
        backup_file = options['backup_file']
        dry_run = options['dry_run']

        if dry_run:
            self.simulate_restore(backup_file)
        else:
            self.restore_data(backup_file)
```

### Comando: clean_inactive_clients

```python
class Command(BaseCommand):
    help = 'Limpiar clientes inactivos antiguos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=365,
            help='Días de inactividad para considerar limpieza'
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirmar eliminación'
        )

    def handle(self, *args, **options):
        days = options['days']
        confirm = options['confirm']

        cutoff_date = timezone.now() - timedelta(days=days)

        clientes_antiguos = Cliente.objects.filter(
            activo=False,
            fecha_actualizacion__lt=cutoff_date
        )

        count = clientes_antiguos.count()

        if count == 0:
            self.log_success("No hay clientes para limpiar")
            return

        self.log_warning(f"Se encontraron {count} clientes para limpiar")

        if not confirm:
            self.log_warning("Use --confirm para proceder con la limpieza")
            return

        clientes_antiguos.delete()
        self.log_success(f"Eliminados {count} clientes inactivos")
```

---

## Integración con CI/CD

### GitHub Actions

```yaml
# .github/workflows/db-management.yml
name: Database Management

on:
  push:
    branches: [main]
    paths:
      - "apps/*/migrations/*"

jobs:
  migrate:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: "3.8"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Check database status
        run: python manage.py dbstatus

      - name: Run migrations
        run: python manage.py migrate_all

      - name: Verify final status
        run: python manage.py dbstatus
```

---

## Mejores Prácticas

### 1. Logging

```python
import logging

logger = logging.getLogger('nail_salon.commands')

class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info("Iniciando comando dbstatus")

        try:
            self.verificar_conexion()
            logger.info("Verificación de conexión exitosa")
        except Exception as e:
            logger.error(f"Error en verificación: {e}")
            raise
```

### 2. Manejo de Errores

```python
def handle(self, *args, **options):
    try:
        self.ejecutar_comando()
    except KeyboardInterrupt:
        self.log_warning("Comando interrumpido por el usuario")
        return
    except Exception as e:
        self.log_error(f"Error inesperado: {e}")
        if options.get('verbosity', 1) > 1:
            import traceback
            self.stdout.write(traceback.format_exc())
        raise
```

### 3. Validación de Argumentos

```python
def add_arguments(self, parser):
    parser.add_argument(
        '--env',
        choices=['development', 'staging', 'production'],
        default='development',
        help='Entorno de ejecución'
    )

def handle(self, *args, **options):
    env = options['env']

    if env == 'production':
        self.log_warning("Ejecutando en producción - Confirmación requerida")
        confirm = input("¿Continuar? (yes/no): ")
        if confirm.lower() != 'yes':
            self.log_warning("Operación cancelada")
            return
```

---

## Monitoreo y Alertas

### Integración con Sistemas de Monitoreo

```python
def notify_completion(self, success=True, message=""):
    """Notificar resultado a sistemas de monitoreo"""

    if hasattr(settings, 'MONITORING_WEBHOOK'):
        import requests

        payload = {
            'command': self.__class__.__name__,
            'success': success,
            'message': message,
            'timestamp': timezone.now().isoformat()
        }

        try:
            requests.post(settings.MONITORING_WEBHOOK, json=payload)
        except:
            pass  # No fallar el comando por problemas de notificación
```
