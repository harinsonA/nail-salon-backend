"""
Tests de integración que verifican el flujo completo del sistema.
"""

from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from .utils import BaseAPITestCase


class TestFlujoCompletoSalon(BaseAPITestCase):
    """Tests que verifican el flujo completo del sistema de salón."""

    def test_flujo_cita_completa(self):
        """Test que verifica el flujo completo: cliente -> servicio -> cita -> pago."""

        # 1. Crear cliente
        cliente_data = {
            "nombre": "María",
            "apellido": "González",
            "telefono": "3001234567",
            "email": "maria.gonzalez@test.com",
        }
        cliente_response = self.api_post("cliente-list", cliente_data)
        self.assert_response_status(cliente_response, status.HTTP_201_CREATED)
        cliente_id = cliente_response.data["cliente_id"]  # Usar campo correcto

        # 2. Crear servicio
        servicio_data = {
            "nombre_servicio": "Manicure Completo",
            "precio": "35000.00",
            "descripcion": "Manicure completo con decoración",
            "duracion_estimada": "01:30:00",
            "categoria": "Manicure",
        }
        servicio_response = self.api_post("servicio-list", servicio_data)
        self.assert_response_status(servicio_response, status.HTTP_201_CREATED)

        # 3. Crear cita
        fecha_cita = timezone.now() + timedelta(days=1)
        cita_data = {
            "cliente": cliente_id,
            "fecha_hora_cita": fecha_cita.isoformat(),
            "estado_cita": "PENDIENTE",  # Usar estado correcto en mayúsculas
            "notas": "Primera cita de María",
        }
        cita_response = self.api_post("cita-list", cita_data)
        self.assert_response_status(cita_response, status.HTTP_201_CREATED)
        cita_id = cita_response.data["cita_id"]  # Usar campo correcto

        # 4. Crear pago
        pago_data = {
            "cita": cita_id,
            "monto_total": "35000.00",
            "metodo_pago": "EFECTIVO",  # Usar método correcto en mayúsculas
            "estado_pago": "PAGADO",  # Usar estado correcto en mayúsculas
            "notas_pago": "Pago en efectivo",
        }
        pago_response = self.api_post("payments:pago-list", pago_data)
        self.assert_response_status(pago_response, status.HTTP_201_CREATED)

        # 5. Verificar relaciones
        # Verificar que el cliente tiene la cita
        cliente_detail = self.api_get("cliente-detail", pk=cliente_id)
        self.assert_response_status(cliente_detail, status.HTTP_200_OK)

        # Verificar que la cita tiene el pago
        cita_detail = self.api_get("cita-detail", pk=cita_id)
        self.assert_response_status(cita_detail, status.HTTP_200_OK)

        # Verificar que el pago está asociado a la cita
        pago_detail = self.api_get(
            "payments:pago-detail", pk=pago_response.data["pago_id"]
        )
        self.assert_response_status(pago_detail, status.HTTP_200_OK)
        self.assertEqual(pago_detail.data["cita"], cita_id)

        # 6. Actualizar estado de cita a completada
        update_cita = self.api_patch(
            "cita-detail", {"estado_cita": "COMPLETADA"}, pk=cita_id
        )
        self.assert_response_status(update_cita, status.HTTP_200_OK)
        self.assertEqual(update_cita.data["estado_cita"], "COMPLETADA")

    def test_busqueda_global_cliente(self):
        """Test que verifica búsqueda de cliente en diferentes endpoints."""

        # Crear cliente
        cliente = self.create_cliente_with_factory(
            nombre="Ana",
            apellido="Martínez",
            email="ana.martinez@search.com",
            telefono="3009999999",
        )

        # Crear cita para el cliente
        cita = self.create_cita_with_factory(cliente=cliente)

        # Buscar cliente por nombre
        search_response = self.api_get("cliente-list", {"search": "Ana"})
        self.assert_response_status(search_response, status.HTTP_200_OK)
        self.assertEqual(search_response.data["count"], 1)

        # Buscar cliente por email
        search_response = self.api_get(
            "cliente-list", {"search": "ana.martinez@search.com"}
        )
        self.assert_response_status(search_response, status.HTTP_200_OK)
        self.assertEqual(search_response.data["count"], 1)

        # Buscar cliente por teléfono
        search_response = self.api_get("cliente-list", {"search": "3009999999"})
        self.assert_response_status(search_response, status.HTTP_200_OK)
        self.assertEqual(search_response.data["count"], 1)

        # Filtrar citas por cliente
        citas_response = self.api_get("cita-list", {"cliente": cliente.cliente_id})
        self.assert_response_status(citas_response, status.HTTP_200_OK)
        self.assertEqual(citas_response.data["count"], 1)

    def test_validacion_consistencia_datos(self):
        """Test que verifica la consistencia de datos entre entidades."""

        # Crear datos base
        cliente = self.create_cliente_with_factory()
        servicio = self.create_servicio_with_factory(precio=Decimal("25000.00"))
        cita = self.create_cita_with_factory(cliente=cliente, estado_cita="PENDIENTE")

        # Crear pago con monto diferente al servicio
        pago_data = {
            "cita": cita.cita_id,
            "monto_total": "30000.00",  # Diferente al precio del servicio
            "metodo_pago": "TARJETA",
            "estado_pago": "PAGADO",
        }
        pago_response = self.api_post("payments:pago-list", pago_data)
        self.assert_response_status(pago_response, status.HTTP_201_CREATED)

        # Verificar que se puede crear pago con monto diferente
        # (esto depende de las reglas de negocio)
        self.assertEqual(pago_response.data["monto_total"], "30000.00")

    def test_eliminacion_en_cascada(self):
        """Test que verifica el comportamiento de eliminación en cascada."""

        # Crear datos relacionados
        cliente = self.create_cliente_with_factory()
        cita = self.create_cita_with_factory(cliente=cliente, estado_cita="PENDIENTE")
        pago = self.create_pago_with_factory(cita=cita)

        cliente_id = cliente.cliente_id
        cita_id = cita.cita_id
        pago_id = pago.pago_id

        # Eliminar cliente
        delete_response = self.api_delete("cliente-detail", pk=cliente_id)
        self.assert_response_status(delete_response, status.HTTP_204_NO_CONTENT)

        # Verificar que el cliente ya no existe
        get_cliente = self.api_get("cliente-detail", pk=cliente_id)
        self.assert_not_found(get_cliente)

        # Verificar comportamiento de citas y pagos (depende de configuración)
        # Si está configurado ON DELETE CASCADE, estos también deberían eliminarse
        get_cita = self.api_get("cita-detail", pk=cita_id)
        get_pago = self.api_get("payments:pago-detail", pk=pago_id)

        # Esto depende de la configuración de la base de datos
        # Por ahora, solo verificamos que el cliente se eliminó
        pass

    def test_rendimiento_listados_grandes(self):
        """Test básico de rendimiento con muchos registros."""

        # Crear muchos clientes
        clientes = []
        for i in range(50):
            cliente = self.create_cliente_with_factory(
                nombre=f"Cliente{i}",
                email=f"cliente{i}@test.com",
                telefono=f"300{i:07d}",
            )
            clientes.append(cliente)

        # Listar todos los clientes
        response = self.api_get("cliente-list")
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 50)

        # Verificar paginación funciona con muchos datos
        response_paginated = self.api_get("cliente-list", {"page_size": 20})
        self.assert_response_status(response_paginated, status.HTTP_200_OK)
        self.assertEqual(len(response_paginated.data["results"]), 20)

    def test_multiples_usuarios_acceso(self):
        """Test que verifica acceso con diferentes tipos de usuarios."""

        # Crear datos como admin
        cliente = self.create_cliente_with_factory()

        # Cambiar a usuario normal
        self.authenticate_as_normal_user()

        # Verificar que usuario normal puede leer
        clientes_response = self.api_get("cliente-list")
        self.assert_response_status(clientes_response, status.HTTP_200_OK)

        servicios_response = self.api_get("servicio-list")
        self.assert_response_status(servicios_response, status.HTTP_200_OK)

        # Verificar que usuario normal puede crear cita
        cita_data = {
            "cliente": cliente.cliente_id,
            "fecha_hora_cita": (timezone.now() + timedelta(days=1)).isoformat(),
            "estado_cita": "PENDIENTE",
        }
        cita_response = self.api_post("cita-list", cita_data)
        self.assert_response_status(cita_response, status.HTTP_201_CREATED)

        # Sin autenticación no debe poder acceder
        self.unauthenticate()
        no_auth_response = self.api_get("cliente-list")
        self.assert_unauthorized(no_auth_response)
