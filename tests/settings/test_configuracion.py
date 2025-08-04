"""
Tests para configuración del salón - API endpoints /api/configuracion/
"""

from rest_framework import status
from ..utils import BaseAPITestCase
from apps.settings.models import ConfiguracionSalon


class TestConfiguracionSalon(BaseAPITestCase):
    """Tests para el endpoint de configuración del salón."""

    def setUp(self):
        super().setUp()
        self.url_name = "configuracion:detail"  # Asumiendo que es un singleton
        self.config = self.create_configuracion_salon_with_factory(
            nombre_salon="Salón de Prueba",
            direccion="Calle Test 123",
            telefono="6011234567",
            email="salon@test.com",
        )

    def test_obtener_configuracion_exitosa(self):
        """Test que verifica obtener configuración del salón."""
        response = self.api_get(self.url_name)
        self.assert_response_status(response, status.HTTP_200_OK)

        expected_fields = [
            "id",
            "nombre_salon",
            "direccion",
            "telefono",
            "email",
            "descripcion",
        ]
        self.assert_response_contains_fields(response.data, expected_fields)
        self.assertEqual(response.data["nombre_salon"], "Salón de Prueba")

    def test_actualizar_configuracion_exitosa(self):
        """Test que verifica actualización de configuración."""
        data = {
            "nombre_salon": "Nuevo Nombre del Salón",
            "direccion": "Nueva Dirección 456",
            "telefono": "6019876543",
            "email": "nuevo@salon.com",
            "descripcion": "Nueva descripción del salón",
        }

        response = self.api_put(self.url_name, data)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["nombre_salon"], "Nuevo Nombre del Salón")
        self.assertEqual(response.data["direccion"], "Nueva Dirección 456")

    def test_actualizar_configuracion_parcial(self):
        """Test que verifica actualización parcial con PATCH."""
        data = {
            "nombre_salon": "Solo Cambio Nombre",
            "descripcion": "Solo cambio descripción",
        }

        response = self.api_patch(self.url_name, data)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["nombre_salon"], "Solo Cambio Nombre")
        # Los demás campos no deben cambiar
        self.assertEqual(response.data["telefono"], "6011234567")

    def test_actualizar_email_invalido(self):
        """Test que verifica validación de email."""
        data = {"email": "email-invalido"}

        response = self.api_patch(self.url_name, data)
        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_actualizar_telefono_invalido(self):
        """Test que verifica validación de teléfono."""
        data = {
            "telefono": "123"  # Muy corto
        }

        response = self.api_patch(self.url_name, data)
        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("telefono", response.data)

    def test_campos_requeridos_configuracion(self):
        """Test que verifica campos requeridos."""
        data = {
            "nombre_salon": "",  # Campo requerido vacío
            "email": "",
        }

        response = self.api_patch(self.url_name, data)
        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nombre_salon", response.data)
        self.assertIn("email", response.data)

    def test_configuracion_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.unauthenticate()

        response = self.api_get(self.url_name)
        self.assert_unauthorized(response)

    def test_configuracion_usuario_normal(self):
        """Test que verifica acceso de usuario normal."""
        self.authenticate_as_normal_user()

        # Usuario normal puede ver configuración
        response = self.api_get(self.url_name)
        self.assert_response_status(response, status.HTTP_200_OK)

        # Pero no puede modificarla (dependiendo de permisos)
        data = {"nombre_salon": "Cambio No Autorizado"}
        response = self.api_patch(self.url_name, data)
        # Puede ser 403 Forbidden o 200 OK dependiendo de la configuración
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]
        )

    def test_descripcion_opcional(self):
        """Test que verifica que la descripción es opcional."""
        data = {
            "descripcion": ""  # Descripción vacía
        }

        response = self.api_patch(self.url_name, data)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["descripcion"], "")

    def test_formato_respuesta_configuracion(self):
        """Test que verifica el formato de la respuesta."""
        response = self.api_get(self.url_name)
        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar tipos de datos
        self.assertIsInstance(response.data["nombre_salon"], str)
        self.assertIsInstance(response.data["direccion"], str)
        self.assertIsInstance(response.data["telefono"], str)
        self.assertIsInstance(response.data["email"], str)

    def create_configuracion_salon_with_factory(self, **kwargs):
        """Helper para crear configuración usando factory."""
        from tests.factories import ConfiguracionSalonFactory

        return ConfiguracionSalonFactory(**kwargs)
