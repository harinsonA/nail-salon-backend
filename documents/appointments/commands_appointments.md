# Documentación de Comandos de Gestión - Appointments

## Visión General

La aplicación appointments incluye varios comandos personalizados de Django que facilitan tareas administrativas y de gestión específicas para citas y servicios. Estos comandos están ubicados en la carpeta `management/commands/` y proporcionan funcionalidades especializadas para el mantenimiento del sistema de citas.

## Estructura de Comandos

**Ubicación**: `apps/appointments/management/commands/`

### Comandos Disponibles

| Comando                    | Archivo                       | Propósito                                      |
| -------------------------- | ----------------------------- | ---------------------------------------------- |
| `limpiar_citas_antiguas`   | `limpiar_citas_antiguas.py`   | Limpiar citas antiguas completadas             |
| `generar_reporte_citas`    | `generar_reporte_citas.py`    | Generar reportes de citas por período          |
| `actualizar_totales_citas` | `actualizar_totales_citas.py` | Recalcular totales de todas las citas          |
| `migrar_estados_citas`     | `migrar_estados_citas.py`     | Migrar estados de citas (para actualizaciones) |
| `verificar_integridad`     | `verificar_integridad.py`     | Verificar integridad de datos de citas         |

---

## Comando: limpiar_citas_antiguas

### Propósito

Limpia automáticamente las citas antiguas completadas o canceladas que excedan un período determinado, manteniendo la base de datos optimizada.

### Archivo: `limpiar_citas_antiguas.py`

```python
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.appointments.models import Cita

class Command(BaseCommand):
    help = 'Limpia citas antiguas completadas o canceladas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=365,
            help='Días de antigüedad para eliminar (por defecto: 365)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular sin eliminar realmente'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Eliminar sin confirmación'
        )

    def handle(self, *args, **options):
        dias = options['dias']
        dry_run = options['dry_run']
        force = options['force']

        fecha_limite = timezone.now() - timedelta(days=dias)

        citas_a_eliminar = Cita.objects.filter(
            fecha_cita__lt=fecha_limite,
            estado__in=['completada', 'cancelada']
        )

        self.limpiar_citas(citas_a_eliminar, dry_run, force)
```

### Uso

```bash
# Limpieza estándar (citas de más de 1 año)
python manage.py limpiar_citas_antiguas

# Especificar días personalizados
python manage.py limpiar_citas_antiguas --dias 180

# Simulación sin eliminar
python manage.py limpiar_citas_antiguas --dry-run

# Forzar eliminación sin confirmación
python manage.py limpiar_citas_antiguas --force --dias 90
```

### Salida Esperada

```
=== LIMPIEZA DE CITAS ANTIGUAS ===

Parámetros:
- Días de antigüedad: 365
- Fecha límite: 2023-01-15
- Modo: Eliminación real

Analizando citas...
✓ Citas completadas encontradas: 45
✓ Citas canceladas encontradas: 12
✓ Total a eliminar: 57

¿Continuar con la eliminación? (y/N): y

Eliminando citas...
✓ 57 citas eliminadas exitosamente
✓ 89 detalles de cita eliminados en cascada

=== RESUMEN ===
Espacio liberado: ~2.3 MB
Citas restantes: 234
Estado: ✓ COMPLETADO
```

### Funcionalidades Avanzadas

#### 1. Validación de Integridad

```python
def validar_antes_eliminar(self, citas):
    """Valida que las citas sean seguras de eliminar"""
    problemas = []

    for cita in citas:
        # Verificar que no tenga pagos pendientes
        if hasattr(cita, 'pagos') and cita.pagos.filter(estado='pendiente').exists():
            problemas.append(f"Cita {cita.id} tiene pagos pendientes")

        # Verificar que esté en estado final
        if cita.estado not in ['completada', 'cancelada']:
            problemas.append(f"Cita {cita.id} no está en estado final")

    return problemas
```

#### 2. Backup Antes de Eliminar

```python
def crear_backup(self, citas):
    """Crea un backup de las citas antes de eliminar"""
    import json
    from datetime import datetime

    backup_data = []
    for cita in citas:
        backup_data.append({
            'id': cita.id,
            'cliente_id': cita.cliente.cliente_id,
            'fecha_cita': cita.fecha_cita.isoformat(),
            'estado': cita.estado,
            'total': str(cita.total),
            'observaciones': cita.observaciones,
            'detalles': [
                {
                    'servicio_id': d.servicio.id,
                    'cantidad': d.cantidad,
                    'precio': str(d.precio)
                }
                for d in cita.detalles.all()
            ]
        })

    filename = f"backup_citas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(backup_data, f, indent=2)

    return filename
```

