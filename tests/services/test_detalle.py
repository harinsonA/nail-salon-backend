"""
Tests para obtener detalle de servicio - API endpoint GET /api/servicios/{id}/
"""

from rest_framework import status
from ..utils import BaseAPITestCase
from apps.services.models import Servicio


class TestDetalleServicio(BaseAPITestCase):
    """Tests para el endpoint de detalle de servicio."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.servicio = self.create_servicio_with_factory(
            nombre_servicio="Manicure Premium",
            precio=30000,
            descripcion="Manicure completo con tratamiento especial",
            categoria="Manicure",
        )
        self.url_name = "servicio-detail"

    def test_obtener_detalle_servicio_exitoso(self):
        """Test que verifica que se puede obtener el detalle de un servicio."""
        response = self.api_get(self.url_name, pk=self.servicio.servicio_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar estructura de la respuesta
        expected_fields = [
            "servicio_id",
            "nombre_servicio",
            "precio",
            "precio_formateado",
            "descripcion",
            "duracion_estimada",
            "duracion_estimada_horas",
            "activo",
            "categoria",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        self.assert_response_contains_fields(response.data, expected_fields)

        # Verificar datos específicos
        self.assertEqual(response.data["servicio_id"], self.servicio.servicio_id)
        self.assertEqual(
            response.data["nombre_servicio"], self.servicio.nombre_servicio
        )
        self.assertEqual(float(response.data["precio"]), float(self.servicio.precio))

    def test_obtener_detalle_servicio_inexistente(self):
        """Test que verifica comportamiento con servicio inexistente."""
        response = self.api_get(self.url_name, pk=99999)

        self.assert_response_status(response, status.HTTP_404_NOT_FOUND)

    def test_estructura_completa_respuesta(self):
        """Test que verifica la estructura completa de la respuesta."""
        response = self.api_get(self.url_name, pk=self.servicio.servicio_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que tenga todos los campos esperados
        response_data = response.data
        self.assertIn("servicio_id", response_data)
        self.assertIn("nombre_servicio", response_data)
        self.assertIn("precio", response_data)
        self.assertIn("precio_formateado", response_data)
        self.assertIn("descripcion", response_data)
        self.assertIn("duracion_estimada", response_data)
        self.assertIn("duracion_estimada_horas", response_data)
        self.assertIn("activo", response_data)
        self.assertIn("categoria", response_data)
        self.assertIn("fecha_creacion", response_data)
        self.assertIn("fecha_actualizacion", response_data)

        # Verificar formato del precio formateado
        self.assertIn("$", response_data["precio_formateado"])

        # Verificar formato de duración
        self.assertIn("m", response_data["duracion_estimada_horas"])

    def test_detalle_servicio_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.client.force_authenticate(user=None)

        response = self.api_get(self.url_name, pk=self.servicio.servicio_id)

        self.assert_response_status(response, status.HTTP_401_UNAUTHORIZED)
