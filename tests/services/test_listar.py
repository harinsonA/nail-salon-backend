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
        self.url_name = "servicio-list"

        # Crear algunos servicios de prueba
        self.servicio1 = self.create_servicio_with_factory(
            nombre_servicio="Manicure Clásico",
            precio=25000,
            categoria="Manicure",
        )
        self.servicio2 = self.create_servicio_with_factory(
            nombre_servicio="Pedicure Spa",
            precio=35000,
            categoria="Pedicure",
        )

    def test_listar_servicios_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.client.logout()
        response = self.api_get(self.url_name)
        self.assert_response_status(response, status.HTTP_401_UNAUTHORIZED)

    def test_listar_servicios_exitoso(self):
        """Test que verifica que se pueden listar los servicios correctamente."""
        response = self.api_get(self.url_name)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertIn("results", response.data)

        # Verificar que retorna los servicios creados
        servicios = response.data["results"]
        self.assertGreaterEqual(len(servicios), 2)

        # Verificar estructura de cada servicio
        servicio_data = servicios[0]
        expected_fields = [
            "id",
            "servicio_id",
            "nombre_servicio",
            "precio",
            "precio_formateado",
            "descripcion",
            "duracion_estimada",
            "duracion_estimada_horas",
            "categoria",
            "activo",
        ]

        self.assert_response_contains_fields(servicio_data, expected_fields)

    def test_listar_servicios_sin_resultados(self):
        """Test para verificar respuesta cuando no hay servicios."""
        # Eliminar todos los servicios
        Servicio.objects.all().delete()

        response = self.api_get(self.url_name)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_listar_servicios_usuario_normal(self):
        """Test que verifica que usuarios normales pueden listar servicios."""
        # Crear usuario normal
        user = self.create_user_with_factory(username="usuario_normal", is_staff=False)
        self.client.force_authenticate(user=user)

        response = self.api_get(self.url_name)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["results"]), 2)

    def test_listar_servicios_ordenamiento(self):
        """Test para verificar ordenamiento de resultados."""
        # Crear servicio adicional con precio diferente
        self.create_servicio_with_factory(nombre_servicio="Servicio Caro", precio=50000)

        response = self.api_get(self.url_name, {"ordering": "precio"})

        self.assert_response_status(response, status.HTTP_200_OK)
        servicios = response.data["results"]

        # Verificar que están ordenados por precio ascendente
        precios = [float(servicio["precio"]) for servicio in servicios]
        self.assertEqual(precios, sorted(precios))

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
        self.assertIsNotNone(response.data["links"]["next"])
        self.assertIsNone(response.data["links"]["previous"])

        # Test segunda página
        response = self.api_get(self.url_name, {"page": 2, "page_size": 10})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data["results"]), 7
        )  # 15 nuevos + 2 existentes = 17 total, segunda página tiene 7
        self.assertIsNone(response.data["links"]["next"])
        self.assertIsNotNone(response.data["links"]["previous"])

    def test_listar_servicios_con_filtros(self):
        """Test para verificar filtros de búsqueda."""
        # Test filtro por categoría usando filterset_fields
        response = self.api_get(self.url_name, {"categoria": "Manicure"})
        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que solo devuelve servicios de la categoría especificada
        for servicio in response.data["results"]:
            self.assertIn("Manicure", servicio["categoria"])

        # Test filtro por estado activo
        response = self.api_get(self.url_name, {"activo": True})
        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que solo devuelve servicios activos
        for servicio in response.data["results"]:
            self.assertTrue(servicio["activo"])

    def test_listar_servicios_busqueda_por_categoria(self):
        """Test para verificar búsqueda por categoría."""
        response = self.api_get(self.url_name, {"search": "Pedicure"})

        self.assert_response_status(response, status.HTTP_200_OK)
        servicios = response.data["results"]

        # Verificar que encuentra servicios relacionados
        self.assertGreater(len(servicios), 0)

        # Verificar que al menos uno contiene "Pedicure" en el nombre o categoría
        found_pedicure = any(
            "Pedicure" in servicio["nombre_servicio"]
            or "Pedicure" in servicio["categoria"]
            for servicio in servicios
        )
        self.assertTrue(found_pedicure)

    def test_formato_precio_en_respuesta(self):
        """Test para verificar formato de precio en la respuesta."""
        response = self.api_get(self.url_name)

        self.assert_response_status(response, status.HTTP_200_OK)
        servicios = response.data["results"]

        for servicio in servicios:
            # Verificar que tiene precio en formato numérico
            self.assertIsInstance(servicio["precio"], str)
            # Verificar que tiene precio formateado
            self.assertIn("precio_formateado", servicio)
            self.assertTrue(servicio["precio_formateado"].startswith("$"))

    def test_formato_duracion_en_respuesta(self):
        """Test para verificar formato de duración en la respuesta."""
        response = self.api_get(self.url_name)

        self.assert_response_status(response, status.HTTP_200_OK)
        servicios = response.data["results"]

        for servicio in servicios:
            # Verificar que tiene duración estimada
            self.assertIn("duracion_estimada", servicio)
            # Verificar que tiene duración en formato legible
            self.assertIn("duracion_estimada_horas", servicio)
