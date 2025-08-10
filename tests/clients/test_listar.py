"""
Tests para listar clientes - API endpoint GET /api/clientes/
"""

from django.urls import reverse
from rest_framework import status
from ..utils import BaseAPITestCase
from apps.clients.models import Cliente


class TestListarClientes(BaseAPITestCase):
    """Tests para el endpoint de listado de clientes."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.url_name = "cliente-list"

        # Crear algunos clientes de prueba
        self.cliente1 = self.create_cliente(
            nombre="Ana",
            apellido="García",
            telefono="3001111111",
            email="ana.garcia@test.com",
        )
        self.cliente2 = self.create_cliente(
            nombre="María",
            apellido="López",
            telefono="3002222222",
            email="maria.lopez@test.com",
            activo=False,
        )
        self.cliente3 = self.create_cliente(
            nombre="Carmen",
            apellido="Rodríguez",
            telefono="3003333333",
            email="carmen.rodriguez@test.com",
        )

    def test_listar_clientes_exitoso(self):
        """Test que verifica que se pueden listar los clientes correctamente."""
        response = self.api_get(self.url_name)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assert_pagination_response(response.data)

        # Verificar que se retornan los clientes creados
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 3)

        # Verificar estructura de cada cliente
        expected_fields = [
            "id",
            "nombre",
            "apellido",
            "telefono",
            "email",
            "activo",
            "fecha_registro",
            "notas",
        ]
        for cliente_data in response.data["results"]:
            self.assert_response_contains_fields(cliente_data, expected_fields)

    def test_listar_clientes_con_filtros(self):
        """Test para verificar filtros de búsqueda."""
        # Filtro por nombre
        response = self.api_get(self.url_name, {"search": "Ana"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["nombre"], "Ana")

        # Filtro por activo
        response = self.api_get(self.url_name, {"activo": "true"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)  # Ana y Carmen están activos

        # Filtro por inactivo
        response = self.api_get(self.url_name, {"activo": "false"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)  # Solo María está inactiva

    def test_listar_clientes_ordenamiento(self):
        """Test para verificar ordenamiento de resultados."""
        response = self.api_get(self.url_name, {"ordering": "nombre"})
        self.assert_response_status(response, status.HTTP_200_OK)

        nombres = [cliente["nombre"] for cliente in response.data["results"]]
        self.assertEqual(nombres, ["Ana", "Carmen", "María"])

        # Ordenamiento descendente
        response = self.api_get(self.url_name, {"ordering": "-nombre"})
        self.assert_response_status(response, status.HTTP_200_OK)

        nombres = [cliente["nombre"] for cliente in response.data["results"]]
        self.assertEqual(nombres, ["María", "Carmen", "Ana"])

    def test_listar_clientes_paginacion(self):
        """Test para verificar la paginación."""
        # Crear más clientes para probar paginación
        for i in range(15):
            self.create_cliente(
                nombre=f"Cliente{i}",
                apellido=f"Test{i}",
                telefono=f"300444{i:04d}",
                email=f"cliente{i}@test.com",
            )

        # Test primera página
        response = self.api_get(self.url_name, {"page": 1, "page_size": 10})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertIsNotNone(response.data["links"]["next"])
        self.assertIsNone(response.data["links"]["previous"])

        # Test segunda página
        response = self.api_get(self.url_name, {"page": 2, "page_size": 10})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data["results"]), 8
        )  # 18 total - 10 primera página
        self.assertIsNone(response.data["links"]["next"])
        self.assertIsNotNone(response.data["links"]["previous"])

    def test_listar_clientes_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.unauthenticate()
        response = self.api_get(self.url_name)
        self.assert_unauthorized(response)

    def test_listar_clientes_usuario_normal(self):
        """Test que verifica que usuarios normales pueden listar clientes."""
        self.authenticate_as_normal_user()
        response = self.api_get(self.url_name)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assert_pagination_response(response.data)

    def test_listar_clientes_sin_resultados(self):
        """Test para verificar respuesta cuando no hay clientes."""
        # Eliminar todos los clientes
        Cliente.objects.all().delete()

        response = self.api_get(self.url_name)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assert_pagination_response(response.data)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(len(response.data["results"]), 0)

    def test_listar_clientes_busqueda_por_telefono(self):
        """Test para verificar búsqueda por número de teléfono."""
        response = self.api_get(self.url_name, {"search": "3001111111"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["telefono"], "3001111111")

    def test_listar_clientes_busqueda_por_email(self):
        """Test para verificar búsqueda por email."""
        response = self.api_get(self.url_name, {"search": "ana.garcia@test.com"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["email"], "ana.garcia@test.com")

    def test_listar_clientes_formato_fecha(self):
        """Test para verificar formato de fechas en la respuesta."""
        response = self.api_get(self.url_name)
        self.assert_response_status(response, status.HTTP_200_OK)

        if response.data["results"]:
            cliente = response.data["results"][0]
            # Verificar que fecha_registro tiene el formato correcto
            self.assertIsNotNone(cliente["fecha_registro"])
            self.assertIsInstance(cliente["fecha_registro"], str)
            # La fecha debe terminar con 'Z' (UTC) o tener offset timezone
            self.assertTrue(
                cliente["fecha_registro"].endswith("Z")
                or "+" in cliente["fecha_registro"]
                or "-" in cliente["fecha_registro"][-6:]
            )
