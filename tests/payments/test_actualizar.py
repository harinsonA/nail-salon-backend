"""
Tests para actualizar pagos - API endpoints PUT/PATCH /api/pagos/{id}/
"""

from decimal import Decimal
from rest_framework import status
from django.utils import timezone
from ..utils import BaseAPITestCase
from apps.payments.models import Pago


class TestActualizarPagos(BaseAPITestCase):
    """Tests para el endpoint de actualización de pagos."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.url_name = "payments:pago-detail"

        # Crear cita y pago de prueba
        self.cita = self.create_cita_with_factory(estado_cita="PENDIENTE")
        self.pago = self.create_pago_with_factory(
            cita=self.cita,
            monto_total=Decimal("30000.00"),
            metodo_pago="EFECTIVO",
            estado_pago="PENDIENTE",
            notas_pago="Pago inicial pendiente",
        )

    def test_actualizar_pago_completo_put(self):
        """Test que verifica actualización completa con PUT."""
        data = {
            "cita": self.cita.cita_id,
            "fecha_pago": timezone.now().isoformat(),
            "monto_total": "35000.00",
            "metodo_pago": "TARJETA",
            "estado_pago": "PAGADO",
            "notas_pago": "Pago actualizado completamente",
        }

        response = self.api_put(self.url_name, data, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar en base de datos
        pago_actualizado = Pago.objects.get(pago_id=self.pago.pago_id)
        self.assertEqual(pago_actualizado.monto_total, Decimal("35000.00"))
        self.assertEqual(pago_actualizado.metodo_pago, "TARJETA")
        self.assertEqual(pago_actualizado.estado_pago, "PAGADO")
        self.assertEqual(pago_actualizado.notas_pago, "Pago actualizado completamente")

        # Verificar respuesta
        self.assertEqual(response.data["monto_total"], "35000.00")
        self.assertEqual(response.data["metodo_pago"], "TARJETA")
        self.assertEqual(response.data["estado_pago"], "PAGADO")

    def test_actualizar_pago_parcial_patch(self):
        """Test que verifica actualización parcial con PATCH."""
        data = {"estado_pago": "PAGADO", "notas_pago": "Pago confirmado y procesado"}

        response = self.api_patch(self.url_name, data, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que solo se actualizaron los campos enviados
        pago_actualizado = Pago.objects.get(pago_id=self.pago.pago_id)
        self.assertEqual(pago_actualizado.estado_pago, "PAGADO")
        self.assertEqual(pago_actualizado.notas_pago, "Pago confirmado y procesado")

        # Verificar que otros campos no cambiaron
        self.assertEqual(pago_actualizado.monto_total, Decimal("30000.00"))  # No cambió
        self.assertEqual(pago_actualizado.metodo_pago, "EFECTIVO")  # No cambió

    def test_actualizar_estado_pago(self):
        """Test que verifica actualización específica del estado."""
        data = {"estado_pago": "PAGADO"}

        response = self.api_patch(self.url_name, data, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["estado_pago"], "PAGADO")

        # Verificar en base de datos
        pago_actualizado = Pago.objects.get(pago_id=self.pago.pago_id)
        self.assertEqual(pago_actualizado.estado_pago, "PAGADO")

    def test_actualizar_monto_pago(self):
        """Test que verifica actualización del monto."""
        data = {"monto_total": "45000.00"}

        response = self.api_patch(self.url_name, data, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["monto_total"], "45000.00")

        # Verificar en base de datos
        pago_actualizado = Pago.objects.get(pago_id=self.pago.pago_id)
        self.assertEqual(pago_actualizado.monto_total, Decimal("45000.00"))

    def test_actualizar_metodo_pago(self):
        """Test que verifica actualización del método de pago."""
        data = {"metodo_pago": "TRANSFERENCIA"}

        response = self.api_patch(self.url_name, data, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["metodo_pago"], "TRANSFERENCIA")

        # Verificar en base de datos
        pago_actualizado = Pago.objects.get(pago_id=self.pago.pago_id)
        self.assertEqual(pago_actualizado.metodo_pago, "TRANSFERENCIA")

    def test_actualizar_notas_pago(self):
        """Test que verifica actualización de las notas."""
        data = {"notas_pago": "Notas actualizadas del pago"}

        response = self.api_patch(self.url_name, data, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["notas_pago"], "Notas actualizadas del pago")

    def test_actualizar_pago_inexistente(self):
        """Test que verifica actualización de pago inexistente."""
        data = {"estado_pago": "pagado"}

        response = self.api_patch(self.url_name, data, pk=99999)

        self.assert_not_found(response)

    def test_actualizar_monto_negativo(self):
        """Test que verifica validación de monto negativo en actualización."""
        data = {"monto_total": "-1000.00"}

        response = self.api_patch(self.url_name, data, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("monto_total", response.data)

    def test_actualizar_monto_cero(self):
        """Test que verifica validación de monto cero."""
        data = {"monto_total": "0.00"}

        response = self.api_patch(self.url_name, data, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("monto_total", response.data)

    def test_actualizar_estado_invalido(self):
        """Test que verifica validación de estado inválido."""
        data = {"estado_pago": "estado_inexistente"}

        response = self.api_patch(self.url_name, data, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("estado_pago", response.data)

    def test_actualizar_metodo_invalido(self):
        """Test que verifica validación de método de pago inválido."""
        data = {"metodo_pago": "metodo_inexistente"}

        response = self.api_patch(self.url_name, data, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("metodo_pago", response.data)

    def test_actualizar_cita_inexistente(self):
        """Test que verifica validación al cambiar a cita inexistente."""
        data = {"cita": 99999}

        response = self.api_patch(self.url_name, data, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cita", response.data)

    def test_actualizar_cambiar_cita(self):
        """Test que verifica cambio de cita asociada al pago."""
        nueva_cita = self.create_cita_with_factory(estado_cita="PROGRAMADA")
        data = {"cita": nueva_cita.cita_id}

        response = self.api_patch(self.url_name, data, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["cita"], nueva_cita.cita_id)

        # Verificar en base de datos
        pago_actualizado = Pago.objects.get(pago_id=self.pago.pago_id)
        self.assertEqual(pago_actualizado.cita.cita_id, nueva_cita.cita_id)

    def test_actualizar_monto_formato_invalido(self):
        """Test que verifica validación de formato de monto."""
        data = {"monto_total": "precio_texto"}

        response = self.api_patch(self.url_name, data, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("monto_total", response.data)

    def test_actualizar_datos_vacios(self):
        """Test que verifica actualización con datos vacíos."""
        data = {}

        response = self.api_patch(self.url_name, data, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # No debe haber cambios
        pago_sin_cambios = Pago.objects.get(pago_id=self.pago.pago_id)
        self.assertEqual(pago_sin_cambios.estado_pago, "PENDIENTE")
        self.assertEqual(pago_sin_cambios.monto_total, Decimal("30000.00"))

    def test_actualizar_estado_pendiente_a_reembolsado(self):
        """Test que verifica transición de estado pendiente a reembolsado."""
        data = {
            "estado_pago": "CANCELADO",
            "notas_pago": "Cancelado por el cliente",
        }

        response = self.api_patch(self.url_name, data, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["estado_pago"], "CANCELADO")

    def test_actualizar_multiples_campos(self):
        """Test que verifica actualización de múltiples campos."""
        data = {
            "monto_total": "40000.00",
            "metodo_pago": "CHEQUE",
            "estado_pago": "PAGADO",
            "notas_pago": "Actualización múltiple de campos",
        }

        response = self.api_patch(self.url_name, data, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar todos los campos actualizados
        self.assertEqual(response.data["monto_total"], "40000.00")
        self.assertEqual(response.data["metodo_pago"], "CHEQUE")
        self.assertEqual(response.data["estado_pago"], "PAGADO")
        self.assertEqual(
            response.data["notas_pago"], "Actualización múltiple de campos"
        )

    def test_actualizar_pago_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.unauthenticate()

        data = {"estado_pago": "pagado"}
        response = self.api_patch(self.url_name, data, pk=self.pago.pago_id)

        self.assert_unauthorized(response)

    def test_actualizar_pago_usuario_normal(self):
        """Test que verifica que usuarios normales pueden actualizar pagos."""
        self.authenticate_as_normal_user()

        data = {"estado_pago": "PAGADO"}
        response = self.api_patch(self.url_name, data, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)

    def test_actualizar_preserva_fecha_creacion(self):
        """Test que verifica que la fecha de creación no cambia."""
        fecha_creacion_original = self.pago.fecha_creacion

        data = {"estado_pago": "PAGADO"}
        response = self.api_patch(self.url_name, data, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que fecha_creacion no cambió
        pago_actualizado = Pago.objects.get(pago_id=self.pago.pago_id)
        self.assertEqual(pago_actualizado.fecha_creacion, fecha_creacion_original)

    def test_actualizar_actualiza_fecha_modificacion(self):
        """Test que verifica que la fecha de actualización cambia."""
        fecha_actualizacion_original = self.pago.fecha_actualizacion

        # Esperar un momento para asegurar diferencia en timestamp
        import time

        time.sleep(0.01)

        data = {"notas_pago": "Nota actualizada"}
        response = self.api_patch(self.url_name, data, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que fecha_actualizacion cambió
        pago_actualizado = Pago.objects.get(pago_id=self.pago.pago_id)
        self.assertNotEqual(
            pago_actualizado.fecha_actualizacion, fecha_actualizacion_original
        )
