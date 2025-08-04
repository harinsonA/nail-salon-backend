"""
Tests para CRUD de citas - API endpoints /api/citas/
"""

from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework import status
from ..utils import BaseAPITestCase
from apps.appointments.models import Cita


class TestListarCitas(BaseAPITestCase):
    """Tests para el endpoint de listado de citas."""

    def setUp(self):
        super().setUp()
        self.url_name = "citas:list"
        self.cliente = self.create_cliente_with_factory()

        # Crear citas de prueba
        self.cita1 = self.create_cita_with_factory(
            cliente=self.cliente, estado="programada"
        )
        self.cita2 = self.create_cita_with_factory(
            cliente=self.cliente, estado="completada"
        )

    def test_listar_citas_exitoso(self):
        response = self.api_get(self.url_name)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assert_pagination_response(response.data)
        self.assertEqual(response.data["count"], 2)

    def test_filtrar_citas_por_estado(self):
        response = self.api_get(self.url_name, {"estado": "programada"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_filtrar_citas_por_cliente(self):
        response = self.api_get(self.url_name, {"cliente": self.cliente.cliente_id})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)


class TestCrearCita(BaseAPITestCase):
    """Tests para el endpoint de creación de citas."""

    def setUp(self):
        super().setUp()
        self.url_name = "citas:list"
        self.cliente = self.create_cliente_with_factory()
        self.fecha_futura = timezone.now() + timedelta(days=1)

    def test_crear_cita_exitosa(self):
        data = {
            "cliente": self.cliente.cliente_id,
            "fecha_hora_cita": self.fecha_futura.isoformat(),
            "estado": "programada",
            "notas": "Cita de test",
        }
        response = self.api_post(self.url_name, data)
        self.assert_response_status(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["cliente"], self.cliente.cliente_id)

    def test_crear_cita_datos_faltantes(self):
        data = {"notas": "Sin cliente ni fecha"}
        response = self.api_post(self.url_name, data)
        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cliente", response.data)
        self.assertIn("fecha_hora_cita", response.data)

    def test_crear_cita_cliente_inexistente(self):
        data = {
            "cliente": 99999,
            "fecha_hora_cita": self.fecha_futura.isoformat(),
            "estado": "programada",
        }
        response = self.api_post(self.url_name, data)
        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)


class TestDetalleCita(BaseAPITestCase):
    """Tests para el endpoint de detalle de cita."""

    def setUp(self):
        super().setUp()
        self.cita = self.create_cita_with_factory()
        self.url_name = "citas:detail"

    def test_obtener_detalle_cita_exitoso(self):
        response = self.api_get(self.url_name, pk=self.cita.id)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.cita.id)

    def test_obtener_detalle_cita_inexistente(self):
        response = self.api_get(self.url_name, pk=99999)
        self.assert_not_found(response)


class TestActualizarCita(BaseAPITestCase):
    """Tests para el endpoint de actualización de cita."""

    def setUp(self):
        super().setUp()
        self.cita = self.create_cita_with_factory(estado="programada")
        self.url_name = "citas:detail"

    def test_actualizar_estado_cita(self):
        data = {"estado": "completada"}
        response = self.api_patch(self.url_name, data, pk=self.cita.id)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["estado"], "completada")

    def test_actualizar_cita_inexistente(self):
        data = {"estado": "cancelada"}
        response = self.api_patch(self.url_name, data, pk=99999)
        self.assert_not_found(response)


class TestEliminarCita(BaseAPITestCase):
    """Tests para el endpoint de eliminación de cita."""

    def setUp(self):
        super().setUp()
        self.cita = self.create_cita_with_factory()
        self.url_name = "citas:detail"

    def test_eliminar_cita_exitosa(self):
        response = self.api_delete(self.url_name, pk=self.cita.id)
        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Cita.objects.filter(id=self.cita.id).exists())

    def test_eliminar_cita_inexistente(self):
        response = self.api_delete(self.url_name, pk=99999)
        self.assert_not_found(response)
