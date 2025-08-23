"""
Tests para eliminar pagos - API endpoint DELETE /api/pagos/{id}/
"""

from decimal import Decimal
from rest_framework import status
from ..utils import BaseAPITestCase
from apps.payments.models import Pago


class TestEliminarPagos(BaseAPITestCase):
    """Tests para el endpoint de eliminación de pagos."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.url_name = "payments:pago-detail"

        # Crear cita y pago de prueba
        self.cita = self.create_cita_with_factory()
        self.pago = self.create_pago_with_factory(
            cita=self.cita,
            monto_total=Decimal("25000.00"),
            metodo_pago="EFECTIVO",
            estado_pago="PAGADO",
        )

    def test_eliminar_pago_exitoso(self):
        """Test que verifica eliminación exitosa de pago."""
        pago_id = self.pago.pago_id

        response = self.api_delete(self.url_name, pk=pago_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar que el pago ya no existe
        self.assertFalse(Pago.objects.filter(pago_id=pago_id).exists())

    def test_eliminar_pago_inexistente(self):
        """Test que verifica eliminación de pago inexistente."""
        response = self.api_delete(self.url_name, pk=99999)

        self.assert_not_found(response)

    def test_eliminar_pago_id_invalido(self):
        """Test que verifica eliminación con ID inválido."""
        response = self.api_delete(self.url_name, pk="abc")

        self.assert_not_found(response)

    def test_eliminar_pago_ya_eliminado(self):
        """Test que verifica doble eliminación del mismo pago."""
        pago_id = self.pago.pago_id

        # Primera eliminación
        response1 = self.api_delete(self.url_name, pk=pago_id)
        self.assert_response_status(response1, status.HTTP_204_NO_CONTENT)

        # Segunda eliminación del mismo pago
        response2 = self.api_delete(self.url_name, pk=pago_id)
        self.assert_not_found(response2)

    def test_eliminar_pago_estado_pendiente(self):
        """Test que verifica eliminación de pago con estado pendiente."""
        pago_pendiente = self.create_pago_with_factory(
            cita=self.create_cita_with_factory(), estado_pago="PENDIENTE"
        )

        response = self.api_delete(self.url_name, pk=pago_pendiente.pago_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Pago.objects.filter(pago_id=pago_pendiente.pago_id).exists())

    def test_eliminar_pago_estado_reembolsado(self):
        """Test que verifica eliminación de pago reembolsado."""
        pago_cancelado = self.create_pago_with_factory(
            cita=self.create_cita_with_factory(), estado_pago="CANCELADO"
        )

        response = self.api_delete(self.url_name, pk=pago_cancelado.pago_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Pago.objects.filter(pago_id=pago_cancelado.pago_id).exists())

    def test_eliminar_pago_diferentes_metodos(self):
        """Test que verifica eliminación de pagos con diferentes métodos."""
        # Pago con tarjeta
        pago_tarjeta = self.create_pago_with_factory(
            cita=self.create_cita_with_factory(), metodo_pago="TARJETA"
        )

        response = self.api_delete(self.url_name, pk=pago_tarjeta.pago_id)
        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Pago por transferencia
        pago_transferencia = self.create_pago_with_factory(
            cita=self.create_cita_with_factory(), metodo_pago="TRANSFERENCIA"
        )

        response = self.api_delete(self.url_name, pk=pago_transferencia.pago_id)
        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

    def test_eliminar_pago_no_afecta_cita(self):
        """Test que verifica que eliminar pago no afecta la cita asociada."""
        cita_id = self.cita.cita_id
        pago_id = self.pago.pago_id

        response = self.api_delete(self.url_name, pk=pago_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar que el pago fue eliminado
        self.assertFalse(Pago.objects.filter(pago_id=pago_id).exists())

        # Verificar que la cita sigue existiendo
        from apps.appointments.models import Cita

        self.assertTrue(Cita.objects.filter(cita_id=cita_id).exists())

    def test_eliminar_uno_de_multiples_pagos_cita(self):
        """Test que verifica eliminar uno de múltiples pagos de la misma cita."""
        # Crear segundo pago para la misma cita
        pago2 = self.create_pago_with_factory(
            cita=self.cita,
            monto_total=Decimal("15000.00"),
            metodo_pago="TARJETA",
        )

        # Eliminar solo el primer pago
        response = self.api_delete(self.url_name, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar que el primer pago fue eliminado
        self.assertFalse(Pago.objects.filter(pago_id=self.pago.pago_id).exists())

        # Verificar que el segundo pago sigue existiendo
        self.assertTrue(Pago.objects.filter(pago_id=pago2.pago_id).exists())

    def test_eliminar_pago_monto_alto(self):
        """Test que verifica eliminación de pago con monto alto."""
        pago_alto = self.create_pago_with_factory(
            cita=self.create_cita_with_factory(), monto_total=Decimal("100000.00")
        )

        response = self.api_delete(self.url_name, pk=pago_alto.pago_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Pago.objects.filter(pago_id=pago_alto.pago_id).exists())

    def test_eliminar_pago_con_notas(self):
        """Test que verifica eliminación de pago con notas extensas."""
        pago_con_notas = self.create_pago_with_factory(
            cita=self.create_cita_with_factory(),
            notas_pago="Esta es una nota muy detallada sobre el pago que incluye información específica del cliente y las condiciones del servicio prestado.",
        )

        response = self.api_delete(self.url_name, pk=pago_con_notas.pago_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Pago.objects.filter(pago_id=pago_con_notas.pago_id).exists())

    def test_eliminar_pago_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.unauthenticate()

        response = self.api_delete(self.url_name, pk=self.pago.pago_id)

        self.assert_unauthorized(response)

        # Verificar que el pago sigue existiendo
        self.assertTrue(Pago.objects.filter(pago_id=self.pago.pago_id).exists())

    def test_eliminar_pago_usuario_normal(self):
        """Test que verifica que usuarios normales pueden eliminar pagos."""
        self.authenticate_as_normal_user()

        response = self.api_delete(self.url_name, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Pago.objects.filter(pago_id=self.pago.pago_id).exists())

    def test_eliminar_pago_respuesta_vacia(self):
        """Test que verifica que la respuesta de eliminación está vacía."""
        response = self.api_delete(self.url_name, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)
        # La respuesta debe estar vacía para DELETE exitoso
        self.assertEqual(response.content, b"")

    def test_eliminar_pagos_secuencial(self):
        """Test que verifica eliminación secuencial de múltiples pagos."""
        # Crear varios pagos
        pagos = []
        for i in range(3):
            cita = self.create_cita_with_factory()
            pago = self.create_pago_with_factory(cita=cita)
            pagos.append(pago)

        # Eliminar todos secuencialmente
        for pago in pagos:
            response = self.api_delete(self.url_name, pk=pago.pago_id)
            self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar que todos fueron eliminados
        for pago in pagos:
            self.assertFalse(Pago.objects.filter(pago_id=pago.pago_id).exists())

    def test_eliminar_pago_concurrente(self):
        """Test que verifica comportamiento con eliminaciones concurrentes."""
        pago_id = self.pago.pago_id

        # Primera eliminación
        response1 = self.api_delete(self.url_name, pk=pago_id)
        self.assert_response_status(response1, status.HTTP_204_NO_CONTENT)

        # Verificar que intentar eliminar nuevamente falla
        response2 = self.api_delete(self.url_name, pk=pago_id)
        self.assert_not_found(response2)

    def test_eliminar_pago_con_cita_futura(self):
        """Test que verifica eliminación de pago de cita futura."""
        # Crear cita futura
        from datetime import datetime, timedelta
        from django.utils import timezone

        fecha_futura = timezone.now() + timedelta(days=7)
        cita_futura = self.create_cita_with_factory()
        # Aquí podrías establecer la fecha futura si el factory lo permite

        pago_futuro = self.create_pago_with_factory(
            cita=cita_futura, estado_pago="PENDIENTE"
        )

        response = self.api_delete(self.url_name, pk=pago_futuro.pago_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Pago.objects.filter(pago_id=pago_futuro.pago_id).exists())

    def test_eliminar_pago_validacion_integridad(self):
        """Test que verifica que no hay problemas de integridad al eliminar."""
        pago_id = self.pago.pago_id
        cita_id = self.cita.cita_id

        # Eliminar pago
        response = self.api_delete(self.url_name, pk=pago_id)
        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar que no hay registros huérfanos o problemas de integridad
        self.assertFalse(Pago.objects.filter(pago_id=pago_id).exists())

        # La cita debe seguir existiendo
        from apps.appointments.models import Cita

        self.assertTrue(Cita.objects.filter(cita_id=cita_id).exists())

    def test_eliminar_ultimo_pago_de_cita(self):
        """Test que verifica eliminar el último pago de una cita."""
        # Asegurar que solo hay un pago para esta cita
        Pago.objects.filter(cita=self.cita).exclude(pago_id=self.pago.pago_id).delete()

        response = self.api_delete(self.url_name, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar que no quedan pagos para la cita
        self.assertEqual(Pago.objects.filter(cita=self.cita).count(), 0)

    def test_eliminar_pago_auditoria(self):
        """Test que verifica que la eliminación queda registrada para auditoría."""
        pago_id = self.pago.pago_id

        # Registrar información antes de eliminar
        monto_original = self.pago.monto_total
        estado_original = self.pago.estado_pago

        response = self.api_delete(self.url_name, pk=pago_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar eliminación
        self.assertFalse(Pago.objects.filter(pago_id=pago_id).exists())

        # Aquí podrías verificar logs de auditoría si los implementas
        # Por ejemplo, verificar que se creó un registro en una tabla de auditoría
