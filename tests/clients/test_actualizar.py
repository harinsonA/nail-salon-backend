"""
Tests para actualizar clientes - API endpoint PUT/PATCH /api/clientes/{id}/
"""

from rest_framework import status
from ..utils import BaseAPITestCase
from apps.clients.models import Cliente


class TestActualizarClientes(BaseAPITestCase):
    """Tests para el endpoint de actualización de clientes."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.cliente = self.create_cliente_with_factory(
            nombre="Carlos",
            apellido="Martínez",
            telefono="3001234567",
            email="carlos.martinez@test.com",
        )
        self.url_name = "cliente-detail"

    def test_actualizar_cliente_completo_put(self):
        """Test que verifica actualización completa con PUT."""
        data = {
            "nombre": "Carlos Alberto",
            "apellido": "Martínez García",
            "telefono": "3009876543",
            "email": "carlos.alberto@test.com",
            "activo": True,
            "notas": "Cliente actualizado",
        }

        response = self.api_put(self.url_name, data, pk=self.cliente.cliente_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que se actualizó en la base de datos
        cliente_actualizado = Cliente.objects.get(cliente_id=self.cliente.cliente_id)
        self.assertEqual(cliente_actualizado.nombre, "Carlos Alberto")
        self.assertEqual(cliente_actualizado.apellido, "Martínez García")
        self.assertEqual(cliente_actualizado.email, "carlos.alberto@test.com")

        # Verificar respuesta
        self.assertEqual(response.data["nombre"], "Carlos Alberto")
        self.assertEqual(response.data["email"], "carlos.alberto@test.com")

    def test_actualizar_cliente_parcial_patch(self):
        """Test que verifica actualización parcial con PATCH."""
        data = {"nombre": "Carlos Eduardo", "notas": "Solo nombre y notas actualizadas"}

        response = self.api_patch(self.url_name, data, pk=self.cliente.cliente_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que solo se actualizaron los campos enviados
        cliente_actualizado = Cliente.objects.get(cliente_id=self.cliente.cliente_id)
        self.assertEqual(cliente_actualizado.nombre, "Carlos Eduardo")
        self.assertEqual(cliente_actualizado.apellido, "Martínez")  # No cambió
        self.assertEqual(
            cliente_actualizado.email, "carlos.martinez@test.com"
        )  # No cambió

    def test_actualizar_cliente_inexistente(self):
        """Test que verifica respuesta para cliente que no existe."""
        data = {"nombre": "No Existe", "apellido": "Test"}

        response = self.api_patch(self.url_name, data, pk=99999)

        self.assert_not_found(response)

    def test_actualizar_email_duplicado(self):
        """Test que verifica que no se puede actualizar con email duplicado."""
        # Crear otro cliente
        otro_cliente = self.create_cliente_with_factory(email="otro@test.com")

        data = {
            "email": "otro@test.com"  # Email que ya existe
        }

        response = self.api_patch(self.url_name, data, pk=self.cliente.cliente_id)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_actualizar_telefono_duplicado(self):
        """Test que verifica que no se puede actualizar con teléfono duplicado."""
        # Crear otro cliente
        otro_cliente = self.create_cliente_with_factory(telefono="3005555555")

        data = {
            "telefono": "3005555555"  # Teléfono que ya existe
        }

        response = self.api_patch(self.url_name, data, pk=self.cliente.cliente_id)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("telefono", response.data)

    def test_actualizar_email_invalido(self):
        """Test que verifica validación de formato de email."""
        data = {"email": "email-invalido"}

        response = self.api_patch(self.url_name, data, pk=self.cliente.cliente_id)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_actualizar_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.unauthenticate()

        data = {"nombre": "Sin Auth"}

        response = self.api_patch(self.url_name, data, pk=self.cliente.cliente_id)

        self.assert_unauthorized(response)

    def test_actualizar_usuario_normal(self):
        """Test que verifica que usuarios normales pueden actualizar."""
        self.authenticate_as_normal_user()

        data = {"notas": "Actualizado por usuario normal"}

        response = self.api_patch(self.url_name, data, pk=self.cliente.cliente_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["notas"], "Actualizado por usuario normal")

    def test_desactivar_cliente(self):
        """Test que verifica desactivación de cliente."""
        data = {"activo": False}

        response = self.api_patch(self.url_name, data, pk=self.cliente.cliente_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["activo"], False)

        # Verificar en base de datos
        cliente_actualizado = Cliente.objects.get(cliente_id=self.cliente.cliente_id)
        self.assertFalse(cliente_actualizado.activo)

    def test_reactivar_cliente(self):
        """Test que verifica reactivación de cliente."""
        # Desactivar cliente primero
        self.cliente.activo = False
        self.cliente.save()

        data = {"activo": True}

        response = self.api_patch(self.url_name, data, pk=self.cliente.cliente_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["activo"], True)

    def test_actualizar_campos_vacios(self):
        """Test que verifica manejo de campos vacíos."""
        data = {
            "notas": ""  # Campo opcional vacío
        }

        response = self.api_patch(self.url_name, data, pk=self.cliente.cliente_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["notas"], "")

    def test_actualizar_campos_requeridos_vacios(self):
        """Test que verifica validación de campos requeridos."""
        data = {
            "nombre": "",  # Campo requerido vacío
            "email": "",
        }

        response = self.api_patch(self.url_name, data, pk=self.cliente.cliente_id)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nombre", response.data)
        self.assertIn("email", response.data)
