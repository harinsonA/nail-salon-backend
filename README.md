# 💅 Nail Salon Backend

[![CI](https://github.com/harinsonA/nail-salon-backend/actions/workflows/ci.yml/badge.svg)](https://github.com/harinsonA/nail-salon-backend/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](https://www.docker.com/)
[![Django](https://img.shields.io/badge/Django-4.2-green.svg)](https://djangoproject.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://postgresql.org)
[![Celery](https://img.shields.io/badge/Celery-5.5-green.svg)](https://docs.celeryq.dev/)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3.3-purple.svg)](https://getbootstrap.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Sistema web para la gestión integral de un salón de uñas, desarrollado con Django. Combina vistas server-rendered con modales Bootstrap y AJAX para ofrecer una experiencia fluida sin recargas de página. El flujo principal es: **Calendario → Agenda diaria → Citas → Pagos**, con un **Dashboard** de métricas del negocio y procesos pesados que corren en segundo plano con Celery.

## ✨ Características Principales

### 🔐 Autenticación, Sesión y Perfil

- Login/Logout con sistema de autenticación nativo de Django
- Edición de perfil (nombre, apellido, email, username) vía modal
- Cambio de contraseña con verificación de contraseña actual
- Redirección automática al calendario tras iniciar sesión
- **Cierre de sesión por inactividad**, con tres relojes independientes:
  - **Inactividad configurable** por la usuaria (15 min a 4 h, o "no cerrar"), por defecto 2 horas
  - **Corte diario** a las 4 AM (`SESSION_DAILY_CUTOFF_HOUR`), que no se puede desactivar y garantiza un login por jornada
  - **Cierre del navegador**: la cookie de sesión no se guarda en disco
- Aviso en pantalla "¿Sigues ahí?" dos minutos antes, con cuenta regresiva y opción de seguir conectada
- Respuesta diferenciada ante una sesión vencida: redirección al login en navegación normal, `401` con JSON en peticiones AJAX

### 📅 Calendario y Agenda

- **Vista mensual**: Calendario interactivo que muestra la cantidad de citas pendientes y completadas por día
- **Vista diaria (Agenda)**: Listado de citas del día seleccionado con acciones contextuales según el estado de cada cita
- **Creación de citas**: Formulario de página completa que permite crear múltiples citas en lote, cada una con un cliente y varios servicios
- **Selección de servicios por categoría**: consulta AJAX que filtra el catálogo al elegir una categoría
- **Validación de horarios**: Consulta AJAX de horas ocupadas para evitar solapamientos
- **Contacto por WhatsApp**: acceso directo para escribirle a la clienta desde la agenda del día
- **Flujo de estados**: Pendiente → Completada / Cancelada, con opción de restaurar citas canceladas

### 👥 Gestión de Clientes

- CRUD completo mediante modales Bootstrap (crear, editar, eliminar)
- Listado server-side con DataTables: búsqueda, paginación y ordenamiento
- Filtro por estado (todos / activos / inactivos)
- **Modal de WhatsApp**: mensaje prellenado con el nombre de la clienta y enlaces a WhatsApp Web o a la aplicación
- Validación de teléfonos por país (Argentina, Chile, Colombia, Ecuador, México, Perú, Rep. Dominicana, Uruguay, Venezuela)
- Soft delete (eliminación lógica) con historial de cambios

### 💄 Catálogo de Servicios y Categorías

- CRUD completo de servicios y categorías mediante modales Bootstrap
- Precio, descripción, duración estimada y categoría configurables por servicio
- Duración mostrada en formato legible (ej: "1h 30m")
- Aviso que recomienda crear categorías antes que servicios cuando el catálogo está vacío
- Listado AJAX con filtro por estado activo/inactivo
- Soft delete con historial de cambios

### 💰 Gestión de Pagos, Ingresos y Deudores

- **Confirmación de cita = Creación de pago**: Al completar una cita se genera automáticamente el registro de pago con sus detalles
- **Abonos parciales**: Soporte para pagos parciales (señas/anticipos) que generan deudas rastreables
- **Vista de pagos completados**: Listado mensual con totales facturados, descontados y cobrados
- **Vista de ingresos**: Listado por rango de fechas, con filtro por método de pago y gráfico de ingresos por método
- **Vista de deudores**: Listado de pagos pendientes con saldo calculado (total - abonos)
- **Detalle de deuda**: Modal con desglose de servicios y historial de pagos parciales
- **Gráfico de ingresos por semana**: Barras con los ingresos de cada semana del mes seleccionado
- **Métodos de pago**: Efectivo, Tarjeta, Transferencia, Cheque
- **Estados de pago**: Pendiente, Completado, Reembolsado, Impago
- **Registros financieros inmutables**: Los detalles de pago no tienen soft delete

### 📊 Dashboard de Métricas

- Panel en `/dashboard/` con gráficos interactivos (Chart.js), cada uno con su propio endpoint AJAX:
  - Clientes atendidos
  - Ingresos
  - Estado de citas (pendientes / completadas / canceladas)
  - Métodos de pago
  - Servicios más solicitados
  - Ingresos por categoría
- Filtros por período reutilizables entre gráficos

### 📤 Exportación e Importación

- **Exportación a Excel** (openpyxl) con estilos de marca: clientes, servicios, categorías, pagos, ingresos y deudores
- **Importación masiva por CSV**: clientes, servicios y categorías
- La importación es **asíncrona**: la vista solo valida el archivo (extensión, peso, codificación), registra el proceso y encola; la validación de filas y el guardado ocurren dentro del worker
- Plantilla de ejemplo descargable por cada tipo de importación
- Reporte detallado de errores por fila, consultable desde la vista de procesos

### ⚙️ Procesos en Segundo Plano

- Vista `/procesos/` con el estado de cada proceso: Pendiente, En proceso, Completado o Fallido, con porcentaje de avance
- Modal de detalle para los procesos fallidos, con el motivo y los errores por fila
- Cada proceso registra quién lo disparó, el origen, los datos de entrada y la metadata del resultado
- Decorador `@background_task`: compone el seguimiento y la tarea de Celery, y garantiza que un proceso que revienta quede **Fallido** con su detalle, nunca "En proceso" para siempre

### 🎛 Preferencias del Sistema

- Gestor de preferencias en `apps/settings`: tabla clave-valor con el valor en **JSONB**, así cada preferencia conserva su tipo real (número, booleano, lista o diccionario)
- **Registro único de definiciones** en código: agregar una preferencia es una entrada, no una migración de esquema
- Alcance por `scope` + `scope_id`: preferencias de la usuaria y, cuando haga falta, del salón
- Tipos disponibles: booleano, entero, opción, texto y JSON, cada uno con su validación y su campo de formulario
- Sin fila en la base, la lectura cae al valor por defecto de la definición
- Auditoría de cada escritura con django-simple-history
- Los formularios piden los campos de una categoría al registro y los dibujan solos: hoy la única preferencia (`session_idle_minutes`) vive en el modal de Perfil
- _Pendiente_: la configuración del salón propiamente tal (Sobre Nosotros, Galería, Servicios destacados) sigue sin implementar

## 🛠 Tecnologías

| Categoría | Tecnología |
|---|---|
| **Backend** | Python 3.12, Django 4.2 |
| **Infraestructura** | Docker (imagen `python:3.12.8-slim`), Render, GitHub Actions (CI) |
| **Base de Datos** | PostgreSQL 13+ |
| **Tareas en segundo plano** | Celery 5.5 + Redis 7 (broker y result backend) |
| **Resultados tipados** | result 0.17 (`Ok` / `Err`) |
| **Frontend** | Bootstrap 5.3.3, jQuery 3.7.1 |
| **Tablas** | DataTables 2.3.4 (server-side, responsive, fixed columns) |
| **Gráficos** | Chart.js 4.5 |
| **Exportación Excel** | openpyxl 3.1.5 |
| **Modales** | django-bootstrap-modal-forms |
| **Historial** | django-simple-history |
| **Soft Delete** | django-model-utils (SoftDeletableModel) |
| **Notificaciones** | Toastify 1.12.0 |
| **Datepickers** | Bootstrap Datepicker 1.10.0 (locale español) |
| **Iconos** | Google Material Symbols (auto-hospedados) + SVG internos |
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
│   │   ├── views/             # CRUD con modales, listado AJAX, WhatsApp, import CSV
│   │   ├── imports.py         # Definición de la importación CSV de clientes
│   │   ├── tasks.py           # Tarea Celery de importación
│   │   ├── management/commands/  # dbstatus, makemigrations_all
│   │   └── templates/
│   ├── services/              # Catálogo de servicios y categorías
│   │   ├── models/            # Servicio (precio, duración, categoría), Categoria
│   │   ├── views/             # CRUD con modales, listado AJAX, import CSV
│   │   ├── imports.py         # Importación CSV de servicios y categorías
│   │   ├── tasks.py           # Tareas Celery de importación
│   │   └── templates/
│   ├── payments/              # Pagos, ingresos y deudores
│   │   ├── models/            # Pago, DetallePago (inmutable)
│   │   ├── choices.py         # EstadoCita, MetodoPago, EstadoPago
│   │   ├── views/
│   │   │   ├── payments/      # Pagos completados (listado mensual)
│   │   │   ├── incomes/       # Ingresos por rango de fechas y método de pago
│   │   │   ├── charts/        # Endpoints de los gráficos de ingresos
│   │   │   └── debtors/       # Deudores, detalle de deuda, agregar abono
│   │   └── templates/
│   ├── profiles/              # Autenticación, sesión y perfil de usuario
│   │   ├── views/
│   │   │   ├── login/         # Login y Logout
│   │   │   ├── profile/       # Perfil, contraseña y preferencias de seguridad
│   │   │   └── session/       # Ping que mantiene viva la sesión
│   │   ├── signals.py         # Abre la ventana de sesión al iniciar sesión
│   │   └── templates/
│   ├── tareas/                # Procesos en segundo plano
│   │   ├── models.py          # TareaEnProceso (estado, progreso, metadata)
│   │   ├── decorators.py      # background_task / tracked_task
│   │   ├── views.py           # Listado de procesos y modal de detalle
│   │   └── templates/
│   ├── settings/              # Configuración del sistema
│   │   ├── models.py          # ConfiguracionSalon (pendiente) + Preference
│   │   └── preferences/       # Gestor de preferencias
│   │       ├── constants.py   # Scope y Category
│   │       ├── models.py      # Preference (scope, scope_id, key, value JSONB)
│   │       ├── types.py       # Boolean / Integer / Choice / Text / Json
│   │       ├── registry.py    # Catálogo único de definiciones
│   │       ├── service.py     # get / get_preferences / set
│   │       └── forms.py       # Campos generados por categoría
│   └── common/                # Utilidades compartidas
│       ├── base_list_view_ajax.py  # Vista base para DataTables server-side
│       ├── middleware.py           # Vencimiento de sesión (inactividad + corte diario)
│       ├── context_processors.py   # Expone el tiempo de inactividad a las plantillas
│       ├── custom_time_fields.py   # DurationInMinutesField, CustomDateField
│       ├── widgets.py              # DatePickerWidget, MonthPickerWidget
│       ├── views/base_views.py     # ProtectedView / ProtectedAjaxView / ProtectedExportView
│       ├── exports/                # ExcelColumn, ExcelExportMixin, estilos de marca
│       ├── imports/                # Formulario, validadores y vista base de import asíncrono
│       └── utils/                  # CommonCleaner, PhoneCleaner, WhatsApp, formateo
├── dashboard/                 # Dashboard de métricas (raíz redirige a /calendario/)
│   ├── services/              # Cálculo de métricas y períodos
│   └── views/charts/          # Un endpoint AJAX por gráfico
├── templates/                 # Templates globales (base, menú, modales, imports)
├── static/
│   ├── css/custom/            # Estilos personalizados
│   ├── images/                # Iconos SVG internos
│   ├── js/custom/             # DataTables, modales, datepickers, AJAX, sesión, dashboard
│   └── js/libs/               # Bootstrap, jQuery, DataTables, Chart.js, Toastify
└── nail_salon_api/            # Configuración Django (settings, urls, wsgi, celery)
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
| `/agenda/servicios/por-categoria/ajax/` | Servicios de una categoría |
| `/agenda/horas/disponibles/ajax/` | Horas ocupadas de una fecha |

### 👥 Clientes

| Ruta | Descripción |
|---|---|
| `/clientes/` | Vista principal |
| `/clientes/lista/ajax` | Listado server-side |
| `/clientes/exportar/` | Exportar clientes a Excel |
| `/clientes/importar/` | Importación masiva por CSV |
| `/clientes/importar/plantilla/` | Descargar plantilla de ejemplo |
| `/clientes/crear/` | Modal de creación |
| `/clientes/{id}/detalle/` | Modal de edición |
| `/clientes/{id}/whatsapp/` | Modal para escribir por WhatsApp |
| `/clientes/{id}/eliminar/` | Modal de eliminación |

### 💄 Servicios y Categorías

| Ruta | Descripción |
|---|---|
| `/servicios/` | Vista principal |
| `/servicios/lista/ajax` | Listado server-side |
| `/servicios/exportar/` | Exportar servicios a Excel |
| `/servicios/importar/` | Importación masiva por CSV |
| `/servicios/importar/plantilla/` | Descargar plantilla de ejemplo |
| `/servicios/crear/` | Modal de creación |
| `/servicios/{id}/detalle/` | Modal de edición |
| `/servicios/{id}/eliminar/` | Modal de eliminación |
| `/categorias/` | Vista principal de categorías |
| `/categorias/lista/ajax` | Listado server-side |
| `/categorias/exportar/` | Exportar categorías a Excel |
| `/categorias/importar/` | Importación masiva por CSV |
| `/categorias/importar/plantilla/` | Descargar plantilla de ejemplo |
| `/categorias/crear/` | Modal de creación |
| `/categorias/{id}/detalle/` | Modal de edición |
| `/categorias/{id}/eliminar/` | Modal de eliminación |

### 💰 Pagos, Ingresos y Deudores

| Ruta | Descripción |
|---|---|
| `/pagos/` | Pagos completados (filtro mensual) |
| `/pagos/lista/ajax` | Listado server-side |
| `/pagos/exportar/` | Exportar pagos a Excel |
| `/pagos/ingresos-semana/ajax` | Datos del gráfico de ingresos por semana |
| `/ingresos/` | Ingresos por rango de fechas |
| `/ingresos/lista/ajax` | Listado server-side |
| `/ingresos/exportar/` | Exportar ingresos a Excel |
| `/ingresos/por-metodo/ajax` | Datos del gráfico de ingresos por método de pago |
| `/deudores/` | Listado de deudores |
| `/deudores/lista/ajax` | Listado server-side |
| `/deudores/exportar/` | Exportar deudores a Excel |
| `/deudores/{id}/detalle-deudor/` | Modal detalle de deuda |
| `/deudores/{id}/detalle-deudor/pagos` | Historial de abonos |
| `/deudores/{id}/detalle-deudor/agregar-pago/` | Modal para agregar abono |
| `/deudores/{id}/detalle-deudor/servicios/{cita_id}/` | Detalle de servicios |

### 📊 Dashboard

| Ruta | Descripción |
|---|---|
| `/dashboard/` | Panel de métricas del negocio |
| `/dashboard/clientes-atendidos/ajax/` | Datos del gráfico de clientes atendidos |
| `/dashboard/ingresos/ajax/` | Datos del gráfico de ingresos |
| `/dashboard/estado-citas/ajax/` | Datos del gráfico de estado de citas |
| `/dashboard/metodos-pago/ajax/` | Datos del gráfico de métodos de pago |
| `/dashboard/servicios-top/ajax/` | Datos del gráfico de servicios más solicitados |
| `/dashboard/ingresos-categoria/ajax/` | Datos del gráfico de ingresos por categoría |

### ⚙️ Procesos en Segundo Plano

| Ruta | Descripción |
|---|---|
| `/procesos/` | Listado de procesos con su estado y avance |
| `/procesos/lista/ajax` | Listado server-side |
| `/procesos/{id}/detalle/` | Modal de detalle (motivo del fallo y errores por fila) |

### 🔐 Autenticación y Sesión

| Ruta | Descripción |
|---|---|
| `/inicio_sesion/` | Login (muestra un aviso si la sesión venció) |
| `/cerrar_sesion/` | Logout |
| `/Perfil/` | Modal de perfil, contraseña y preferencias de seguridad |
| `/sesion/ping/` | Mantiene viva la sesión desde el aviso de inactividad |

## 💾 Modelos de Datos

### Cliente
- `nombre`, `apellido`, `telefono`, `email`, `notas`
- `estado` (activo/inactivo) — soft delete
- Historial de cambios automático
- Managers: `activos`, `inactivos`

### Categoria
- `nombre`, `descripcion`
- `estado` (activo/inactivo) — soft delete
- Historial de cambios automático
- Managers: `activos`, `inactivos`

### Servicio
- `nombre`, `precio` (Decimal 10,2), `descripcion`, `duracion_estimada` (DurationField)
- `categoria` (FK nullable a Categoria)
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

### TareaEnProceso
- `nombre_proceso`, `origen`, `celery_task_id`, `user_id`
- `estado`: Pendiente, En proceso, Completado, Fallido
- `progreso_actual` / `total_registros`, con propiedad `porcentaje`
- `datos_entrada` y `resultado_metadata` (JSON), `finalizado_en`

### Preference
- `scope` (usuario / salón) + `scope_id`, `key`, `value` (JSONB)
- Único por combinación `scope` + `scope_id` + `key`
- Historial de cambios automático
- El tipo, el valor por defecto y la validación viven en el registro de definiciones, no en la tabla

## 🔧 Utilidades Compartidas

- **ProtectedView / ProtectedAjaxView / ProtectedExportView**: bases de vistas protegidas. Una sola validación decide el tipo de respuesta ante una sesión no válida: redirección al login o `401` con JSON, según quién pregunte
- **SessionExpiryMiddleware**: vencimiento de la sesión por inactividad y por corte diario
- **Preferencias**: registro de definiciones tipadas y servicio `get` / `get_preferences` / `set`, con lectura en lote en una sola consulta
- **background_task**: decorador que convierte una función en tarea de Celery con seguimiento en `TareaEnProceso`
- **BaseListViewAjax**: Vista base reutilizable para listados DataTables server-side con paginación, búsqueda, ordenamiento y filtros por formulario
- **ExcelExportMixin / ExcelColumn**: Base de exportación a Excel con estilos de marca (openpyxl)
- **Import CSV base**: Formulario, validadores por columna y vista base asíncrona reutilizados por clientes, servicios y categorías
- **CommonCleaner**: Validación de campos alfabéticos, longitud máxima y teléfonos
- **PhoneCleaner**: Validación de teléfonos con prefijos de operador por país (9 países latinoamericanos)
- **get_whatsapp_url()**: Armado del enlace a WhatsApp Web o a la aplicación, con mensaje prellenado
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

# Borrar las sesiones vencidas de la tabla django_session
python manage.py clearsessions
```

## 🚀 Instalación

### Opción A: Con Docker (recomendada)

Requiere [Docker Desktop](https://www.docker.com/products/docker-desktop/). Levanta la aplicación, PostgreSQL, Redis y el worker de Celery en contenedores, sin instalar nada más:

```bash
git clone https://github.com/harinsonA/nail-salon-backend.git
cd nail-salon-backend

# Levantar todos los servicios (primera vez compila la imagen)
docker compose up --build

# En otra terminal: crear el superusuario
docker compose exec web python manage.py createsuperuser
```

La aplicación queda en `http://localhost:8000/`. Las migraciones se aplican automáticamente al arrancar. La configuración vive en `.env.docker` (solo valores de desarrollo).

Servicios que levanta `docker compose`:

| Servicio | Para qué |
|---|---|
| `db` | PostgreSQL 15 |
| `redis` | Broker y result backend de Celery |
| `web` | La aplicación Django |
| `worker` | Worker de Celery que procesa las importaciones |

> Nota: el PostgreSQL del contenedor se expone en el puerto `5433` del host para no chocar con una instalación nativa de PostgreSQL (5432). Redis se expone en el `6379` para poder usarlo también desde un `runserver` nativo.

### Opción B: Instalación nativa

#### Prerrequisitos

- Python 3.8+
- PostgreSQL 13+
- Redis (solo si quieres procesar las tareas en segundo plano de verdad)
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

#### 8. Ejecutar el worker de Celery (opcional)

```bash
celery -A nail_salon_api worker --loglevel=info

# En Windows hay que agregar el pool solo
celery -A nail_salon_api worker --loglevel=info --pool=solo
```

Si no quieres levantar Redis ni el worker, define `CELERY_TASK_ALWAYS_EAGER=True` en el `.env`: las tareas corren dentro del request, de forma síncrona. Es el modo cómodo para desarrollo, y sirve de interruptor de emergencia.

Acceder a `http://localhost:8000/` → redirige a `/calendario/` tras iniciar sesión.

## ⚙️ Variables de Entorno

| Variable | Por defecto | Para qué |
|---|---|---|
| `SECRET_KEY` | clave de desarrollo | Clave criptográfica de Django |
| `DEBUG` | `False` | Modo depuración |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Hosts permitidos |
| `CSRF_TRUSTED_ORIGINS` | vacío | Orígenes confiables para CSRF |
| `DATABASE_URL` | vacío | Connection string; tiene prioridad sobre las `DATABASE_*` |
| `DATABASE_NAME` / `USER` / `PASSWORD` / `HOST` / `PORT` | `manicuredb`, `postgres`, vacío, `127.0.0.1`, `5432` | Conexión a PostgreSQL |
| `REDIS_URL` | `redis://localhost:6379/0` | Broker y result backend de Celery |
| `CELERY_TASK_ALWAYS_EAGER` | `False` | `True` ejecuta las tareas de forma síncrona, sin worker ni Redis |
| `SESSION_DAILY_CUTOFF_HOUR` | `4` | Hora del corte diario de sesión |

## 🚀 Deployment

La aplicación se despliega en [Render](https://render.com) como Web Service con **runtime Docker**: Render construye la imagen desde el `Dockerfile` del repositorio en cada push a `main` y la pone en producción. Las migraciones corren en el Pre-Deploy Command (`python manage.py migrate`), con respaldo en el `entrypoint.sh` de la imagen, que además limpia las sesiones vencidas con `clearsessions`.

La base de datos es una instancia PostgreSQL administrada de Render (no un contenedor), inyectada vía `DATABASE_URL`.

Para que las importaciones corran realmente en segundo plano hacen falta dos servicios más en la misma región: una instancia **Key Value (Redis)** como broker y un **Background Worker** que ejecute `celery -A nail_salon_api worker`. Mientras no existan, `CELERY_TASK_ALWAYS_EAGER=True` mantiene el procesamiento síncrono dentro del request.

### Variables de entorno para producción (Dashboard de Render)

```env
DATABASE_URL=postgresql://...   # connection string de la BD administrada
SECRET_KEY=clave-secreta-segura
DEBUG=False                     # opcional: es el default si no se define
REDIS_URL=redis://...           # Internal URL de la instancia Key Value
CELERY_TASK_ALWAYS_EAGER=True   # mientras no exista el worker
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
