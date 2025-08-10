# 💅 Nail Salon Backend API

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.2+-green.svg)](https://djangoproject.com)
[![DRF](https://img.shields.io/badge/DRF-3.14+-orange.svg)](https://django-rest-framework.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

API REST robusta desarrollada con Django REST Framework para la gestión integral de un salón de uñas. Sistema completo con autenticación, CRUD operations, tests automatizados y documentación de API.

## ✨ Características Principales

### 🔐 Autenticación y Seguridad

- Autenticación basada en tokens
- Permisos granulares por endpoint
- Validaciones de datos robustas

### 👥 Gestión de Clientes

- CRUD completo de clientes
- Validación de emails y teléfonos únicos
- Historial de citas por cliente
- Estados activo/inactivo

### 💄 Catálogo de Servicios

- Gestión de servicios de manicure/pedicure
- Precios y duraciones configurables
- Categorización de servicios

### 📅 Sistema de Citas

- Programación de citas con validaciones
- Estados: programada, confirmada, en_proceso, completada, cancelada
- Asociación cliente-servicio-fecha

### 💰 Gestión de Pagos

- Registro de pagos con múltiples métodos
- Estados: pendiente, completado, cancelado
- Vinculación con citas

### ⚙️ Configuración del Salón

- Configuraciones globales del negocio
- Horarios de atención
- Información de contacto

## 🛠 Tecnologías Utilizadas

- **Backend**: Python 3.8+, Django 4.2+
- **API**: Django REST Framework 3.14+
- **Base de Datos**: PostgreSQL 13+ (Dual: main + test)
- **Autenticación**: Token-based authentication
- **Testing**: Factory Boy, Coverage.py
- **Validaciones**: Custom validators
- **Documentación**: Auto-generated API docs

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
# Crear bases de datos en PostgreSQL
createdb manicuredb
createdb test_manicuredb

# Configurar archivo .env (copiar desde .env.example)
cp .env.example .env
# Editar .env con tus credenciales de base de datos
```

### 5. Ejecutar Migraciones

```bash
# Aplicar migraciones en ambas bases de datos
python manage.py migrate_all

# O individualmente:
python manage.py migrate
python manage.py migrate --database=test_db
```

### 6. Crear Superusuario

```bash
python manage.py createsuperuser
```

### 7. Ejecutar Servidor de Desarrollo

```bash
python manage.py runserver
```

La API estará disponible en: `http://localhost:8000/api/v1/`

## 🧪 Testing

### Ejecutar Tests

```bash
# Todos los tests
python manage.py test

# Tests específicos por aplicación
python manage.py test tests.clients
python manage.py test tests.services
python manage.py test tests.appointments

# Tests con cobertura
coverage run --source='.' manage.py test
coverage report
coverage html
```

### Comandos Personalizados de Base de Datos

```bash
# Estado de ambas bases de datos
python manage.py dbstatus

# Sincronizar base de datos de test
python manage.py sync_test_db

# Crear migraciones y aplicarlas automáticamente
python manage.py makemigrations_all
```

````

3. Activar entorno virtual:

```bash
# Windows
## 📁 Estructura del Proyecto

````

nail-salon-backend/
├── 📁 apps/ # Aplicaciones Django
│ ├── 👥 clients/ # Gestión de clientes
│ │ ├── models/ # Modelos de cliente
│ │ ├── views/ # ViewSets de API
│ │ ├── serializers/ # Serializadores DRF
│ │ └── management/ # Comandos personalizados
│ ├── 💄 services/ # Catálogo de servicios
│ ├── 📅 appointments/ # Sistema de citas
│ ├── 💰 payments/ # Gestión de pagos
│ └── ⚙️ settings/ # Configuraciones del salón
├── 🧪 tests/ # Suite de tests
│ ├── factories/ # Factory Boy factories
│ ├── clients/ # Tests de clientes
│ ├── services/ # Tests de servicios
│ └── utils.py # Utilidades de testing
├── 🛠 utils/ # Utilidades compartidas
│ ├── validators.py # Validadores custom
│ ├── permissions.py # Permisos personalizados
│ └── pagination.py # Paginación custom
├── 📁 nail_salon_api/ # Configuración principal
├── 📋 requirements.txt # Dependencias Python
├── 🔧 manage.py # CLI de Django
└── 📝 .env.example # Variables de entorno ejemplo

````

## 📊 API Endpoints

### 👥 Clientes (`/api/v1/clientes/`)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/` | Listar clientes con paginación y filtros |
| `POST` | `/` | Crear nuevo cliente |
| `GET` | `/{id}/` | Obtener cliente por ID |
| `PUT` | `/{id}/` | Actualizar cliente completo |
| `PATCH` | `/{id}/` | Actualizar cliente parcial |
| `DELETE` | `/{id}/` | Eliminar cliente |
| `POST` | `/{id}/desactivar/` | Desactivar cliente |
| `POST` | `/{id}/activar/` | Activar cliente |

### 💄 Servicios (`/api/v1/servicios/`)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/` | Listar servicios disponibles |
| `POST` | `/` | Crear nuevo servicio |
| `GET` | `/{id}/` | Obtener servicio por ID |
| `PUT/PATCH` | `/{id}/` | Actualizar servicio |
| `DELETE` | `/{id}/` | Eliminar servicio |

### 📅 Citas (`/api/v1/citas/`)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/` | Listar citas con filtros de fecha |
| `POST` | `/` | Programar nueva cita |
| `GET` | `/{id}/` | Obtener cita por ID |
| `PUT/PATCH` | `/{id}/` | Actualizar cita |
| `DELETE` | `/{id}/` | Cancelar cita |

### 💰 Pagos (`/api/v1/pagos/`)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/` | Listar pagos |
| `POST` | `/` | Registrar nuevo pago |
| `GET` | `/{id}/` | Obtener pago por ID |
| `PUT/PATCH` | `/{id}/` | Actualizar pago |

## 🔐 Autenticación

### Obtener Token
```bash
POST /api/v1/auth/login/
{
    "username": "tu_usuario",
    "password": "tu_password"
}
````

### Usar Token en Requests

```bash
curl -H "Authorization: Token your_token_here" \
     http://localhost:8000/api/v1/clientes/
```

## 📈 Características Avanzadas

### 🔍 Filtros y Búsqueda

```bash
# Buscar clientes por nombre o email
GET /api/v1/clientes/?search=ana

# Filtrar por estado activo
GET /api/v1/clientes/?activo=true

# Ordenar por fecha de registro
GET /api/v1/clientes/?ordering=-fecha_registro
```

### 📄 Paginación

```bash
# Paginación automática
GET /api/v1/clientes/?page=2&page_size=10
```

### ✅ Validaciones

- Emails únicos por cliente
- Teléfonos únicos por cliente
- Validación de formato de teléfono colombiano
- Validación de fechas de citas futuras
- Validación de estados de cita válidos

## 🎯 Casos de Uso

### Crear Cliente y Agendar Cita

```python
# 1. Crear cliente
POST /api/v1/clientes/
{
    "nombre": "Ana",
    "apellido": "García",
    "telefono": "3001234567",
    "email": "ana@email.com"
}

# 2. Agendar cita
POST /api/v1/citas/
{
    "cliente": 1,
    "servicio": 1,
    "fecha_hora_cita": "2025-08-10T14:00:00",
    "estado": "programada"
}

# 3. Registrar pago
POST /api/v1/pagos/
{
    "cita": 1,
    "monto": 25000,
    "metodo_pago": "efectivo",
    "estado": "completado"
}
```

## 🚀 Deployment

### Variables de Entorno Producción

```bash
DEBUG=False
DATABASE_URL=postgresql://user:pass@localhost/manicuredb
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

### Docker (Opcional)

```dockerfile
# Dockerfile ejemplo
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "nail_salon_api.wsgi:application"]
```

## 🤝 Contribución

1. 🍴 **Fork** el proyecto
2. 🌱 **Crear rama**: `git checkout -b feature/nueva-funcionalidad`
3. 💾 **Commit**: `git commit -m 'Agregar nueva funcionalidad'`
4. 📤 **Push**: `git push origin feature/nueva-funcionalidad`
5. 🔄 **Pull Request**: Crear PR desde GitHub

### 📋 Guías de Contribución

- Seguir PEP 8 para estilo de código Python
- Escribir tests para nuevas funcionalidades
- Actualizar documentación cuando sea necesario
- Usar mensajes de commit descriptivos

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo [LICENSE](LICENSE) para más detalles.

## 👨‍💻 Autor

**harinsonA** - [GitHub](https://github.com/harinsonA)

## 🙏 Agradecimientos

- Django REST Framework por la excelente documentación
- Factory Boy por facilitar la creación de datos de prueba
- PostgreSQL por la robustez en base de datos

---

⭐ **¡Dale una estrella al proyecto si te ha sido útil!** ⭐
