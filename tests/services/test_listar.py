"""
Tests para listar servicios - API endpoint GET /api/servicios/
"""

from rest_framework import status
from ..utils import BaseAPITestCase
from apps.services.models import Servicio


class TestListarServicios(BaseAPITestCase):
    """Tests para el endpoint de listado de servicios."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.url_name = "servicios:list"

        # Crear algunos servicios de prueba
        self.servicio1 = self.create_servicio_with_factory(
            nombre_servicio="Manicure Clásico", precio=25000, categoria="Manicure"
        )
        self.servicio2 = self.create_servicio_with_factory(
            nombre_servicio="Pedicure Spa",
            precio=35000,
            categoria="Pedicure",
            activo=False,
        )
        self.servicio3 = self.create_servicio_with_factory(
            nombre_servicio="Nail Art", precio=15000, categoria="Decoración"
        )

    def test_listar_servicios_exitoso(self):
        """Test que verifica que se pueden listar los servicios correctamente."""
        response = self.api_get(self.url_name)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assert_pagination_response(response.data)

        # Verificar que se retornan los servicios creados
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 3)

        # Verificar estructura de cada servicio
        expected_fields = [
            "id",
            "nombre_servicio",
            "precio",
            "descripcion",
            "duracion_estimada",
            "activo",
            "categoria",
        ]
        for servicio_data in response.data["results"]:
            self.assert_response_contains_fields(servicio_data, expected_fields)

    def test_listar_servicios_con_filtros(self):
        """Test para verificar filtros de búsqueda."""
        # Filtro por nombre
        response = self.api_get(self.url_name, {"search": "Manicure"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["nombre_servicio"], "Manicure Clásico"
        )

        # Filtro por activo
        response = self.api_get(self.url_name, {"activo": "true"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)  # Manicure y Nail Art están activos

        # Filtro por inactivo
        response = self.api_get(self.url_name, {"activo": "false"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)  # Solo Pedicure está inactivo

        # Filtro por categoría
        response = self.api_get(self.url_name, {"categoria": "Manicure"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_listar_servicios_ordenamiento(self):
        """Test para verificar ordenamiento de resultados."""
        response = self.api_get(self.url_name, {"ordering": "nombre_servicio"})
        self.assert_response_status(response, status.HTTP_200_OK)

        nombres = [servicio["nombre_servicio"] for servicio in response.data["results"]]
        self.assertEqual(nombres, ["Manicure Clásico", "Nail Art", "Pedicure Spa"])

        # Ordenamiento por precio descendente
        response = self.api_get(self.url_name, {"ordering": "-precio"})
        self.assert_response_status(response, status.HTTP_200_OK)

        precios = [float(servicio["precio"]) for servicio in response.data["results"]]
        self.assertEqual(precios, [35000.0, 25000.0, 15000.0])

    def test_listar_servicios_paginacion(self):
        """Test para verificar la paginación."""
        # Crear más servicios para probar paginación
        for i in range(15):
            self.create_servicio_with_factory(
                nombre_servicio=f"Servicio {i}", precio=10000 + (i * 1000)
            )

        # Test primera página
        response = self.api_get(self.url_name, {"page": 1, "page_size": 10})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

        # Test segunda página
        response = self.api_get(self.url_name, {"page": 2, "page_size": 10})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data["results"]), 8
        )  # 18 total - 10 primera página
        self.assertIsNone(response.data["next"])
        self.assertIsNotNone(response.data["previous"])

    def test_listar_servicios_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.unauthenticate()
        response = self.api_get(self.url_name)
        self.assert_unauthorized(response)

    def test_listar_servicios_usuario_normal(self):
        """Test que verifica que usuarios normales pueden listar servicios."""
        self.authenticate_as_normal_user()
        response = self.api_get(self.url_name)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assert_pagination_response(response.data)

    def test_listar_servicios_sin_resultados(self):
        """Test para verificar respuesta cuando no hay servicios."""
        # Eliminar todos los servicios
        Servicio.objects.all().delete()

        response = self.api_get(self.url_name)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assert_pagination_response(response.data)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(len(response.data["results"]), 0)

    def test_listar_servicios_busqueda_por_categoria(self):
        """Test para verificar búsqueda por categoría."""
        response = self.api_get(self.url_name, {"search": "Decoración"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["categoria"], "Decoración")

    def test_formato_precio_en_respuesta(self):
        """Test para verificar formato de precio en la respuesta."""
        response = self.api_get(self.url_name)
        self.assert_response_status(response, status.HTTP_200_OK)

        if response.data["results"]:
            servicio = response.data["results"][0]
            # Verificar que el precio es un string con formato decimal
            self.assertIsInstance(servicio["precio"], str)
            # Verificar que se puede convertir a float
            precio_float = float(servicio["precio"])
            self.assertGreater(precio_float, 0)

    def test_formato_duracion_en_respuesta(self):
        """Test para verificar formato de duración en la respuesta."""
        response = self.api_get(self.url_name)
        self.assert_response_status(response, status.HTTP_200_OK)

        if response.data["results"]:
            servicio = response.data["results"][0]
            # Verificar que duracion_estimada está presente
            self.assertIn("duracion_estimada", servicio)
            # El formato puede variar según la serialización (HH:MM:SS o seconds)
            self.assertIsNotNone(servicio["duracion_estimada"])
