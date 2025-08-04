# Comandos de Gestión de Migraciones Sincronizadas

Este proyecto incluye comandos personalizados de Django que mantienen automáticamente sincronizadas las bases de datos principal y de test.

## 📋 Comandos Disponibles

### 1. `makemigrations_all` - Crear y Aplicar Migraciones

Crea migraciones y las aplica automáticamente en ambas bases de datos.

```bash
# Crear migraciones para todas las apps y aplicarlas
python manage.py makemigrations_all

# Crear migraciones para una app específica
python manage.py makemigrations_all clients

# Solo crear migraciones sin aplicarlas automáticamente
python manage.py makemigrations_all --skip-auto-migrate

# Modo dry-run (ver qué migraciones se crearían)
python manage.py makemigrations_all --dry-run

# Crear migración vacía
python manage.py makemigrations_all --empty clients --name add_custom_field
```

### 2. `migrate_all` - Aplicar Migraciones en Ambas Bases

Aplica migraciones existentes en la base principal y luego en la base de test.

```bash
# Aplicar todas las migraciones pendientes
python manage.py migrate_all

# Aplicar migraciones de una app específica
python manage.py migrate_all clients

# Migrar a una migración específica
python manage.py migrate_all clients 0002_add_fields

# Solo verificar migraciones pendientes
python manage.py migrate_all --check

# Saltar la base de datos de test
python manage.py migrate_all --skip-test-db
```

### 3. `sync_test_db` - Sincronizar Base de Test

Sincroniza la base de datos de test con la estructura actual del proyecto.

```bash
# Aplicar migraciones a la base de test
python manage.py sync_test_db

# Recrear completamente la base de test
python manage.py sync_test_db --recreate

# Forzar sin confirmación
python manage.py sync_test_db --force
```

### 4. `dbstatus` - Verificar Estado de Sincronización

Verifica el estado de ambas bases de datos y su sincronización.

```bash
# Verificar estado general
python manage.py dbstatus

# Mostrar comparación detallada de tablas
python manage.py dbstatus --tables
```

## 🔄 Flujos de Trabajo Recomendados

### Desarrollo Normal

1. **Hacer cambios en modelos**
2. **Crear y aplicar migraciones:**
   ```bash
   python manage.py makemigrations_all
   ```
   Esto automáticamente:
   - Crea las migraciones
   - Las aplica en la base principal
   - Las aplica en la base de test

### Cuando Solo Quieres Crear Migraciones

```bash
python manage.py makemigrations_all --skip-auto-migrate
# Luego cuando estés listo:
python manage.py migrate_all
```

### Verificar Estado Antes de Cambios

```bash
python manage.py dbstatus
```

### Sincronizar Base de Test Existente

```bash
python manage.py sync_test_db
```

### En Casos de Emergencia (Recrear Base de Test)

```bash
python manage.py sync_test_db --recreate --force
```

## 🎯 Ventajas de Este Sistema

### ✅ **Automatización Completa**

- Una sola comando sincroniza todo
- No más pasos manuales para mantener bases actualizadas
- Reduce errores humanos

### ✅ **Flujo de Desarrollo Optimizado**

- `makemigrations_all` → Crear y aplicar en un paso
- Feedback inmediato si algo falla
- Tests siempre ejecutan contra esquema actualizado

### ✅ **Trabajo en Equipo**

- Compañeros pueden sincronizar fácilmente con `sync_test_db`
- `dbstatus` muestra estado actual sin ambigüedades
- Comandos consistentes para todo el equipo

### ✅ **Debugging y Verificación**

- `dbstatus` muestra estado detallado
- Opciones `--dry-run` para verificar antes de aplicar
- Logs claros de qué se está ejecutando

## 🛠️ Opciones Avanzadas

### Flags Útiles

```bash
# Ver qué haría sin ejecutar
python manage.py makemigrations_all --dry-run

# Crear migración vacía para cambios manuales
python manage.py makemigrations_all --empty myapp --name custom_change

# Solo migrar base principal (saltar test)
python manage.py migrate_all --skip-test-db

# Verificar si hay migraciones pendientes
python manage.py migrate_all --check

# Migrar con más detalle
python manage.py migrate_all --verbosity=2

# Forzar recreación completa de base test
python manage.py sync_test_db --recreate --force
```

### Integración con Scripts de CI/CD

```bash
# En pipeline de CI/CD
python manage.py dbstatus
python manage.py migrate_all --check
python manage.py test
```

## 🚨 Casos de Uso Específicos

### Nuevo Desarrollador en el Equipo

```bash
# Configurar base de test por primera vez
python manage.py sync_test_db --recreate

# Verificar que todo está bien
python manage.py dbstatus
```

### Después de Pull/Merge con Migraciones

```bash
# Aplicar cualquier migración nueva
python manage.py migrate_all

# Verificar sincronización
python manage.py dbstatus
```

### Cambios Grandes en Modelos

```bash
# Verificar estado antes
python manage.py dbstatus

# Crear migraciones pero no aplicar automáticamente
python manage.py makemigrations_all --skip-auto-migrate

# Revisar migraciones generadas, luego aplicar
python manage.py migrate_all
```

### Problemas con Base de Test

```bash
# Verificar qué está mal
python manage.py dbstatus --tables

# Recrear base de test si es necesario
python manage.py sync_test_db --recreate
```

## 📝 Notas Importantes

1. **Backup**: Siempre haz backup antes de `--recreate`
2. **Permisos**: Asegúrate de tener permisos para crear/eliminar bases de datos
3. **Conexiones**: Los comandos manejan conexiones automáticamente
4. **Logs**: Usa `--verbosity=2` para más detalles si hay problemas

## 🔍 Troubleshooting

### "Base de datos de test no configurada"

- Verifica que `test_db` esté en `DATABASES` en settings.py

### "No se puede conectar a base de test"

- Verifica credenciales en settings.py
- Asegúrate de que PostgreSQL esté ejecutándose
- Confirma que la base `test_manicuredb` existe

### "Migraciones no se aplican"

- Ejecuta `python manage.py dbstatus` para diagnóstico
- Usa `--verbosity=2` para más detalles
- Verifica permisos de base de datos
