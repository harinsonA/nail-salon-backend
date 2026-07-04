# 💅 Nail Salon Backend

[![CI](https://github.com/harinsonA/nail-salon-backend/actions/workflows/ci.yml/badge.svg)](https://github.com/harinsonA/nail-salon-backend/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](https://www.docker.com/)
[![Django](https://img.shields.io/badge/Django-4.2-green.svg)](https://djangoproject.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://postgresql.org)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3.3-purple.svg)](https://getbootstrap.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Sistema web para la gestión integral de un salón de uñas, desarrollado con Django. Combina vistas server-rendered con modales Bootstrap y AJAX para ofrecer una experiencia fluida sin recargas de página. El flujo principal es: **Calendario → Agenda diaria → Citas → Pagos**.

## ✨ Características Principales

### 🔐 Autenticación y Perfil

- Login/Logout con sistema de autenticación nativo de Django
- Edición de perfil (nombre, apellido, email, username) vía modal
- Cambio de contraseña con verificación de contraseña actual
- Redirección automática al calendario tras iniciar sesión

### 📅 Calendario y Agenda

- **Vista mensual**: Calendario interactivo que muestra la cantidad de citas pendientes y completadas por día
- **Vista diaria (Agenda)**: Listado de citas del día seleccionado con acciones contextuales según el estado de cada cita
- **Creación de citas**: Formulario de página completa que permite crear múltiples citas en lote, cada una con un cliente y varios servicios
- **Validación de horarios**: Consulta AJAX de horas ocupadas para evitar solapamientos
- **Flujo de estados**: Pendiente → Completada / Cancelada, con opción de restaurar citas canceladas

### 👥 Gestión de Clientes

- CRUD completo mediante modales Bootstrap (crear, editar, eliminar)
- Listado server-side con DataTables: búsqueda, paginación y ordenamiento
- Filtro por estado (todos / activos / inactivos)
- Validación de teléfonos por país (Argentina, Chile, Colombia, Ecuador, México, Perú, Rep. Dominicana, Uruguay, Venezuela)
- Soft delete (eliminación lógica) con historial de cambios

### 💄 Catálogo de Servicios

- CRUD completo mediante modales Bootstrap
- Precio, descripción y duración estimada configurables
- Duración mostrada en formato legible (ej: "1h 30m")
- Listado AJAX con filtro por estado activo/inactivo
- Soft delete con historial de cambios

### 💰 Gestión de Pagos

- **Confirmación de cita = Creación de pago**: Al completar una cita se genera automáticamente el registro de pago con sus detalles
- **Abonos parciales**: Soporte para pagos parciales (señas/anticipos) que generan deudas rastreables
- **Vista de pagos completados**: Listado mensual con totales facturados, descontados y cobrados
- **Vista de deudores**: Listado de pagos pendientes con saldo calculado (total - abonos)
- **Detalle de deuda**: Modal con desglose de servicios y historial de pagos parciales
- **Métodos de pago**: Efectivo, Tarjeta, Transferencia, Cheque
- **Estados de pago**: Pendiente, Completado, Reembolsado, Impago
- **Registros financieros inmutables**: Los detalles de pago no tienen soft delete

### ⚙️ Configuración del Salón _(en desarrollo)_

- Estructura preparada para: Sobre Nosotros, Galería de imágenes, Servicios destacados
- Modelos, vistas y URLs pendientes de implementación

## 🛠 Tecnologías

| Categoría | Tecnología |
|---|---|
| **Backend** | Python 3.12, Django 4.2 |
| **Infraestructura** | Docker (imagen `python:3.12.8-slim`), Render, GitHub Actions (CI) |
| **Base de Datos** | PostgreSQL 13+ |
| **Frontend** | Bootstrap 5.3.3, jQuery 3.7.1 |
| **Tablas** | DataTables 2.3.4 (server-side, responsive, fixed columns) |
| **Modales** | django-bootstrap-modal-forms |
| **Historial** | django-simple-history |
| **Soft Delete** | django-model-utils (SoftDeletableModel) |
| **Notificaciones** | Toastify 1.12.0 |
| **Datepickers** | Bootstrap Datepicker 1.10.0 (locale español) |
| **Iconos** | Google Material Symbols |
| **Config** | python-decouple (.env) |

## 📁 Estructura del Proyecto

```
nail-salon-backend/
├── apps/
│   ├── appointments/          # Calendario, agenda diaria y citas
│   │   ├── models/            # Cita, DetalleCita (snapshot de servicios)
│   │   ├── views/             # Calendar, Agenda CRUD, Handler de creación en lote
│   │   └── templates/         # Calendario mensual, modales de citas
│   ├── clients/               # Gestión de clientes
│   │   ├── models/            # Cliente (soft delete + historial)
│   │   ├── views/             # CRUD con modales, listado AJAX
│   │   ├── management/commands/  # dbstatus, makemigrations_all
│   │   └── templates/
│   ├── services/              # Catálogo de servicios
│   │   ├── models/            # Servicio (precio, duración, soft delete)
│   │   ├── views/             # CRUD con modales, listado AJAX
│   │   └── templates/
│   ├── payments/              # Pagos y deudores
│   │   ├── models/            # Pago, DetallePago (inmutable)
│   │   ├── choices.py         # EstadoCita, MetodoPago, EstadoPago
│   │   ├── views/
│   │   │   ├── payments/      # Pagos completados (listado mensual)
│   │   │   └── debtors/       # Deudores, detalle de deuda, agregar abono
│   │   └── templates/
│   ├── profiles/              # Autenticación y perfil de usuario
│   │   ├── views/
│   │   │   ├── login/         # Login y Logout
│   │   │   └── profile/       # Edición de perfil y cambio de contraseña
│   │   └── templates/
│   ├── settings/              # Configuración del salón (en desarrollo)
│   └── common/                # Utilidades compartidas
│       ├── base_list_view_ajax.py  # Vista base para DataTables server-side
│       ├── custom_time_fields.py   # DurationInMinutesField, CustomDateField
│       ├── widgets.py              # DatePickerWidget, MonthPickerWidget
│       └── utils/                  # CommonCleaner, PhoneCleaner, formateo
├── dashboard/                 # Redirige a /calendario/
├── templates/                 # Templates globales (base, menú, modales)
├── static/
│   ├── css/custom/            # Estilos personalizados
│   ├── js/custom/             # DataTables, modales, datepickers, AJAX
│   └── js/libs/               # Bootstrap, jQuery, DataTables, Toastify
└── nail_salon_api/            # Configuración Django (settings, urls, wsgi)
```

## 🌐 Rutas Principales

### 📅 Calendario y Agenda

| Ruta | Descripción |
|---|---|
| `/calendario/` | Vista mensual del calendario (página principal) |
| `/calendario/lista/ajax/` | Datos del calendario (JSON) |
| `/calendario/agenda/{fecha}/` | Agenda diaria de una fecha |
| `/calendario/agenda/{fecha}/crear/` | Crear citas para una fecha |
| `/agenda/lista/ajax/` | Listado AJAX de citas del día |
| `/agenda/detalle/{id}/editar/modal/` | Editar cita |
| `/agenda/detalle/{id}/ver/modal/` | Ver detalle de cita |
| `/agenda/detalle/{id}/confirmar/modal/` | Completar cita y generar pago |
| `/agenda/detalle/{id}/cancelar/modal/` | Cancelar cita |
| `/agenda/detalle/{id}/restaurar/modal/` | Restaurar cita cancelada |
| `/agenda/detalle/{id}/eliminar/modal/` | Eliminar cita |
| `/agenda/servicio/detalles/ajax/` | Info de servicio (precio, duración) |
| `/agenda/horas/disponibles/ajax/` | Horas ocupadas de una fecha |

### 👥 Clientes

| Ruta | Descripción |
|---|---|
| `/clientes/` | Vista principal |
| `/clientes/lista/ajax` | Listado server-side |
| `/clientes/crear/` | Modal de creación |
| `/clientes/{id}/detalle/` | Modal de edición |
| `/clientes/{id}/eliminar/` | Modal de eliminación |

### 💄 Servicios

| Ruta | Descripción |
|---|---|
| `/servicios/` | Vista principal |
| `/servicios/lista/ajax` | Listado server-side |
| `/servicios/crear/` | Modal de creación |
| `/servicios/{id}/detalle/` | Modal de edición |
| `/servicios/{id}/eliminar/` | Modal de eliminación |

### 💰 Pagos y Deudores

| Ruta | Descripción |
|---|---|
| `/pagos/` | Pagos completados (filtro mensual) |
| `/pagos/lista/ajax` | Listado server-side |
| `/deudores/` | Listado de deudores |
| `/deudores/lista/ajax` | Listado server-side |
| `/deudores/{id}/detalle-deudor/` | Modal detalle de deuda |
| `/deudores/{id}/detalle-deudor/pagos` | Historial de abonos |
| `/deudores/{id}/detalle-deudor/agregar-pago/` | Modal para agregar abono |
| `/deudores/{id}/detalle-deudor/servicios/{cita_id}/` | Detalle de servicios |

### 🔐 Autenticación

| Ruta | Descripción |
|---|---|
| `/inicio_sesion/` | Login |
| `/cerrar_sesion/` | Logout |
| `/Perfil/` | Modal de edición de perfil |

## 💾 Modelos de Datos

### Cliente
- `nombre`, `apellido`, `telefono`, `email`, `notas`
- `estado` (activo/inactivo) — soft delete
- Historial de cambios automático
- Managers: `activos`, `inactivos`

### Servicio
- `nombre`, `precio` (Decimal 10,2), `descripcion`, `duracion_estimada` (DurationField)
- `estado` (activo/inactivo) — soft delete
- Historial de cambios automático

### Cita
- `cliente` (FK), `fecha_agenda`, `hora_agenda`, `observaciones`
- `estado`: Pendiente, Confirmada, Cancelada, Completada
- Soft delete + historial
- Propiedades calculadas: `monto_total`, `duracion_total`

### DetalleCita
- `cita` (FK), `servicio` (FK nullable)
- Snapshot: `nombre_servicio`, `precio_servicio`, `duracion_estimada_servicio`
- `precio_acordado`, `cantidad_servicios`, `descuento`, `notas_detalle`
- Restricción: único por combinación cita + servicio

### Pago
- `cita` (OneToOne), `monto_total_cita`, `descuento_total`
- Snapshots: `cliente_nombre`, `fecha_cita`
- `estado_pago`: Pendiente, Completado, Reembolsado, Impago
- `fecha_pago_completado`
- Soft delete + historial

### DetallePago _(inmutable)_
- `pago` (FK), `fecha_pago`, `monto_pago` (mínimo 0.01)
- `metodo_pago`: Efectivo, Tarjeta, Transferencia, Cheque
- `referencia_pago`, `notas_detalle`
- Sin soft delete — los registros financieros no se eliminan

## 🔧 Utilidades Compartidas

- **BaseListViewAjax**: Vista base reutilizable para listados DataTables server-side con paginación, búsqueda, ordenamiento y filtros por formulario
- **CommonCleaner**: Validación de campos alfabéticos, longitud máxima y teléfonos
- **PhoneCleaner**: Validación de teléfonos con prefijos de operador por país (9 países latinoamericanos)
- **DurationInMinutesField**: Campo personalizado para duraciones en minutos
- **CustomDateField / CustomMonthField**: Campos de fecha en formato DD/MM/YYYY y selector de mes
- **format_currency()**: Formateo de moneda chilena (CLP: `$ X.XXX`)
- **format_full_date()**: Fecha en español (ej: "Lunes 5 de Marzo del 2022")

## 🧪 Comandos de Gestión

```bash
# Verificar conectividad, tablas y migraciones pendientes de la BD
python manage.py dbstatus

# Crear migraciones y aplicarlas automáticamente
python manage.py makemigrations_all
```

## 🚀 Instalación

### Opción A: Con Docker (recomendada)

Requiere [Docker Desktop](https://www.docker.com/products/docker-desktop/). Levanta la aplicación y PostgreSQL en contenedores, sin instalar nada más:

```bash
git clone https://github.com/harinsonA/nail-salon-backend.git
cd nail-salon-backend

# Levantar la aplicación + PostgreSQL (primera vez compila la imagen)
docker compose up --build

# En otra terminal: crear el superusuario
docker compose exec web python manage.py createsuperuser
```

La aplicación queda en `http://localhost:8000/`. Las migraciones se aplican automáticamente al arrancar. La configuración vive en `.env.docker` (solo valores de desarrollo).

> Nota: el PostgreSQL del contenedor se expone en el puerto `5433` del host para no chocar con una instalación nativa de PostgreSQL (5432).

### Opción B: Instalación nativa

#### Prerrequisitos

- Python 3.8+
- PostgreSQL 13+
- Git

#### 1. Clonar el repositorio

```bash
git clone https://github.com/harinsonA/nail-salon-backend.git
cd nail-salon-backend
```

#### 2. Crear entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

#### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

#### 4. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` con las credenciales de PostgreSQL:

```env
DATABASE_NAME=manicuredb
DATABASE_USER=tu_usuario
DATABASE_PASSWORD=tu_contraseña
DATABASE_HOST=127.0.0.1
DATABASE_PORT=5432
SECRET_KEY=tu-secret-key
```

#### 5. Crear base de datos y ejecutar migraciones

```bash
createdb manicuredb
python manage.py migrate
```

#### 6. Crear superusuario

```bash
python manage.py createsuperuser
```

#### 7. Ejecutar servidor

```bash
python manage.py runserver
```

Acceder a `http://localhost:8000/` → redirige a `/calendario/` tras iniciar sesión.

## 🚀 Deployment

La aplicación se despliega en [Render](https://render.com) como Web Service con **runtime Docker**: Render construye la imagen desde el `Dockerfile` del repositorio en cada push a `main` y la pone en producción. Las migraciones corren en el Pre-Deploy Command (`python manage.py migrate`), con respaldo en el `entrypoint.sh` de la imagen.

La base de datos es una instancia PostgreSQL administrada de Render (no un contenedor), inyectada vía `DATABASE_URL`.

### Variables de entorno para producción (Dashboard de Render)

```env
DATABASE_URL=postgresql://...   # connection string de la BD administrada
SECRET_KEY=clave-secreta-segura
DEBUG=False                     # opcional: es el default si no se define
```

`ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` se derivan automáticamente de `RENDER_EXTERNAL_HOSTNAME`, que Render inyecta solo.

En cada Pull Request, GitHub Actions compila la imagen y la arranca en modo producción contra un PostgreSQL efímero con un smoke test HTTP (ver `.github/workflows/ci.yml`).

## 🤝 Contribución

1. Fork del proyecto
2. Crear rama: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -m 'Agregar nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

### Guías

- Seguir PEP 8
- Mensajes de commit descriptivos en español
- Actualizar documentación cuando sea necesario

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo [LICENSE](LICENSE) para más detalles.

## 👨‍💻 Autor

**harinsonA** - [GitHub](https://github.com/harinsonA)