---

## Comando: generar_reporte_citas

### Propósito

Genera reportes detallados de citas por diferentes períodos y criterios, útil para análisis de negocio y seguimiento de KPIs.

### Archivo: `generar_reporte_citas.py`

```python
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Sum, Avg
from datetime import timedelta
import csv

class Command(BaseCommand):
    help = 'Genera reportes de citas por período'

    def add_arguments(self, parser):
        parser.add_argument(
            '--periodo',
            choices=['dia', 'semana', 'mes', 'año'],
            default='mes',
            help='Período del reporte'
        )
        parser.add_argument(
            '--formato',
            choices=['consola', 'csv', 'json'],
            default='consola',
            help='Formato de salida del reporte'
        )
        parser.add_argument(
            '--desde',
            type=str,
            help='Fecha de inicio (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--hasta',
            type=str,
            help='Fecha de fin (YYYY-MM-DD)'
        )

    def handle(self, *args, **options):
        periodo = options['periodo']
        formato = options['formato']

        fechas = self.calcular_fechas(periodo, options['desde'], options['hasta'])
        datos = self.generar_datos_reporte(fechas)

        if formato == 'consola':
            self.mostrar_reporte_consola(datos, periodo)
        elif formato == 'csv':
            self.generar_csv(datos, periodo)
        elif formato == 'json':
            self.generar_json(datos, periodo)
```

### Uso

```bash
# Reporte mensual por consola
python manage.py generar_reporte_citas --periodo mes

# Reporte semanal en CSV
python manage.py generar_reporte_citas --periodo semana --formato csv

# Reporte personalizado
python manage.py generar_reporte_citas --desde 2024-01-01 --hasta 2024-01-31 --formato json

# Reporte anual completo
python manage.py generar_reporte_citas --periodo año --formato csv
```

### Salida Esperada

```
=== REPORTE DE CITAS - ENERO 2024 ===

📊 ESTADÍSTICAS GENERALES
├─ Total de citas: 234
├─ Citas completadas: 198 (84.6%)
├─ Citas canceladas: 24 (10.3%)
├─ Citas pendientes: 12 (5.1%)
└─ Ingresos totales: $8,450,000

💰 INGRESOS POR ESTADO
├─ Completadas: $7,920,000
├─ Confirmadas: $450,000
└─ Programadas: $80,000

📈 TENDENCIAS
├─ Promedio citas/día: 7.5
├─ Promedio ingresos/día: $272,581
├─ Día más ocupado: Sábado (45 citas)
└─ Servicio más popular: Manicure Clásico (89 veces)

🏆 TOP SERVICIOS
1. Manicure Clásico - 89 servicios ($4,005,000)
2. Pedicure Spa - 67 servicios ($2,680,000)
3. Diseño de Uñas - 45 servicios ($1,350,000)

👥 TOP CLIENTES
1. María García - 8 citas ($680,000)
2. Ana López - 6 citas ($540,000)
3. Carmen Ruiz - 5 citas ($425,000)

📅 DISTRIBUCIÓN SEMANAL
Semana 1: 56 citas - $1,890,000
Semana 2: 62 citas - $2,170,000
Semana 3: 58 citas - $2,015,000
Semana 4: 58 citas - $2,375,000

=== ARCHIVO GENERADO ===
📄 reporte_citas_enero_2024.csv
```

---

## Comando: actualizar_totales_citas

### Propósito

Recalcula y actualiza los totales de todas las citas basándose en sus detalles de servicios. Útil para corregir inconsistencias o después de cambios masivos de precios.

### Archivo: `actualizar_totales_citas.py`

