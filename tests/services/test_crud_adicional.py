"""
Tests para obtener detalle, actualizar y eliminar servicios.
"""

from rest_framework import status
from ..utils import BaseAPITestCase
from apps.services.models import Servicio


class TestDetalleServicio(BaseAPITestCase):
    """Tests para el endpoint de detalle de servicio."""

    def setUp(self):
        super().setUp()
        self.servicio = self.create_servicio_with_factory(
            nombre_servicio="Manicure Test", precio=25000
        )
        self.url_name = "servicios:detail"

    def test_obtener_detalle_servicio_exitoso(self):
        response = self.api_get(self.url_name, pk=self.servicio.id)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.servicio.id)

    def test_obtener_detalle_servicio_inexistente(self):
        response = self.api_get(self.url_name, pk=99999)
        self.assert_not_found(response)


class TestActualizarServicio(BaseAPITestCase):
    """Tests para el endpoint de actualización de servicio."""

    def setUp(self):
        super().setUp()
        self.servicio = self.create_servicio_with_factory(
            nombre_servicio="Servicio Original", precio=20000
        )
        self.url_name = "servicios:detail"

    def test_actualizar_servicio_exitoso(self):
        data = {"nombre_servicio": "Servicio Actualizado", "precio": "30000.00"}
        response = self.api_patch(self.url_name, data, pk=self.servicio.id)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["nombre_servicio"], "Servicio Actualizado")

    def test_actualizar_servicio_inexistente(self):
        data = {"nombre_servicio": "No Existe"}
        response = self.api_patch(self.url_name, data, pk=99999)
        self.assert_not_found(response)


class TestEliminarServicio(BaseAPITestCase):
    """Tests para el endpoint de eliminación de servicio."""

    def setUp(self):
        super().setUp()
        self.servicio = self.create_servicio_with_factory()
        self.url_name = "servicios:detail"

    def test_eliminar_servicio_exitoso(self):
        response = self.api_delete(self.url_name, pk=self.servicio.id)
        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Servicio.objects.filter(id=self.servicio.id).exists())

    def test_eliminar_servicio_inexistente(self):
        response = self.api_delete(self.url_name, pk=99999)
        self.assert_not_found(response)
