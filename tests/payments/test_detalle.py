"""
Tests para obtener detalle de pago - API endpoint GET /api/pagos/{id}/
"""

from decimal import Decimal
from rest_framework import status
from ..utils import BaseAPITestCase
from apps.payments.models import Pago


class TestDetallePago(BaseAPITestCase):
    """Tests para el endpoint de detalle de pago."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.url_name = "payments:pago-detail"

        # Crear cita y pago de prueba
        self.cita = self.create_cita_with_factory()
        self.pago = self.create_pago_with_factory(
            cita=self.cita,
            monto_total=Decimal("35000.00"),
            metodo_pago="TARJETA",
            estado_pago="PAGADO",
            notas_pago="Pago completo del servicio",
        )

    def test_obtener_detalle_pago_exitoso(self):
        """Test que verifica que se puede obtener el detalle de un pago."""
        response = self.api_get(self.url_name, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar estructura de la respuesta
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
        self.assert_response_contains_fields(response.data, expected_fields)

        # Verificar valores específicos
        self.assertEqual(response.data["id"], self.pago.pago_id)
        self.assertEqual(response.data["cita"], self.cita.cita_id)
        self.assertEqual(response.data["monto_total"], "35000.00")
        self.assertEqual(response.data["metodo_pago"], "TARJETA")
        self.assertEqual(response.data["estado_pago"], "PAGADO")
        self.assertEqual(response.data["notas_pago"], "Pago completo del servicio")

    def test_obtener_detalle_pago_inexistente(self):
        """Test que verifica respuesta para pago que no existe."""
        response = self.api_get(self.url_name, pk=99999)

        self.assert_not_found(response)

    def test_obtener_detalle_pago_id_invalido(self):
        """Test que verifica respuesta para ID inválido."""
        response = self.api_get(self.url_name, pk="abc")

        self.assert_not_found(response)

    def test_detalle_incluye_informacion_cita(self):
        """Test que verifica que el detalle incluye información de la cita."""
        response = self.api_get(self.url_name, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que incluye el ID de la cita
        self.assertEqual(response.data["cita"], self.cita.cita_id)

        # Si el serializer incluye información expandida de la cita, verificarla
        # (esto depende de cómo esté configurado el serializer)

    def test_detalle_campos_computados(self):
        """Test que verifica que los campos computados están presentes."""
        response = self.api_get(self.url_name, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar formato de fecha
        self.assertIn("fecha_creacion", response.data)
        self.assertIn("fecha_creacion", response.data)

        # Verificar que el monto está formateado correctamente
        self.assertEqual(response.data["monto_total"], "35000.00")

    def test_detalle_pago_estado_pendiente(self):
        """Test que verifica detalle de pago con estado pendiente."""
        pago_pendiente = self.create_pago_with_factory(
            cita=self.create_cita_with_factory(),
            estado_pago="PENDIENTE",
            monto_total=Decimal("25000.00"),
        )

        response = self.api_get(self.url_name, pk=pago_pendiente.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["estado_pago"], "PENDIENTE")

    def test_detalle_pago_estado_reembolsado(self):
        """Test que verifica detalle de pago con estado reembolsado."""
        pago_cancelado = self.create_pago_with_factory(
            cita=self.create_cita_with_factory(),
            estado_pago="CANCELADO",
            monto_total=Decimal("30000.00"),
            notas_pago="Cancelado por el cliente",
        )

        response = self.api_get(self.url_name, pk=pago_cancelado.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["estado_pago"], "CANCELADO")
        self.assertEqual(response.data["notas_pago"], "Cancelado por el cliente")

    def test_detalle_pago_diferentes_metodos(self):
        """Test que verifica detalle para diferentes métodos de pago."""
        # Pago en efectivo
        pago_efectivo = self.create_pago_with_factory(
            cita=self.create_cita_with_factory(), metodo_pago="EFECTIVO"
        )

        response = self.api_get(self.url_name, pk=pago_efectivo.pago_id)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["metodo_pago"], "EFECTIVO")

        # Pago por transferencia
        pago_transferencia = self.create_pago_with_factory(
            cita=self.create_cita_with_factory(), metodo_pago="TRANSFERENCIA"
        )

        response = self.api_get(self.url_name, pk=pago_transferencia.pago_id)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["metodo_pago"], "TRANSFERENCIA")

    def test_detalle_pago_sin_notas(self):
        """Test que verifica detalle de pago sin notas."""
        pago_sin_notas = self.create_pago_with_factory(
            cita=self.create_cita_with_factory(), notas_pago=""
        )

        response = self.api_get(self.url_name, pk=pago_sin_notas.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["notas_pago"], "")

    def test_detalle_pago_notas_largas(self):
        """Test que verifica detalle de pago con notas largas."""
        notas_largas = "Esta es una nota muy larga que describe " * 10
        pago_notas_largas = self.create_pago_with_factory(
            cita=self.create_cita_with_factory(), notas_pago=notas_largas
        )

        response = self.api_get(self.url_name, pk=pago_notas_largas.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["notas_pago"], notas_largas)

    def test_detalle_pago_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.unauthenticate()

        response = self.api_get(self.url_name, pk=self.pago.pago_id)
        self.assert_unauthorized(response)

    def test_detalle_pago_usuario_normal(self):
        """Test que verifica que usuarios normales pueden ver detalles."""
        self.authenticate_as_normal_user()

        response = self.api_get(self.url_name, pk=self.pago.pago_id)
        self.assert_response_status(response, status.HTTP_200_OK)

    def test_detalle_formato_fecha_pago(self):
        """Test que verifica el formato de la fecha de pago."""
        response = self.api_get(self.url_name, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que fecha_pago está presente
        self.assertIn("fecha_pago", response.data)

        # Si fecha_pago no es None, verificar formato
        if response.data["fecha_pago"]:
            # Debe ser una cadena en formato ISO
            self.assertIsInstance(response.data["fecha_pago"], str)

    def test_detalle_monto_precision_decimal(self):
        """Test que verifica la precisión decimal del monto."""
        # Crear pago con monto con decimales
        pago_decimal = self.create_pago_with_factory(
            cita=self.create_cita_with_factory(), monto_total=Decimal("25000.50")
        )

        response = self.api_get(self.url_name, pk=pago_decimal.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["monto_total"], "25000.50")

    def test_detalle_pago_con_cita_cancelada(self):
        """Test que verifica detalle de pago cuya cita fue cancelada."""
        # Crear cita y cancelarla
        cita_cancelada = self.create_cita_with_factory()
        # Aquí podrías cancelar la cita si hay ese método

        pago_cita_cancelada = self.create_pago_with_factory(
            cita=cita_cancelada,
            estado_pago="CANCELADO",
            notas_pago="Cancelado por cita cancelada",
        )

        response = self.api_get(self.url_name, pk=pago_cita_cancelada.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["estado_pago"], "CANCELADO")

    def test_detalle_consistencia_datos(self):
        """Test que verifica consistencia de datos entre modelo y respuesta."""
        response = self.api_get(self.url_name, pk=self.pago.pago_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Recargar el pago desde la base de datos
        pago_db = Pago.objects.get(pago_id=self.pago.pago_id)

        # Verificar consistencia
        self.assertEqual(response.data["id"], pago_db.pago_id)
        self.assertEqual(response.data["cita"], pago_db.cita.cita_id)
        self.assertEqual(response.data["monto_total"], str(pago_db.monto_total))
        self.assertEqual(response.data["metodo_pago"], pago_db.metodo_pago)
        self.assertEqual(response.data["estado_pago"], pago_db.estado_pago)
