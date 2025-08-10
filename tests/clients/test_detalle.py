"""
Tests para obtener detalle de cliente - API endpoint GET /api/clientes/{id}/
"""

from rest_framework import status
from ..utils import BaseAPITestCase
from apps.clients.models import Cliente


class TestDetalleCliente(BaseAPITestCase):
    """Tests para el endpoint de detalle de cliente."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.cliente = self.create_cliente_with_factory(
            nombre="Ana",
            apellido="García",
            telefono="3001111111",
            email="ana.garcia@test.com",
        )
        self.url_name = "cliente-detail"

    def test_obtener_detalle_cliente_exitoso(self):
        """Test que verifica que se puede obtener el detalle de un cliente."""
        response = self.api_get(self.url_name, pk=self.cliente.cliente_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar estructura de la respuesta
        expected_fields = [
            "cliente_id",
            "nombre",
            "apellido",
            "telefono",
            "email",
            "activo",
            "fecha_registro",
            "notas",
        ]
        self.assert_response_contains_fields(response.data, expected_fields)

        # Verificar valores
        self.assertEqual(response.data["cliente_id"], self.cliente.cliente_id)
        self.assertEqual(response.data["nombre"], "Ana")
        self.assertEqual(response.data["apellido"], "García")
        self.assertEqual(response.data["email"], "ana.garcia@test.com")

    def test_obtener_detalle_cliente_inexistente(self):
        """Test que verifica respuesta para cliente que no existe."""
        response = self.api_get(self.url_name, pk=99999)

        self.assert_not_found(response)

    def test_obtener_detalle_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.unauthenticate()
        response = self.api_get(self.url_name, pk=self.cliente.cliente_id)

        self.assert_unauthorized(response)

    def test_obtener_detalle_usuario_normal(self):
        """Test que verifica que usuarios normales pueden ver detalles."""
        self.authenticate_as_normal_user()
        response = self.api_get(self.url_name, pk=self.cliente.cliente_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["cliente_id"], self.cliente.cliente_id)

    def test_obtener_detalle_cliente_inactivo(self):
        """Test que verifica que se puede obtener detalle de cliente inactivo."""
        cliente_inactivo = self.create_cliente_with_factory(
            nombre="Inactivo",
            apellido="Test",
            email="inactivo@test.com",
            telefono="3002222222",
            activo=False,
        )

        response = self.api_get(self.url_name, pk=cliente_inactivo.cliente_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["activo"], False)

    def test_formato_fecha_en_detalle(self):
        """Test que verifica el formato de fecha en el detalle."""
        response = self.api_get(self.url_name, pk=self.cliente.cliente_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que fecha_registro tiene el formato correcto
        self.assertIsNotNone(response.data["fecha_registro"])
        self.assertIsInstance(response.data["fecha_registro"], str)
        # La fecha debe terminar con 'Z' (UTC) o tener offset timezone
        self.assertTrue(
            response.data["fecha_registro"].endswith("Z")
            or "+" in response.data["fecha_registro"]
            or "-" in response.data["fecha_registro"][-6:]
        )
