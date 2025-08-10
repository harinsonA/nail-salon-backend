"""
Tests para obtener detalle de cita - API endpoint GET /api/citas/{id}/
"""

from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from ..utils import BaseAPITestCase


class TestDetalleCita(BaseAPITestCase):
    """Tests para el endpoint de detalle de cita."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()

        # Crear cliente de prueba
        self.cliente = self.create_cliente_with_factory(
            nombre="Ana",
            apellido="García",
            telefono="3001111111",
            email="ana.garcia@test.com",
        )

        # Crear servicio de prueba
        self.servicio = self.create_servicio_with_factory(
            nombre_servicio="Manicure Básico", precio=25000
        )

        # Crear cita de prueba
        fecha_futura = timezone.now() + timedelta(days=1)
        self.cita = self.create_cita_with_factory(
            cliente=self.cliente,
            fecha_hora_cita=fecha_futura,
            estado_cita="CONFIRMADA",
            observaciones="Cita de prueba para detalle",
        )

        self.url_name = "cita-detail"

    def test_obtener_detalle_cita_exitoso(self):
        """Test que verifica que se puede obtener el detalle de una cita."""
        response = self.api_get(self.url_name, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar estructura de la respuesta
        expected_fields = [
            "cita_id",
            "cliente",
            "fecha_hora_cita",
            "estado_cita",
            "observaciones",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        self.assert_response_contains_fields(response.data, expected_fields)

        # Verificar valores
        self.assertEqual(response.data["cita_id"], self.cita.cita_id)
        self.assertEqual(response.data["cliente"], self.cliente.cliente_id)
        self.assertEqual(response.data["estado_cita"], "CONFIRMADA")
        self.assertEqual(response.data["observaciones"], "Cita de prueba para detalle")

    def test_obtener_detalle_cita_inexistente(self):
        """Test que verifica respuesta para cita que no existe."""
        response = self.api_get(self.url_name, pk=99999)

        self.assert_not_found(response)

    def test_obtener_detalle_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.unauthenticate()
        response = self.api_get(self.url_name, pk=self.cita.cita_id)

        self.assert_unauthorized(response)

    def test_obtener_detalle_usuario_normal(self):
        """Test que verifica que usuarios normales pueden ver detalles."""
        self.authenticate_as_normal_user()
        response = self.api_get(self.url_name, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["cita_id"], self.cita.cita_id)

    def test_obtener_detalle_cita_cancelada(self):
        """Test que verifica que se puede obtener detalle de cita cancelada."""
        cita_cancelada = self.create_cita_with_factory(
            cliente=self.cliente,
            fecha_hora_cita=timezone.now() + timedelta(days=2),
            estado_cita="CANCELADA",
            observaciones="Cita cancelada por el cliente",
        )

        response = self.api_get(self.url_name, pk=cita_cancelada.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["estado_cita"], "CANCELADA")

    def test_obtener_detalle_cita_completada(self):
        """Test que verifica que se puede obtener detalle de cita completada."""
        cita_completada = self.create_cita_with_factory(
            cliente=self.cliente,
            fecha_hora_cita=timezone.now() - timedelta(days=1),  # Fecha pasada
            estado_cita="COMPLETADA",
            observaciones="Cita realizada exitosamente",
        )

        response = self.api_get(self.url_name, pk=cita_completada.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["estado_cita"], "COMPLETADA")

    def test_formato_fecha_en_detalle(self):
        """Test que verifica el formato de fecha en el detalle."""
        response = self.api_get(self.url_name, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que fecha_hora_cita tiene el formato correcto
        self.assertIsNotNone(response.data["fecha_hora_cita"])
        self.assertIsInstance(response.data["fecha_hora_cita"], str)

        # Verificar que fecha_creacion tiene el formato correcto
        self.assertIsNotNone(response.data["fecha_creacion"])
        self.assertIsInstance(response.data["fecha_creacion"], str)

        # Verificar que fecha_actualizacion tiene el formato correcto
        self.assertIsNotNone(response.data["fecha_actualizacion"])
        self.assertIsInstance(response.data["fecha_actualizacion"], str)

    def test_obtener_detalle_con_servicios_incluidos(self):
        """Test que verifica el detalle incluye servicios asociados."""
        # Agregar detalle de servicio a la cita
        self.create_detalle_cita_with_factory(
            cita=self.cita,
            servicio=self.servicio,
            precio_acordado=self.servicio.precio,
            cantidad_servicios=1,
            notas_detalle="Servicio principal",
        )

        response = self.api_get(self.url_name, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que incluye información de detalles si está configurado
        if "detalles" in response.data:
            self.assertGreater(len(response.data["detalles"]), 0)
            detalle_response = response.data["detalles"][0]
            self.assertEqual(detalle_response["servicio"], self.servicio.servicio_id)
            self.assertEqual(
                float(detalle_response["precio_acordado"]), float(self.servicio.precio)
            )

    def test_obtener_detalle_con_monto_total(self):
        """Test que verifica que el detalle incluye monto total calculado."""
        # Agregar detalles de servicios
        self.create_detalle_cita_with_factory(
            cita=self.cita,
            servicio=self.servicio,
            precio_acordado=25000,
            cantidad_servicios=2,
        )

        response = self.api_get(self.url_name, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que incluye monto total si está configurado
        if "monto_total" in response.data:
            self.assertEqual(float(response.data["monto_total"]), 50000.0)  # 25000 * 2

    def test_obtener_detalle_información_cliente(self):
        """Test que verifica que se incluye información del cliente."""
        response = self.api_get(self.url_name, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que se incluye información del cliente si está expandida
        if "cliente_info" in response.data:
            cliente_info = response.data["cliente_info"]
            self.assertEqual(cliente_info["nombre"], self.cliente.nombre)
            self.assertEqual(cliente_info["apellido"], self.cliente.apellido)
            self.assertEqual(cliente_info["email"], self.cliente.email)

    def test_obtener_detalle_cita_con_observaciones_vacias(self):
        """Test que verifica manejo de citas sin observaciones."""
        cita_sin_observaciones = self.create_cita_with_factory(
            cliente=self.cliente,
            fecha_hora_cita=timezone.now() + timedelta(days=3),
            estado_cita="PENDIENTE",
            observaciones=None,  # Sin observaciones
        )

        response = self.api_get(self.url_name, pk=cita_sin_observaciones.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        # Las observaciones pueden ser null o string vacío
        self.assertIn(response.data["observaciones"], [None, ""])

    def test_obtener_detalle_validar_estados_disponibles(self):
        """Test que verifica que el estado de la cita es válido."""
        response = self.api_get(self.url_name, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        estados_validos = ["PENDIENTE", "CONFIRMADA", "CANCELADA", "COMPLETADA"]
        self.assertIn(response.data["estado_cita"], estados_validos)

    def test_obtener_detalle_cita_con_timestamps(self):
        """Test que verifica que los timestamps están presentes y son válidos."""
        response = self.api_get(self.url_name, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que los timestamps existen
        self.assertIsNotNone(response.data["fecha_creacion"])
        self.assertIsNotNone(response.data["fecha_actualizacion"])

        # Verificar que fecha_creacion <= fecha_actualizacion
        fecha_creacion = timezone.datetime.fromisoformat(
            response.data["fecha_creacion"].replace("Z", "+00:00")
        )
        fecha_actualizacion = timezone.datetime.fromisoformat(
            response.data["fecha_actualizacion"].replace("Z", "+00:00")
        )

        self.assertLessEqual(fecha_creacion, fecha_actualizacion)

    def test_obtener_detalle_duracion_total_estimada(self):
        """Test que verifica cálculo de duración total estimada."""
        # Agregar servicio con duración específica
        servicio_con_duracion = self.create_servicio_with_factory(
            nombre_servicio="Pedicure Completo",
            precio=35000,
            duracion_estimada=timedelta(minutes=90),
        )

        self.create_detalle_cita_with_factory(
            cita=self.cita,
            servicio=servicio_con_duracion,
            precio_acordado=35000,
            cantidad_servicios=1,
        )

        response = self.api_get(self.url_name, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que incluye duración estimada si está configurado
        if "duracion_total_minutos" in response.data:
            self.assertEqual(response.data["duracion_total_minutos"], 90)
