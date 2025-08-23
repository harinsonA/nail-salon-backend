# Documentación de la App Payments

Esta carpeta contiene la documentación completa de la aplicación `payments` del sistema de gestión de salón de uñas.

## Estructura de la Documentación

1. **[Modelo de Payments](./modelo_payments.md)** - Documentación detallada del modelo de datos
2. **[Vistas y ViewSets](./vistas_payments.md)** - Documentación de las vistas y endpoints de la API
3. **[URLs y Rutas](./urls_payments.md)** - Documentación del sistema de rutas
4. **[Serializers](./serializers_payments.md)** - Documentación de los serializadores
5. **[Administración Django](./admin_payments.md)** - Configuración del panel de administración
6. **[Pruebas (Tests)](./tests_payments.md)** - Documentación de las pruebas unitarias

## Visión General

La aplicación `payments` es responsable de gestionar todo el sistema de pagos del salón de uñas. Proporciona una API RESTful completa para administrar pagos asociados a citas, métodos de pago, estados de pago y toda la lógica de negocio financiera.

### Características Principales

- **Gestión Completa de Pagos**: CRUD completo con validaciones de estado y monto
- **Asociación con Citas**: Cada pago está vinculado a una cita específica
- **Múltiples Métodos de Pago**: Efectivo, tarjeta, transferencia, cheque
- **Estados de Pago**: Control de flujo (PENDIENTE → PAGADO/CANCELADO)
- **API RESTful**: Endpoints siguiendo estándares REST
- **Autenticación Requerida**: Todos los endpoints requieren autenticación
- **Filtros Avanzados**: Por estado, método, cita, rango de fechas, monto
- **Búsqueda**: Por notas de pago y referencias
- **Validaciones de Negocio**: Montos positivos, citas válidas, integridad referencial
- **Campos Computados**: Monto formateado, validación de pago completo
- **Auditoría**: Registro de usuario creador y fechas de gestión

### Tecnologías Utilizadas

- **Django**: Framework web principal
- **Django REST Framework**: Para la API REST
- **Django Filters**: Para filtros avanzados
- **Factory Boy**: Para generar datos de prueba
- **Pytest**: Para pruebas unitarias

## Estructura de Archivos

```
apps/payments/
├── models/
│   ├── __init__.py
│   └── pago.py                 # Modelo principal de Pago
├── views/
│   ├── __init__.py
│   └── pago_views.py           # ViewSet principal de pagos
├── serializers/
│   ├── __init__.py
│   └── pago_serializer.py      # Serializadores para API
├── migrations/
│   ├── __init__.py
│   ├── 0001_initial.py
│   └── 0002_pago_fecha_actualizacion.py
├── admin.py                    # Configuración del admin
├── apps.py                     # Configuración de la app
├── urls.py                     # URLs de la aplicación
├── views.py                    # Vista base (alias)
└── tests.py                    # Tests base (alias)
```

## Estados de Pago

La aplicación maneja un flujo de estados específico:

1. **PENDIENTE**: Estado inicial al crear el pago
2. **PAGADO**: Pago completado y confirmado
3. **CANCELADO**: Pago cancelado o reembolsado

### Reglas de Negocio

- Solo se pueden **modificar** pagos en estado PENDIENTE
- Los pagos **PAGADOS** solo permiten modificar las notas
- Los pagos **CANCELADOS** no se pueden modificar
- **No se pueden crear** pagos para citas CANCELADAS
- El **monto debe ser positivo** y mayor a cero
- Se puede **asociar múltiples pagos** a una misma cita (pagos parciales)
- Los **métodos de pago** están limitados a las opciones predefinidas

## Métodos de Pago Soportados

| Método        | Código          | Descripción                       |
| ------------- | --------------- | --------------------------------- |
| Efectivo      | `EFECTIVO`      | Pago en efectivo                  |
| Tarjeta       | `TARJETA`       | Pago con tarjeta (débito/crédito) |
| Transferencia | `TRANSFERENCIA` | Transferencia bancaria            |
| Cheque        | `CHEQUE`        | Pago con cheque                   |

## Campos Computados

- **monto_formateado**: Formato de moneda con separadores de miles
- **es_pago_completo**: Indica si el pago cubre el monto total de la cita
- **cita_info**: Información expandida de la cita asociada

## Validaciones Implementadas

### A Nivel de Modelo

- Monto total debe ser mayor a cero
- Referencia de pago opcional pero limitada a 100 caracteres
- Relación válida con cita existente

### A Nivel de Serializer

- Validación de cita no cancelada
- Validación de campos requeridos
- Formato correcto de fechas y montos

### A Nivel de Vista

- Autenticación requerida para todas las operaciones
- Validación de permisos de modificación según estado
- Filtros de integridad referencial

## Funcionalidades Especiales

### Pago Automático de Cita

Cuando un pago se marca como completado y cubre el monto total de la cita, automáticamente actualiza el estado de la cita a "COMPLETADA".

### Múltiples Pagos por Cita

El sistema permite pagos parciales, donde una cita puede tener múltiples pagos hasta completar el monto total.

### Auditoría Completa

Todos los pagos registran:

- Usuario que creó el pago
- Fecha de creación
- Fecha de última actualización
- Historial de cambios de estado

## Enlaces Rápidos

- **[🔧 Configuración del Modelo](./modelo_payments.md)**
- **[🌐 Endpoints de la API](./vistas_payments.md)**
- **[🔗 Sistema de URLs](./urls_payments.md)**
- **[📝 Serializadores](./serializers_payments.md)**
- **[⚙️ Panel de Admin](./admin_payments.md)**
- **[🧪 Suite de Tests](./tests_payments.md)**

---

**Última actualización**: Agosto 2025  
**Versión**: 1.0  
**Estado**: ✅ Completamente funcional y probado
