"""
Tests para listar pagos - API endpoint GET /api/pagos/
"""

from decimal import Decimal
from rest_framework import status
from ..utils import BaseAPITestCase
from apps.payments.models import Pago


class TestListarPagos(BaseAPITestCase):
    """Tests para el endpoint de listado de pagos."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.url_name = "payments:pago-list"

        # Crear citas de prueba
        self.cita1 = self.create_cita_with_factory()
        self.cita2 = self.create_cita_with_factory()
        self.cita3 = self.create_cita_with_factory()

        # Crear pagos de prueba
        self.pago1 = self.create_pago_with_factory(
            cita=self.cita1,
            monto_total=Decimal("25000.00"),
            metodo_pago="EFECTIVO",
            estado_pago="PAGADO",
        )
        self.pago2 = self.create_pago_with_factory(
            cita=self.cita2,
            monto_total=Decimal("35000.00"),
            metodo_pago="TARJETA",
            estado_pago="PENDIENTE",
        )
        self.pago3 = self.create_pago_with_factory(
            cita=self.cita3,
            monto_total=Decimal("40000.00"),
            metodo_pago="TRANSFERENCIA",
            estado_pago="CANCELADO",
        )

    def test_listar_pagos_exitoso(self):
        """Test que verifica que se pueden listar los pagos correctamente."""
        response = self.api_get(self.url_name)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assert_pagination_response(response.data)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 3)

        # Verificar estructura de cada pago
        pago = response.data["results"][0]
        expected_fields = [
            "id",
            "cita",
            "monto_total",
            "metodo_pago",
            "estado_pago",
            "fecha_pago",
            "notas_pago",
            "fecha_creacion",
            "fecha_creacion",
        ]
        self.assert_response_contains_fields(pago, expected_fields)

    def test_listar_pagos_vacio(self):
        """Test que verifica el listado cuando no hay pagos."""
        # Eliminar todos los pagos
        Pago.objects.all().delete()

        response = self.api_get(self.url_name)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(len(response.data["results"]), 0)

    def test_filtrar_pagos_por_estado(self):
        """Test que verifica filtros por estado de pago."""
        # Filtrar por estado "PAGADO"
        response = self.api_get(self.url_name, {"estado_pago": "PAGADO"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["estado_pago"], "PAGADO")

        # Filtrar por estado "PENDIENTE"
        response = self.api_get(self.url_name, {"estado_pago": "PENDIENTE"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["estado_pago"], "PENDIENTE")

    def test_filtrar_pagos_por_metodo(self):
        """Test que verifica filtros por método de pago."""
        # Filtrar por efectivo
        response = self.api_get(self.url_name, {"metodo_pago": "EFECTIVO"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["metodo_pago"], "EFECTIVO")

        # Filtrar por tarjeta
        response = self.api_get(self.url_name, {"metodo_pago": "TARJETA"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_filtrar_pagos_por_cita(self):
        """Test que verifica filtros por cita específica."""
        response = self.api_get(self.url_name, {"cita": self.cita1.cita_id})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["cita"], self.cita1.cita_id)

    def test_filtrar_pagos_por_rango_fecha(self):
        """Test que verifica filtros por rango de fechas."""
        # Filtro por fecha desde
        from datetime import date

        fecha_desde = date.today().strftime("%Y-%m-%d")

        response = self.api_get(self.url_name, {"fecha_desde": fecha_desde})
        self.assert_response_status(response, status.HTTP_200_OK)
        # Todos los pagos deberían estar incluidos si se crearon hoy
        self.assertGreaterEqual(response.data["count"], 3)

    def test_filtrar_pagos_por_monto_minimo(self):
        """Test que verifica filtros por monto mínimo."""
        response = self.api_get(self.url_name, {"monto_minimo": "30000"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)  # pago2 y pago3

        # Verificar que todos los resultados tienen monto >= 30000
        for pago in response.data["results"]:
            self.assertGreaterEqual(float(pago["monto_total"]), 30000.0)

    def test_filtrar_pagos_por_monto_maximo(self):
        """Test que verifica filtros por monto máximo."""
        response = self.api_get(self.url_name, {"monto_maximo": "30000"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)  # solo pago1

        # Verificar que todos los resultados tienen monto <= 30000
        for pago in response.data["results"]:
            self.assertLessEqual(float(pago["monto_total"]), 30000.0)

    def test_ordenamiento_pagos(self):
        """Test que verifica ordenamiento de resultados."""
        # Ordenar por monto ascendente
        response = self.api_get(self.url_name, {"ordering": "monto_total"})
        self.assert_response_status(response, status.HTTP_200_OK)

        montos = [float(pago["monto_total"]) for pago in response.data["results"]]
        self.assertEqual(montos, sorted(montos))

        # Ordenar por monto descendente
        response = self.api_get(self.url_name, {"ordering": "-monto_total"})
        self.assert_response_status(response, status.HTTP_200_OK)

        montos = [float(pago["monto_total"]) for pago in response.data["results"]]
        self.assertEqual(montos, sorted(montos, reverse=True))

    def test_ordenamiento_por_fecha(self):
        """Test que verifica ordenamiento por fecha."""
        # Ordenar por fecha de creación descendente (más recientes primero)
        response = self.api_get(self.url_name, {"ordering": "-fecha_creacion"})
        self.assert_response_status(response, status.HTTP_200_OK)

        fechas = response.data["results"]
        self.assertGreaterEqual(len(fechas), 3)

    def test_busqueda_pagos(self):
        """Test que verifica búsqueda por texto en notas."""
        # Crear pago con notas específicas
        pago_especial = self.create_pago_with_factory(
            cita=self.create_cita_with_factory(),
            notas_pago="Pago especial con descuento aplicado",
        )

        response = self.api_get(self.url_name, {"search": "especial"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], pago_especial.pago_id)

    def test_paginacion_pagos(self):
        """Test que verifica la paginación."""
        # Crear más pagos para probar paginación
        for i in range(15):
            cita = self.create_cita_with_factory()
            self.create_pago_with_factory(
                cita=cita, monto_total=Decimal(f"{20000 + (i * 1000)}.00")
            )

        # Test primera página
        response = self.api_get(self.url_name, {"page": 1, "page_size": 10})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertIsNotNone(response.data["links"]["next"])

        # Test segunda página
        response = self.api_get(self.url_name, {"page": 2, "page_size": 10})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertGreater(len(response.data["results"]), 0)

    def test_filtros_combinados(self):
        """Test que verifica combinación de múltiples filtros."""
        response = self.api_get(
            self.url_name,
            {
                "estado_pago": "PAGADO",
                "metodo_pago": "EFECTIVO",
                "monto_minimo": "20000",
            },
        )

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

        pago = response.data["results"][0]
        self.assertEqual(pago["estado_pago"], "PAGADO")
        self.assertEqual(pago["metodo_pago"], "EFECTIVO")
        self.assertGreaterEqual(float(pago["monto_total"]), 20000.0)

    def test_listar_pagos_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.unauthenticate()

        response = self.api_get(self.url_name)
        self.assert_unauthorized(response)

    def test_listar_pagos_usuario_normal(self):
        """Test que verifica que usuarios normales pueden listar pagos."""
        self.authenticate_as_normal_user()

        response = self.api_get(self.url_name)
        self.assert_response_status(response, status.HTTP_200_OK)

    def test_estructura_respuesta_detallada(self):
        """Test que verifica la estructura detallada de la respuesta."""
        response = self.api_get(self.url_name)
        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar estructura de paginación
        self.assertIn("count", response.data)
        self.assertIn("links", response.data)
        self.assertIn("results", response.data)

        # Verificar que links contiene next y previous
        self.assertIn("next", response.data["links"])
        self.assertIn("previous", response.data["links"])

        # Verificar estructura de cada resultado
        if response.data["results"]:
            pago = response.data["results"][0]
            self.assertIn("monto_total", pago)
            self.assertIsInstance(
                pago["monto_total"], str
            )  # Decimal serializado como string
