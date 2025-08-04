# Nail Salon Backend

API REST desarrollada con Django REST Framework para la gestión integral de un salón de uñas.

## Características

- Gestión de clientes
- Catálogo de servicios
- Sistema de citas
- Gestión de pagos
- Panel de administración
- API REST completa

## Tecnologías

- Python 3.8+
- Django 4.2+
- Django REST Framework
- SQLite (desarrollo) / PostgreSQL (producción)

## Instalación

1. Clonar el repositorio
2. Crear entorno virtual:

```bash
python -m venv venv
```

3. Activar entorno virtual:

```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

4. Instalar dependencias:

```bash
pip install -r requirements.txt
```

5. Configurar variables de entorno:

```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

6. Ejecutar migraciones:

```bash
python manage.py makemigrations
python manage.py migrate
```

7. Crear superusuario:

```bash
python manage.py createsuperuser
```

8. Ejecutar servidor:

```bash
python manage.py runserver
```

## Estructura del Proyecto

```
nail-salon-backend/
├── manage.py
├── requirements.txt
├── .env.example
├── nail_salon_api/          # Configuración principal
├── apps/                    # Aplicaciones
│   ├── clients/            # Gestión de clientes
│   ├── services/           # Catálogo de servicios
│   ├── appointments/       # Sistema de citas
│   ├── payments/           # Gestión de pagos
│   └── settings/           # Configuraciones
└── utils/                  # Utilidades compartidas
```

## Endpoints API

### Clientes

- `GET /api/v1/clientes/` - Listar clientes
- `POST /api/v1/clientes/` - Crear cliente
- `GET /api/v1/clientes/{id}/` - Obtener cliente
- `PUT /api/v1/clientes/{id}/` - Actualizar cliente
- `DELETE /api/v1/clientes/{id}/` - Eliminar cliente

### Servicios

- `GET /api/v1/servicios/` - Listar servicios
- `POST /api/v1/servicios/` - Crear servicio
- `GET /api/v1/servicios/{id}/` - Obtener servicio
- `PUT /api/v1/servicios/{id}/` - Actualizar servicio
- `DELETE /api/v1/servicios/{id}/` - Eliminar servicio

### Citas

- `GET /api/v1/citas/` - Listar citas
- `POST /api/v1/citas/` - Crear cita
- `GET /api/v1/citas/{id}/` - Obtener cita
- `PUT /api/v1/citas/{id}/` - Actualizar cita
- `DELETE /api/v1/citas/{id}/` - Eliminar cita

### Pagos

- `GET /api/v1/pagos/` - Listar pagos
- `POST /api/v1/pagos/` - Crear pago
- `GET /api/v1/pagos/{id}/` - Obtener pago
- `PUT /api/v1/pagos/{id}/` - Actualizar pago

## Administración

Acceder al panel de administración en: `http://localhost:8000/admin/`

## Desarrollo

Para ejecutar en modo desarrollo:

```bash
python manage.py runserver
```

La API estará disponible en: `http://localhost:8000/api/v1/`

## Contribución

1. Fork el proyecto
2. Crear una rama para tu funcionalidad
3. Commit tus cambios
4. Push a la rama
5. Crear un Pull Request
