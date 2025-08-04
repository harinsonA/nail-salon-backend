"""
Tests para CRUD de pagos - API endpoints /api/pagos/
"""

from decimal import Decimal
from rest_framework import status
from ..utils import BaseAPITestCase
from apps.payments.models import Pago


class TestListarPagos(BaseAPITestCase):
    """Tests para el endpoint de listado de pagos."""

    def setUp(self):
        super().setUp()
        self.url_name = "pagos:list"
        self.cita = self.create_cita_with_factory()

        # Crear pagos de prueba
        self.pago1 = self.create_pago_with_factory(
            cita=self.cita, monto_total=Decimal("25000.00"), estado_pago="pagado"
        )
        self.pago2 = self.create_pago_with_factory(
            cita=self.create_cita_with_factory(),
            monto_total=Decimal("35000.00"),
            estado_pago="pendiente",
        )

    def test_listar_pagos_exitoso(self):
        response = self.api_get(self.url_name)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assert_pagination_response(response.data)
        self.assertEqual(response.data["count"], 2)

    def test_filtrar_pagos_por_estado(self):
        response = self.api_get(self.url_name, {"estado_pago": "pagado"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_filtrar_pagos_por_cita(self):
        response = self.api_get(self.url_name, {"cita": self.cita.id})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)


class TestCrearPago(BaseAPITestCase):
    """Tests para el endpoint de creación de pagos."""

    def setUp(self):
        super().setUp()
        self.url_name = "pagos:list"
        self.cita = self.create_cita_with_factory()

    def test_crear_pago_exitoso(self):
        data = {
            "cita": self.cita.id,
            "monto_total": "50000.00",
            "metodo_pago": "efectivo",
            "estado_pago": "pagado",
            "notas_pago": "Pago de test",
        }
        response = self.api_post(self.url_name, data)
        self.assert_response_status(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["cita"], self.cita.id)
        self.assertEqual(response.data["monto_total"], "50000.00")

    def test_crear_pago_datos_faltantes(self):
        data = {"notas_pago": "Sin cita ni monto"}
        response = self.api_post(self.url_name, data)
        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cita", response.data)
        self.assertIn("monto_total", response.data)

    def test_crear_pago_monto_negativo(self):
        data = {
            "cita": self.cita.id,
            "monto_total": "-1000.00",
            "metodo_pago": "efectivo",
        }
        response = self.api_post(self.url_name, data)
        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)


class TestDetallePago(BaseAPITestCase):
    """Tests para el endpoint de detalle de pago."""

    def setUp(self):
        super().setUp()
        self.pago = self.create_pago_with_factory()
        self.url_name = "pagos:detail"

    def test_obtener_detalle_pago_exitoso(self):
        response = self.api_get(self.url_name, pk=self.pago.id)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.pago.id)

    def test_obtener_detalle_pago_inexistente(self):
        response = self.api_get(self.url_name, pk=99999)
        self.assert_not_found(response)


class TestActualizarPago(BaseAPITestCase):
    """Tests para el endpoint de actualización de pago."""

    def setUp(self):
        super().setUp()
        self.pago = self.create_pago_with_factory(estado_pago="pendiente")
        self.url_name = "pagos:detail"

    def test_actualizar_estado_pago(self):
        data = {"estado_pago": "pagado"}
        response = self.api_patch(self.url_name, data, pk=self.pago.id)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["estado_pago"], "pagado")

    def test_actualizar_pago_inexistente(self):
        data = {"estado_pago": "reembolsado"}
        response = self.api_patch(self.url_name, data, pk=99999)
        self.assert_not_found(response)


class TestEliminarPago(BaseAPITestCase):
    """Tests para el endpoint de eliminación de pago."""

    def setUp(self):
        super().setUp()
        self.pago = self.create_pago_with_factory()
        self.url_name = "pagos:detail"

    def test_eliminar_pago_exitoso(self):
        response = self.api_delete(self.url_name, pk=self.pago.id)
        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Pago.objects.filter(id=self.pago.id).exists())

    def test_eliminar_pago_inexistente(self):
        response = self.api_delete(self.url_name, pk=99999)
        self.assert_not_found(response)
