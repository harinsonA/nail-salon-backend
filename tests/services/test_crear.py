"""
Tests para crear servicios - API endpoint POST /api/servicios/
"""

from decimal import Decimal
from datetime import timedelta
from rest_framework import status
from ..utils import BaseAPITestCase
from apps.services.models import Servicio


class TestCrearServicios(BaseAPITestCase):
    """Tests para el endpoint de creación de servicios."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.url_name = "servicios:list"

    def test_crear_servicio_exitoso(self):
        """Test que verifica que se puede crear un servicio correctamente."""
        data = {
            "nombre_servicio": "Manicure Premium",
            "precio": "30000.00",
            "descripcion": "Manicure completo con tratamiento especial",
            "duracion_estimada": "01:30:00",  # 1 hora 30 minutos
            "activo": True,
            "categoria": "Manicure",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_201_CREATED)

        # Verificar que se creó en la base de datos
        self.assertTrue(
            Servicio.objects.filter(nombre_servicio="Manicure Premium").exists()
        )

        # Verificar estructura de la respuesta
        expected_fields = [
            "id",
            "nombre_servicio",
            "precio",
            "descripcion",
            "duracion_estimada",
            "activo",
            "categoria",
        ]
        self.assert_response_contains_fields(response.data, expected_fields)

        # Verificar valores
        self.assertEqual(response.data["nombre_servicio"], "Manicure Premium")
        self.assertEqual(response.data["precio"], "30000.00")
        self.assertEqual(response.data["categoria"], "Manicure")

    def test_crear_servicio_datos_minimos(self):
        """Test que verifica crear servicio con datos mínimos requeridos."""
        data = {"nombre_servicio": "Servicio Básico", "precio": "15000.00"}

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["activo"], True)  # Por defecto debe ser True

    def test_crear_servicio_nombre_duplicado(self):
        """Test que verifica que no se puede crear servicio con nombre duplicado."""
        # Crear servicio inicial
        self.create_servicio_with_factory(nombre_servicio="Servicio Único")

        data = {
            "nombre_servicio": "Servicio Único",  # Nombre duplicado
            "precio": "25000.00",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nombre_servicio", response.data)

    def test_crear_servicio_datos_faltantes(self):
        """Test que verifica validación de campos requeridos."""
        data = {
            "descripcion": "Servicio sin nombre ni precio"
            # Faltan nombre_servicio y precio
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nombre_servicio", response.data)
        self.assertIn("precio", response.data)

    def test_crear_servicio_precio_invalido(self):
        """Test que verifica validación de precio."""
        data = {
            "nombre_servicio": "Servicio Precio Inválido",
            "precio": "-1000.00",  # Precio negativo
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("precio", response.data)

    def test_crear_servicio_precio_cero(self):
        """Test que verifica precio cero."""
        data = {"nombre_servicio": "Servicio Gratis", "precio": "0.00"}

        response = self.api_post(self.url_name, data)

        # Dependiendo de las reglas de negocio, esto podría ser válido o no
        # Asumiendo que se permite precio 0
        self.assert_response_status(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["precio"], "0.00")

    def test_crear_servicio_duracion_invalida(self):
        """Test que verifica validación de duración."""
        data = {
            "nombre_servicio": "Servicio Duración Inválida",
            "precio": "20000.00",
            "duracion_estimada": "25:70:90",  # Formato inválido
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("duracion_estimada", response.data)

    def test_crear_servicio_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.unauthenticate()

        data = {"nombre_servicio": "Servicio Sin Auth", "precio": "15000.00"}

        response = self.api_post(self.url_name, data)
        self.assert_unauthorized(response)

    def test_crear_servicio_usuario_normal(self):
        """Test que verifica que usuarios normales pueden crear servicios."""
        self.authenticate_as_normal_user()

        data = {
            "nombre_servicio": "Servicio Usuario Normal",
            "precio": "18000.00",
            "categoria": "Test",
        }

        response = self.api_post(self.url_name, data)
        self.assert_response_status(response, status.HTTP_201_CREATED)

    def test_crear_servicio_nombre_largo(self):
        """Test que verifica límites de longitud en campos."""
        data = {
            "nombre_servicio": "A" * 201,  # Muy largo
            "precio": "20000.00",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nombre_servicio", response.data)

    def test_crear_servicio_descripcion_opcional(self):
        """Test que verifica que la descripción es opcional."""
        data = {
            "nombre_servicio": "Sin Descripción",
            "precio": "15000.00",
            "descripcion": "",  # Descripción vacía
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["descripcion"], "")

    def test_crear_servicio_categoria_opcional(self):
        """Test que verifica que la categoría es opcional."""
        data = {"nombre_servicio": "Sin Categoría", "precio": "12000.00"}

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_201_CREATED)
        # Verificar que categoria puede ser null o string vacío
        self.assertIn("categoria", response.data)

    def test_crear_servicio_precio_formato_decimal(self):
        """Test que verifica diferentes formatos de precio."""
        data = {
            "nombre_servicio": "Precio con Decimales",
            "precio": "25000.50",  # Con decimales
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["precio"], "25000.50")
