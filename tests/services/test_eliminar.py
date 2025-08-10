"""
Tests para eliminar servicios - API endpoint DELETE /api/servicios/{id}/
"""

from rest_framework import status
from ..utils import BaseAPITestCase
from apps.services.models import Servicio


class TestEliminarServicios(BaseAPITestCase):
    """Tests para el endpoint de eliminación de servicios."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.servicio = self.create_servicio_with_factory(
            nombre_servicio="Servicio a Eliminar",
            precio=20000,
            descripcion="Servicio de prueba para eliminar",
            categoria="Test",
        )
        self.url_name = "servicio-detail"

    def test_eliminar_servicio_exitoso(self):
        """Test que verifica que se puede eliminar un servicio correctamente."""
        servicio_id = self.servicio.servicio_id

        response = self.api_delete(self.url_name, pk=servicio_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar que se eliminó de la base de datos
        self.assertFalse(Servicio.objects.filter(servicio_id=servicio_id).exists())

    def test_eliminar_servicio_inexistente(self):
        """Test que verifica comportamiento con servicio inexistente."""
        response = self.api_delete(self.url_name, pk=99999)

        self.assert_response_status(response, status.HTTP_404_NOT_FOUND)

    def test_eliminar_servicio_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.client.force_authenticate(user=None)

        response = self.api_delete(self.url_name, pk=self.servicio.servicio_id)

        self.assert_response_status(response, status.HTTP_401_UNAUTHORIZED)

        # Verificar que no se eliminó
        self.assertTrue(
            Servicio.objects.filter(servicio_id=self.servicio.servicio_id).exists()
        )

    def test_eliminar_y_verificar_conteo(self):
        """Test que verifica que el conteo de servicios se actualiza correctamente."""
        # Crear servicios adicionales
        self.create_servicio_with_factory(nombre_servicio="Servicio 1")
        self.create_servicio_with_factory(nombre_servicio="Servicio 2")

        # Verificar conteo inicial
        conteo_inicial = Servicio.objects.count()
        self.assertEqual(conteo_inicial, 3)  # servicio original + 2 nuevos

        # Eliminar un servicio
        response = self.api_delete(self.url_name, pk=self.servicio.servicio_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar conteo final
        conteo_final = Servicio.objects.count()
        self.assertEqual(conteo_final, 2)

    def test_eliminar_servicio_multiple_veces(self):
        """Test que verifica que no se puede eliminar el mismo servicio múltiples veces."""
        servicio_id = self.servicio.servicio_id

        # Primera eliminación - debe ser exitosa
        response = self.api_delete(self.url_name, pk=servicio_id)
        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Segunda eliminación - debe fallar
        response = self.api_delete(self.url_name, pk=servicio_id)
        self.assert_response_status(response, status.HTTP_404_NOT_FOUND)

    def test_respuesta_sin_contenido(self):
        """Test que verifica que la respuesta de eliminación no tiene contenido."""
        response = self.api_delete(self.url_name, pk=self.servicio.servicio_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar que no hay contenido en la respuesta
        self.assertEqual(len(response.content), 0)