```python
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.appointments.models import Cita

class Command(BaseCommand):
    help = 'Recalcula los totales de todas las citas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cita-id',
            type=int,
            help='ID específico de cita a actualizar'
        )
        parser.add_argument(
            '--estado',
            choices=['programada', 'confirmada', 'en_proceso', 'completada', 'cancelada'],
            help='Actualizar solo citas en este estado'
        )
        parser.add_argument(
            '--verificar-solo',
            action='store_true',
            help='Solo verificar inconsistencias sin actualizar'
        )

    def handle(self, *args, **options):
        cita_id = options.get('cita_id')
        estado = options.get('estado')
        verificar_solo = options['verificar_solo']

        if cita_id:
            citas = Cita.objects.filter(id=cita_id)
        elif estado:
            citas = Cita.objects.filter(estado=estado)
        else:
            citas = Cita.objects.all()

        self.procesar_citas(citas, verificar_solo)
```

### Uso

```bash
# Actualizar todas las citas
python manage.py actualizar_totales_citas

# Actualizar una cita específica
python manage.py actualizar_totales_citas --cita-id 123

# Actualizar solo citas completadas
python manage.py actualizar_totales_citas --estado completada

# Solo verificar inconsistencias
python manage.py actualizar_totales_citas --verificar-solo
```

### Salida Esperada

```
=== ACTUALIZACIÓN DE TOTALES DE CITAS ===

Analizando 234 citas...

📊 ANÁLISIS INICIAL
├─ Citas con totales correctos: 229
├─ Citas con inconsistencias: 5
└─ Citas sin detalles: 0

🔧 CITAS A CORREGIR
├─ Cita #45: Total actual $85,000 → Correcto $90,000
├─ Cita #67: Total actual $120,000 → Correcto $115,000
├─ Cita #89: Total actual $75,000 → Correcto $80,000
├─ Cita #102: Total actual $95,000 → Correcto $100,000
└─ Cita #156: Total actual $110,000 → Correcto $105,000

Aplicando correcciones...
✓ 5 citas actualizadas exitosamente
✓ Diferencia total corregida: +$5,000

=== RESUMEN ===
Total citas procesadas: 234
Actualizaciones realizadas: 5
Estado: ✓ COMPLETADO
```

---

## Comando: migrar_estados_citas

### Propósito

Migra estados de citas cuando se realizan cambios en la lógica de negocio o se introducen nuevos estados en el sistema.

### Archivo: `migrar_estados_citas.py`

```python
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.appointments.models import Cita

class Command(BaseCommand):
    help = 'Migra estados de citas según nuevas reglas de negocio'

    def add_arguments(self, parser):
        parser.add_argument(
            '--regla',
            choices=['completar_antiguas', 'actualizar_pendientes', 'limpiar_inconsistencias'],
            required=True,
            help='Regla de migración a aplicar'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular sin aplicar cambios'
        )

    def handle(self, *args, **options):
        regla = options['regla']
        dry_run = options['dry_run']

        if regla == 'completar_antiguas':
            self.completar_citas_antiguas(dry_run)
        elif regla == 'actualizar_pendientes':
            self.actualizar_citas_pendientes(dry_run)
        elif regla == 'limpiar_inconsistencias':
            self.limpiar_inconsistencias(dry_run)
```

### Uso

```bash
# Completar citas antiguas automáticamente
python manage.py migrar_estados_citas --regla completar_antiguas

# Simular actualización
python manage.py migrar_estados_citas --regla actualizar_pendientes --dry-run

# Limpiar inconsistencias de estado
python manage.py migrar_estados_citas --regla limpiar_inconsistencias
```

---

## Comando: verificar_integridad

### Propósito

Verifica la integridad de los datos de citas, detectando inconsistencias, referencias huérfanas y problemas de validación.

### Archivo: `verificar_integridad.py`

```python
from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.appointments.models import Cita, DetalleCita

class Command(BaseCommand):
    help = 'Verifica la integridad de datos de appointments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reparar',
            action='store_true',
            help='Reparar problemas encontrados automáticamente'
        )
        parser.add_argument(
            '--detallado',
            action='store_true',
            help='Mostrar detalles de todos los problemas'
        )

    def handle(self, *args, **options):
        reparar = options['reparar']
        detallado = options['detallado']

        problemas = []

        # Verificar citas huérfanas
        problemas.extend(self.verificar_citas_huerfanas())

        # Verificar totales incorrectos
        problemas.extend(self.verificar_totales_incorrectos())

        # Verificar fechas inconsistentes
        problemas.extend(self.verificar_fechas_inconsistentes())

        # Verificar detalles sin cita
        problemas.extend(self.verificar_detalles_huerfanos())

        self.mostrar_resultados(problemas, reparar, detallado)
```

