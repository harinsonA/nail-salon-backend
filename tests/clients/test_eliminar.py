"""
Tests para eliminar clientes - API endpoint DELETE /api/clientes/{id}/
"""

from rest_framework import status
from ..utils import BaseAPITestCase
from apps.clients.models import Cliente


class TestEliminarClientes(BaseAPITestCase):
    """Tests para el endpoint de eliminación de clientes."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.cliente = self.create_cliente_with_factory(
            nombre="Elena",
            apellido="Rodríguez",
            telefono="3001111111",
            email="elena.rodriguez@test.com",
        )
        self.url_name = "cliente-detail"

    def test_eliminar_cliente_exitoso(self):
        """Test que verifica eliminación exitosa de cliente."""
        cliente_id = self.cliente.cliente_id

        response = self.api_delete(self.url_name, pk=cliente_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar que el cliente ya no existe en la base de datos
        self.assertFalse(Cliente.objects.filter(id=cliente_id).exists())

    def test_eliminar_cliente_inexistente(self):
        """Test que verifica respuesta para cliente que no existe."""
        response = self.api_delete(self.url_name, pk=99999)

        self.assert_not_found(response)

    def test_eliminar_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.unauthenticate()

        response = self.api_delete(self.url_name, pk=self.cliente.cliente_id)

        self.assert_unauthorized(response)

    def test_eliminar_usuario_normal(self):
        """Test que verifica que usuarios normales pueden eliminar."""
        self.authenticate_as_normal_user()

        response = self.api_delete(self.url_name, pk=self.cliente.cliente_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

    def test_eliminar_cliente_con_citas(self):
        """Test que verifica comportamiento al eliminar cliente con citas."""
        # Crear cita asociada al cliente
        cita = self.create_cita_with_factory(cliente=self.cliente)

        response = self.api_delete(self.url_name, pk=self.cliente.cliente_id)

        # Dependiendo de la configuración, podría fallar o eliminar en cascada
        # Asumiendo que se permite eliminación en cascada
        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar que el cliente ya no existe
        self.assertFalse(Cliente.objects.filter(id=self.cliente.cliente_id).exists())

    def test_eliminar_cliente_ya_eliminado(self):
        """Test que verifica doble eliminación."""
        cliente_id = self.cliente.cliente_id

        # Primera eliminación
        response = self.api_delete(self.url_name, pk=cliente_id)
        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Segunda eliminación del mismo cliente
        response = self.api_delete(self.url_name, pk=cliente_id)
        self.assert_not_found(response)

    def test_verificar_eliminacion_completa(self):
        """Test que verifica que la eliminación es completa."""
        cliente_id = self.cliente.cliente_id
        email_original = self.cliente.email

        # Eliminar cliente
        response = self.api_delete(self.url_name, pk=cliente_id)
        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar que no existe en la base de datos
        self.assertFalse(Cliente.objects.filter(id=cliente_id).exists())
        self.assertFalse(Cliente.objects.filter(email=email_original).exists())

        # Verificar que se puede crear otro cliente con el mismo email
        nuevo_cliente = self.create_cliente_with_factory(email=email_original)
        self.assertTrue(Cliente.objects.filter(id=nuevo_cliente.cliente_id).exists())
