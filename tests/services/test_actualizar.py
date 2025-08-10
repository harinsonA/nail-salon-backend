"""
Tests para actualizar servicios - API endpoint PUT/PATCH /api/servicios/{id}/
"""

from decimal import Decimal
from datetime import timedelta
from rest_framework import status
from ..utils import BaseAPITestCase
from apps.services.models import Servicio


class TestActualizarServicios(BaseAPITestCase):
    """Tests para el endpoint de actualización de servicios."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.servicio = self.create_servicio_with_factory(
            nombre_servicio="Manicure Básico",
            precio=25000,
            descripcion="Manicure estándar",
            categoria="Manicure",
        )
        self.url_name = "servicio-detail"

    def test_actualizar_servicio_completo_put(self):
        """Test que verifica actualización completa con PUT."""
        data = {
            "nombre_servicio": "Manicure Premium Actualizado",
            "precio": "35000.00",
            "descripcion": "Manicure premium con tratamiento especial",
            "duracion_estimada": "02:00:00",  # 2 horas
            "activo": True,
            "categoria": "Manicure Premium",
        }

        response = self.api_put(self.url_name, data, pk=self.servicio.servicio_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que se actualizó en la base de datos
        servicio_actualizado = Servicio.objects.get(
            servicio_id=self.servicio.servicio_id
        )
        self.assertEqual(
            servicio_actualizado.nombre_servicio, "Manicure Premium Actualizado"
        )
        self.assertEqual(servicio_actualizado.precio, Decimal("35000.00"))
        self.assertEqual(servicio_actualizado.categoria, "Manicure Premium")

    def test_actualizar_servicio_parcial_patch(self):
        """Test que verifica actualización parcial con PATCH."""
        data = {"precio": "30000.00", "descripcion": "Descripción actualizada"}

        response = self.api_patch(self.url_name, data, pk=self.servicio.servicio_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que solo se actualizaron los campos enviados
        servicio_actualizado = Servicio.objects.get(
            servicio_id=self.servicio.servicio_id
        )
        self.assertEqual(servicio_actualizado.precio, Decimal("30000.00"))
        self.assertEqual(servicio_actualizado.descripcion, "Descripción actualizada")
        # Verificar que otros campos no cambiaron
        self.assertEqual(
            servicio_actualizado.nombre_servicio, self.servicio.nombre_servicio
        )
        self.assertEqual(servicio_actualizado.categoria, self.servicio.categoria)

    def test_actualizar_servicio_inexistente(self):
        """Test que verifica comportamiento con servicio inexistente."""
        data = {"nombre_servicio": "Servicio No Existe", "precio": "25000.00"}

        response = self.api_put(self.url_name, data, pk=99999)

        self.assert_response_status(response, status.HTTP_404_NOT_FOUND)

    def test_actualizar_precio_invalido(self):
        """Test que verifica validación de precio inválido."""
        data = {
            "precio": "-10.00"  # Precio inválido (negativo)
        }

        response = self.api_patch(self.url_name, data, pk=self.servicio.servicio_id)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("precio", response.data)

    def test_actualizar_precio_negativo(self):
        """Test que verifica validación de precio negativo."""
        data = {
            "precio": "-1000.00"  # Precio negativo
        }

        response = self.api_patch(self.url_name, data, pk=self.servicio.servicio_id)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("precio", response.data)

    def test_actualizar_duracion_invalida(self):
        """Test que verifica validación de duración inválida."""
        data = {
            "duracion_estimada": "00:00:00"  # Duración inválida
        }

        response = self.api_patch(self.url_name, data, pk=self.servicio.servicio_id)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("duracion_estimada", response.data)

    def test_actualizar_nombre_muy_largo(self):
        """Test que verifica límites de longitud en nombre."""
        data = {
            "nombre_servicio": "x" * 201  # Excede el límite de 200 caracteres
        }

        response = self.api_patch(self.url_name, data, pk=self.servicio.servicio_id)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nombre_servicio", response.data)

    def test_actualizar_categoria_opcional(self):
        """Test que verifica que la categoría es opcional."""
        data = {
            "categoria": ""  # Categoría vacía
        }

        response = self.api_patch(self.url_name, data, pk=self.servicio.servicio_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que se actualizó
        servicio_actualizado = Servicio.objects.get(
            servicio_id=self.servicio.servicio_id
        )
        self.assertEqual(servicio_actualizado.categoria, "")

    def test_actualizar_servicio_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.client.force_authenticate(user=None)

        data = {"precio": "30000.00"}

        response = self.api_patch(self.url_name, data, pk=self.servicio.servicio_id)

        self.assert_response_status(response, status.HTTP_401_UNAUTHORIZED)

    def test_estructura_respuesta_actualizacion(self):
        """Test que verifica la estructura de la respuesta de actualización."""
        data = {"precio": "28000.00", "descripcion": "Nueva descripción"}

        response = self.api_patch(self.url_name, data, pk=self.servicio.servicio_id)

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

        # Verificar que los datos actualizados están en la respuesta
        self.assertEqual(float(response.data["precio"]), 28000.00)
        self.assertEqual(response.data["descripcion"], "Nueva descripción")