### Uso

```bash
# Verificación estándar
python manage.py verificar_integridad

# Verificación con reparación automática
python manage.py verificar_integridad --reparar

# Verificación detallada
python manage.py verificar_integridad --detallado
```

### Salida Esperada

```
=== VERIFICACIÓN DE INTEGRIDAD - APPOINTMENTS ===

🔍 ANÁLISIS DE INTEGRIDAD

✓ Citas con clientes válidos: 234/234
✓ Detalles con citas válidas: 456/456
✓ Detalles con servicios válidos: 456/456
⚠️ Citas con totales incorrectos: 3/234
⚠️ Citas con fechas pasadas en estado 'programada': 2/234

🔧 PROBLEMAS DETECTADOS

1. TOTALES INCORRECTOS (3 casos)
   ├─ Cita #45: Total $85,000 ≠ Calculado $90,000
   ├─ Cita #67: Total $120,000 ≠ Calculado $115,000
   └─ Cita #89: Total $75,000 ≠ Calculado $80,000

2. FECHAS INCONSISTENTES (2 casos)
   ├─ Cita #156: Fecha 2024-01-10 está en el pasado (estado: programada)
   └─ Cita #178: Fecha 2024-01-12 está en el pasado (estado: confirmada)

=== RESUMEN ===
├─ Total problemas: 5
├─ Críticos: 0
├─ Advertencias: 5
└─ Estado general: ⚠️ ATENCIÓN REQUERIDA

💡 RECOMENDACIONES
1. Ejecutar: python manage.py actualizar_totales_citas
2. Revisar manualmente las citas con fechas pasadas
3. Considerar migrar estados automáticamente

¿Aplicar reparaciones automáticas? (y/N):
```

## Automatización con Cron

### Configuración de Tareas Programadas

```bash
# Crontab para automatizar comandos
# /etc/crontab o crontab -e

# Limpiar citas antiguas cada mes
0 2 1 * * cd /path/to/project && python manage.py limpiar_citas_antiguas --force

# Generar reporte semanal cada lunes
0 9 * * 1 cd /path/to/project && python manage.py generar_reporte_citas --periodo semana --formato csv

# Verificar integridad cada día
0 3 * * * cd /path/to/project && python manage.py verificar_integridad

# Actualizar totales cada semana
0 4 * * 0 cd /path/to/project && python manage.py actualizar_totales_citas
```

## Scripts de Mantenimiento

### Script Maestro: `mantenimiento_appointments.sh`

```bash
#!/bin/bash
# Script de mantenimiento completo para appointments

echo "=== INICIO MANTENIMIENTO APPOINTMENTS ==="
date

# 1. Verificar integridad
echo "1. Verificando integridad..."
python manage.py verificar_integridad --reparar

# 2. Actualizar totales
echo "2. Actualizando totales..."
python manage.py actualizar_totales_citas

# 3. Limpiar citas antiguas (más de 2 años)
echo "3. Limpiando citas antiguas..."
python manage.py limpiar_citas_antiguas --dias 730 --force

# 4. Generar reporte mensual
echo "4. Generando reporte..."
python manage.py generar_reporte_citas --periodo mes --formato csv

echo "=== FIN MANTENIMIENTO ==="
date
```

## Logging y Monitoreo

### Configuración de Logs

```python
# En cada comando
import logging

logger = logging.getLogger('appointments.management')

class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info(f"Iniciando comando {self.__class__.__name__}")

        try:
            # Lógica del comando
            resultado = self.ejecutar_comando()
            logger.info(f"Comando completado exitosamente: {resultado}")

        except Exception as e:
            logger.error(f"Error en comando: {str(e)}")
            raise
```

### Métricas de Rendimiento

```python
def medir_rendimiento(func):
    """Decorator para medir rendimiento de comandos"""
    def wrapper(*args, **kwargs):
        inicio = time.time()
        resultado = func(*args, **kwargs)
        fin = time.time()

        logger.info(f"Comando ejecutado en {fin - inicio:.2f} segundos")
        return resultado

    return wrapper
```

Esta documentación proporciona una guía completa para todos los comandos de gestión disponibles en la aplicación appointments, facilitando el mantenimiento y la administración del sistema de citas.
