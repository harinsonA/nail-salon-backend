# Documentación de la App Clients

Esta carpeta contiene la documentación completa de la aplicación `clients` del sistema de gestión de salón de uñas.

## Estructura de la Documentación

1. **[Modelo Cliente](./modelo_cliente.md)** - Documentación detallada del modelo de datos
2. **[Vistas y ViewSets](./vistas_cliente.md)** - Documentación de las vistas y endpoints de la API
3. **[URLs y Rutas](./urls_cliente.md)** - Documentación del sistema de rutas
4. **[Serializers](./serializers_cliente.md)** - Documentación de los serializadores
5. **[Administración Django](./admin_cliente.md)** - Configuración del panel de administración
6. **[Pruebas (Tests)](./tests_cliente.md)** - Documentación de las pruebas unitarias
7. **[Comandos de Gestión](./commands_cliente.md)** - Comandos personalizados de Django

## Visión General

La aplicación `clients` es responsable de gestionar toda la información relacionada con los clientes del salón de uñas. Proporciona una API RESTful completa para realizar operaciones CRUD (Crear, Leer, Actualizar, Eliminar) sobre los datos de los clientes.

### Características Principales

- **Gestión Completa de Clientes**: CRUD completo con validaciones
- **API RESTful**: Endpoints siguiendo estándares REST
- **Autenticación Requerida**: Todos los endpoints requieren autenticación
- **Filtros y Búsqueda**: Capacidades avanzadas de filtrado y búsqueda
- **Paginación**: Resultados paginados para mejor performance
- **Validaciones**: Validaciones robustas de datos
- **Panel de Administración**: Interfaz administrativa completa

### Tecnologías Utilizadas

- **Django**: Framework web principal
- **Django REST Framework**: Para la API REST
- **Django Filters**: Para filtros avanzados
- **Factory Boy**: Para generar datos de prueba
- **Pytest**: Para pruebas unitarias

## Estructura de Archivos

```
apps/clients/
├── models/
│   ├── __init__.py
│   └── cliente.py          # Modelo principal de Cliente
├── views/
│   ├── __init__.py
│   └── cliente_views.py    # ViewSet con todos los endpoints
├── serializers/
│   ├── __init__.py
│   └── cliente_serializer.py  # Serializadores para API
├── management/
│   └── commands/           # Comandos personalizados
├── migrations/             # Migraciones de base de datos
├── admin.py               # Configuración panel admin
├── apps.py                # Configuración de la app
├── models.py              # Importaciones de modelos
├── urls.py                # Configuración de URLs
└── views.py               # Archivo legacy (vacío)

tests/clients/
├── test_crear.py          # Tests para creación
├── test_listar.py         # Tests para listado
├── test_detalle.py        # Tests para detalle
├── test_actualizar.py     # Tests para actualización
└── test_eliminar.py       # Tests para eliminación
```

## Endpoints Principales

| Método | URL                              | Descripción                 |
| ------ | -------------------------------- | --------------------------- |
| GET    | `/api/clientes/`                 | Listar todos los clientes   |
| POST   | `/api/clientes/`                 | Crear nuevo cliente         |
| GET    | `/api/clientes/{id}/`            | Obtener detalle de cliente  |
| PUT    | `/api/clientes/{id}/`            | Actualizar cliente completo |
| PATCH  | `/api/clientes/{id}/`            | Actualizar cliente parcial  |
| DELETE | `/api/clientes/{id}/`            | Eliminar cliente            |
| POST   | `/api/clientes/{id}/activar/`    | Activar cliente             |
| POST   | `/api/clientes/{id}/desactivar/` | Desactivar cliente          |
| GET    | `/api/clientes/{id}/citas/`      | Obtener citas del cliente   |

## Próximos Pasos

Para una comprensión completa de la aplicación, recomendamos leer los documentos en el siguiente orden:

1. Modelo Cliente (base de datos)
2. Serializers (transformación de datos)
3. Vistas (lógica de negocio)
4. URLs (enrutamiento)
5. Tests (validación de funcionalidad)
