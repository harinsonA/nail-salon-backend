# 💅 Nail Salon Backend

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.2+-green.svg)](https://djangoproject.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://postgresql.org)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5+-purple.svg)](https://getbootstrap.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Sistema web robusto desarrollado con Django para la gestión integral de un salón de uñas. Aplicación web tradicional con vistas basadas en templates, modales Bootstrap y AJAX para una experiencia de usuario fluida.

## ✨ Características Principales

### 🔐 Autenticación y Seguridad

- Sistema de autenticación Django nativo
- Gestión de usuarios con permisos
- Sesiones seguras
- Validaciones de datos robustas

### 👥 Gestión de Clientes

- CRUD completo de clientes
- Validación de emails y teléfonos
- Interfaz con modales Bootstrap
- Estados activo/inactivo
- Listados AJAX con paginación

### 💄 Catálogo de Servicios

- Gestión completa de servicios
- Precios y duraciones configurables
- Interfaz intuitiva con modales
- Operaciones CRUD vía AJAX

### 📅 Sistema de Citas (Agenda)

- Programación de citas con validaciones
- Estados: PENDIENTE, CONFIRMADA, COMPLETADA, CANCELADA
- Validación de horarios disponibles
- Asociación cliente-servicio-fecha
- Interfaz de agenda interactiva

### 💰 Gestión de Pagos

- Registro de pagos con múltiples métodos
- Métodos: EFECTIVO, TARJETA, TRANSFERENCIA, CHEQUE
- Estados: PAGADO, PENDIENTE, CANCELADO
- Vinculación con citas

### ⚙️ Configuración del Salón

- Configuraciones globales del negocio
- Galería de imágenes
- Información "Sobre Nosotros"
- Servicios destacados

## 🛠 Tecnologías Utilizadas

- **Backend**: Python 3.8+, Django 4.2+
- **Frontend**: HTML5, Bootstrap 5, JavaScript (AJAX)
- **Base de Datos**: PostgreSQL 13+
- **Autenticación**: Django Auth System
- **UI Components**: django-bootstrap-modal-forms
- **Validaciones**: Custom validators y cleaners
- **Arquitectura**: MVT (Model-View-Template)

## 🚀 Instalación y Configuración

### Prerrequisitos

- Python 3.8+
- PostgreSQL 13+
- Git

### 1. Clonar el Repositorio

```bash
git clone https://github.com/harinsonA/nail-salon-backend.git
cd nail-salon-backend
```

### 2. Configurar Entorno Virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Base de Datos

```bash
# Crear base de datos en PostgreSQL
createdb manicuredb

# Configurar archivo .env (copiar desde .env.example)
cp .env.example .env
# Editar .env con tus credenciales de base de datos
```

### 5. Ejecutar Migraciones

```bash
python manage.py migrate
```

### 6. Crear Superusuario

```bash
python manage.py createsuperuser
```

### 7. Ejecutar Servidor de Desarrollo

```bash
python manage.py runserver
```

La aplicación estará disponible en: `http://localhost:8000/`

## 📁 Estructura del Proyecto

```
nail-salon-backend/
├── 📁 apps/                    # Aplicaciones Django
│   ├── 👥 clients/             # Gestión de clientes
│   │   ├── models/             # Modelos de cliente
│   │   ├── views/              # Vistas web con modales
│   │   ├── templates/          # Templates HTML
│   │   └── urls.py             # URLs de clientes
│   ├── 💄 services/            # Catálogo de servicios
│   │   ├── models/             # Modelos de servicio
│   │   ├── views/              # Vistas web
│   │   └── urls.py             # URLs de servicios
│   ├── 📅 appointments/        # Sistema de citas
│   │   ├── models/             # Modelos de cita
│   │   ├── views/              # Vistas de agenda
│   │   └── urls.py             # URLs de citas
│   ├── 💰 payments/            # Gestión de pagos
│   │   ├── models/             # Modelos de pago
│   │   ├── choices.py          # Constantes (Estados, Métodos)
│   │   └── views/              # Vistas de pagos
│   ├── ⚙️ settings/            # Configuraciones del salón
│   │   ├── about_us/           # Sobre nosotros
│   │   ├── gallery/            # Galería de imágenes
│   │   └── services_to_show/   # Servicios destacados
│   └── 🔧 common/              # Utilidades compartidas
│       ├── utils/              # CommonCleaner, PhoneCleaner
│       ├── base_list_view_ajax.py  # Vista base para AJAX
│       └── custom_time_fields.py   # Campos personalizados
├── 📁 templates/               # Templates globales
│   ├── base.html               # Template base
│   ├── menu.html               # Menú de navegación
│   ├── bs_modal.html           # Modal Bootstrap
│   └── canvas_modal.html       # Modal canvas
├── 📁 static/                  # Archivos estáticos
│   ├── css/                    # Estilos CSS
│   ├── js/                     # JavaScript
│   ├── images/                 # Imágenes
│   └── fonts/                  # Fuentes
├── 📁 nail_salon_api/          # Configuración principal
│   ├── settings.py             # Configuración Django
│   ├── urls.py                 # URLs principales
│   └── wsgi.py                 # WSGI config
├── 📋 requirements.txt         # Dependencias Python
└── 🔧 manage.py                # CLI de Django
```

## 🌐 Rutas Web Principales

### 👥 Clientes

- `/clientes/` - Vista principal de clientes
- `/clientes/lista/ajax` - Listado AJAX
- `/clientes/crear/` - Modal crear cliente
- `/clientes/{id}/detalle/` - Modal detalle cliente
- `/clientes/{id}/eliminar/` - Modal eliminar cliente

### 💄 Servicios

- `/servicios/` - Vista principal de servicios
- `/servicios/lista/ajax` - Listado AJAX
- `/servicios/crear/` - Modal crear servicio
- `/servicios/{id}/detalle/` - Modal detalle servicio
- `/servicios/{id}/eliminar/` - Modal eliminar servicio

### 📅 Agenda (Citas)

- `/agenda/` - Vista principal de agenda
- `/agenda/lista/ajax/` - Listado AJAX de citas
- `/agenda/crear/` - Modal crear cita
- `/agenda/servicio/detalles/ajax/` - Obtener detalles de servicio
- `/agenda/horas/disponibles/ajax/` - Validar horas disponibles

## ✨ Características Técnicas

### 🎨 Interfaz de Usuario

- **Modales Bootstrap**: Operaciones CRUD sin recargar página
- **AJAX**: Listados dinámicos y validaciones en tiempo real
- **Responsive Design**: Compatible con dispositivos móviles
- **Formularios Validados**: Validación cliente y servidor

### 🔧 Validaciones y Utilidades

- **CommonCleaner**: Validación de campos alfabéticos, teléfonos, longitud
- **PhoneCleaner**: Validación de números telefónicos con prefijos
- **Custom Fields**: DurationInMinutesField, CustomMonthField, CustomDateField
- **BaseListViewAjax**: Vista base reutilizable para listados AJAX

### 💾 Modelos de Datos

**Cliente**:

- nombre, apellido, teléfono, email
- activo (soft delete)
- fecha_registro, fecha_actualizacion

**Servicio**:

- nombre, precio, descripción
- duracion_estimada
- activo (soft delete)

**Cita**:

- cliente (FK), fecha_agenda, hora_agenda
- estado (PENDIENTE, CONFIRMADA, COMPLETADA, CANCELADA)
- observaciones

**Pago**:

- cita (FK), fecha_pago, monto_total
- metodo_pago (EFECTIVO, TARJETA, TRANSFERENCIA, CHEQUE)
- estado_pago (PAGADO, PENDIENTE, CANCELADO)

## 🚀 Deployment

### Variables de Entorno Producción

```bash
DEBUG=False
DATABASE_URL=postgresql://user:pass@localhost/manicuredb
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=yourdomain.com
```

## 🤝 Contribución

1. 🍴 **Fork** el proyecto
2. 🌱 **Crear rama**: `git checkout -b feature/nueva-funcionalidad`
3. 💾 **Commit**: `git commit -m 'Agregar nueva funcionalidad'`
4. 📤 **Push**: `git push origin feature/nueva-funcionalidad`
5. 🔄 **Pull Request**: Crear PR desde GitHub

### 📋 Guías de Contribución

- Seguir PEP 8 para estilo de código Python
- Escribir código limpio y documentado
- Actualizar documentación cuando sea necesario
- Usar mensajes de commit descriptivos

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo [LICENSE](LICENSE) para más detalles.

## 👨‍💻 Autor

**harinsonA** - [GitHub](https://github.com/harinsonA)

---

⭐ **¡Dale una estrella al proyecto si te ha sido útil!** ⭐
