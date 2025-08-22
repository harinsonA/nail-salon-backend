# Documentación de la App Services

Esta carpeta contiene la documentación completa de la aplicación `services` del sistema de gestión de salón de uñas.

## Estructura de la Documentación

1. **[Modelo Servicio](./modelo_servicio.md)** - Documentación detallada del modelo de datos
2. **[Vistas y ViewSets](./vistas_servicio.md)** - Documentación de las vistas y endpoints de la API
3. **[URLs y Rutas](./urls_servicio.md)** - Documentación del sistema de rutas
4. **[Serializers](./serializers_servicio.md)** - Documentación de los serializadores
5. **[Administración Django](./admin_servicio.md)** - Configuración del panel de administración
6. **[Pruebas (Tests)](./tests_servicio.md)** - Documentación de las pruebas unitarias
7. **[Comandos de Gestión](./commands_servicio.md)** - Comandos personalizados de Django

## Visión General

La aplicación `services` es responsable de gestionar toda la información relacionada con los servicios ofrecidos por el salón de uñas. Proporciona una API RESTful completa para realizar operaciones CRUD (Crear, Leer, Actualizar, Eliminar) sobre los datos de los servicios.

### Características Principales

- **Gestión Completa de Servicios**: CRUD completo con validaciones
- **API RESTful**: Endpoints siguiendo estándares REST
- **Autenticación Requerida**: Todos los endpoints requieren autenticación
- **Filtros y Búsqueda**: Capacidades avanzadas de filtrado y búsqueda
- **Paginación**: Resultados paginados para mejor performance
- **Validaciones**: Validaciones robustas de datos
- **Panel de Administración**: Interfaz administrativa completa
- **Campos Opcionales**: Descripción y duración estimada opcionales
- **Formateo de Datos**: Precio formateado y duración en formato legible

### Tecnologías Utilizadas

- **Django**: Framework web principal
- **Django REST Framework**: Para la API REST
- **Django Filters**: Para filtros avanzados
- **Factory Boy**: Para generar datos de prueba
- **Pytest**: Para pruebas unitarias

## Estructura de Archivos

```
apps/services/
├── models/
│   ├── __init__.py
│   └── servicio.py         # Modelo principal de Servicio
├── views/
│   ├── __init__.py
│   └── servicio_views.py   # ViewSet con todos los endpoints
├── serializers/
│   ├── __init__.py
│   └── servicio_serializer.py  # Serializadores para API
├── management/
│   └── commands/           # Comandos personalizados
├── migrations/             # Migraciones de base de datos
├── admin.py               # Configuración panel admin
├── apps.py                # Configuración de la app
├── models.py              # Importaciones de modelos
├── urls.py                # Configuración de URLs
└── views.py               # Archivo legacy (vacío)

tests/services/
├── test_crear.py          # Tests para creación
├── test_listar.py         # Tests para listado
├── test_detalle.py        # Tests para detalle
├── test_actualizar.py     # Tests para actualización
└── test_eliminar.py       # Tests para eliminación
```

## Endpoints Principales

| Método | URL                    | Descripción                  |
| ------ | ---------------------- | ---------------------------- |
| GET    | `/api/servicios/`      | Listar todos los servicios   |
| POST   | `/api/servicios/`      | Crear nuevo servicio         |
| GET    | `/api/servicios/{id}/` | Obtener detalle de servicio  |
| PUT    | `/api/servicios/{id}/` | Actualizar servicio completo |
| PATCH  | `/api/servicios/{id}/` | Actualizar servicio parcial  |
| DELETE | `/api/servicios/{id}/` | Eliminar servicio            |

## Campos del Modelo

### Campos Principales

- **servicio_id**: Identificador único (PK)
- **nombre_servicio**: Nombre del servicio (requerido)
- **precio**: Precio del servicio (requerido, validado > 0)
- **descripcion**: Descripción del servicio (opcional)
- **duracion_estimada**: Tiempo estimado del servicio (opcional)
- **activo**: Estado del servicio (por defecto True)
- **categoria**: Categoría del servicio (opcional)

### Campos de Gestión

- **fecha_creacion**: Timestamp de creación (automático)
- **fecha_actualizacion**: Timestamp de última actualización (automático)

## Validaciones Implementadas

### Validaciones de Precio

- **Precio positivo**: El precio debe ser mayor a 0
- **Formato decimal**: Acepta hasta 2 decimales
- **Máximo 10 dígitos**: Con 2 decimales

### Validaciones de Duración

- **Duración positiva**: Si se especifica, debe ser mayor a 0
- **Formato tiempo**: Acepta formato HH:MM:SS

### Validaciones de Texto

- **Nombre requerido**: El nombre del servicio es obligatorio
- **Longitud máxima**: Nombre máximo 200 caracteres
- **Categoría opcional**: Puede estar vacía o ser null

## Características Especiales

### Serializers Duales

- **ServicioSerializer**: Para operaciones detalladas (crear, actualizar, detalle)
- **ServicioListSerializer**: Para listados optimizados (menos campos)

### Campos Computados

- **precio_formateado**: Precio con formato de moneda ($25,000)
- **duracion_estimada_horas**: Duración en formato legible (90m, 2h 30m)

### Filtros Disponibles

- Filtro por estado activo
- Búsqueda por nombre, descripción y categoría
- Ordenamiento por nombre, precio, fecha de creación

## Próximos Pasos

Para una comprensión completa de la aplicación, recomendamos leer los documentos en el siguiente orden:

1. Modelo Servicio (base de datos)
2. Serializers (transformación de datos)
3. Vistas (lógica de negocio)
4. URLs (enrutamiento)
5. Tests (validación de funcionalidad)

## Estado Actual

✅ **Implementación Completa**

- Modelo con validaciones
- ViewSets con CRUD completo
- Serializers con campos computados
- URLs configuradas
- Admin panel configurado
- Suite de tests completa (43 tests)
- Migraciones aplicadas
- Documentación completa
