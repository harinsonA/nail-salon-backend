"""
Tests para actualizar citas - API endpoint PUT/PATCH /api/citas/{id}/
"""

from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from ..utils import BaseAPITestCase
from apps.appointments.models import Cita


class TestActualizarCitas(BaseAPITestCase):
    """Tests para el endpoint de actualización de citas."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()

        # Crear cliente de prueba
        self.cliente = self.create_cliente_with_factory(
            nombre="Carlos",
            apellido="Martínez",
            telefono="3001234567",
            email="carlos.martinez@test.com",
        )

        # Crear otro cliente para tests de cambio
        self.otro_cliente = self.create_cliente_with_factory(
            nombre="María",
            apellido="López",
            telefono="3009876543",
            email="maria.lopez@test.com",
        )

        # Crear servicio de prueba
        self.servicio = self.create_servicio_with_factory(
            nombre_servicio="Manicure Básico", precio=25000
        )

        # Crear cita de prueba
        self.fecha_original = timezone.now() + timedelta(days=1)
        self.cita = self.create_cita_with_factory(
            cliente=self.cliente,
            fecha_hora_cita=self.fecha_original,
            estado_cita="PENDIENTE",
            observaciones="Cita original para actualizar",
        )

        self.url_name = "cita-detail"

    def test_actualizar_cita_completa_put(self):
        """Test que verifica actualización completa con PUT."""
        nueva_fecha = timezone.now() + timedelta(days=2)
        data = {
            "cliente": self.cliente.cliente_id,
            "fecha_hora_cita": nueva_fecha.isoformat(),
            "estado_cita": "CONFIRMADA",
            "observaciones": "Cita actualizada completamente",
        }

        response = self.api_put(self.url_name, data, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que se actualizó en la base de datos
        cita_actualizada = Cita.objects.get(cita_id=self.cita.cita_id)
        self.assertEqual(cita_actualizada.estado_cita, "CONFIRMADA")
        self.assertEqual(
            cita_actualizada.observaciones, "Cita actualizada completamente"
        )

        # Verificar respuesta
        self.assertEqual(response.data["estado_cita"], "CONFIRMADA")
        self.assertEqual(
            response.data["observaciones"], "Cita actualizada completamente"
        )

    def test_actualizar_cita_parcial_patch(self):
        """Test que verifica actualización parcial con PATCH."""
        data = {
            "estado_cita": "CONFIRMADA",
            "observaciones": "Solo estado y observaciones actualizadas",
        }

        response = self.api_patch(self.url_name, data, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que solo se actualizaron los campos enviados
        cita_actualizada = Cita.objects.get(cita_id=self.cita.cita_id)
        self.assertEqual(cita_actualizada.estado_cita, "CONFIRMADA")
        self.assertEqual(
            cita_actualizada.observaciones, "Solo estado y observaciones actualizadas"
        )
        self.assertEqual(
            cita_actualizada.cliente.cliente_id, self.cliente.cliente_id
        )  # No cambió

    def test_actualizar_cita_inexistente(self):
        """Test que verifica respuesta para cita que no existe."""
        data = {"estado_cita": "CANCELADA", "observaciones": "No existe"}

        response = self.api_patch(self.url_name, data, pk=99999)

        self.assert_not_found(response)

    def test_actualizar_cliente_cita(self):
        """Test que verifica que se puede cambiar el cliente de una cita."""
        data = {"cliente": self.otro_cliente.cliente_id}

        response = self.api_patch(self.url_name, data, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar en base de datos
        cita_actualizada = Cita.objects.get(cita_id=self.cita.cita_id)
        self.assertEqual(
            cita_actualizada.cliente.cliente_id, self.otro_cliente.cliente_id
        )

    def test_actualizar_cliente_inexistente(self):
        """Test que verifica que no se puede actualizar con cliente inexistente."""
        data = {
            "cliente": 99999  # Cliente que no existe
        }

        response = self.api_patch(self.url_name, data, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cliente", response.data)

    def test_actualizar_fecha_cita(self):
        """Test que verifica actualización de fecha de cita."""
        nueva_fecha = timezone.now() + timedelta(days=3)
        data = {"fecha_hora_cita": nueva_fecha.isoformat()}

        response = self.api_patch(self.url_name, data, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar en base de datos
        cita_actualizada = Cita.objects.get(cita_id=self.cita.cita_id)
        # Comparar fechas redondeando a segundos para evitar problemas de microsegundos
        fecha_actualizada = cita_actualizada.fecha_hora_cita.replace(microsecond=0)
        nueva_fecha_redondeada = nueva_fecha.replace(microsecond=0)
        self.assertEqual(fecha_actualizada, nueva_fecha_redondeada)

    def test_actualizar_fecha_pasada(self):
        """Test que verifica validación de fecha en el pasado."""
        fecha_pasada = timezone.now() - timedelta(days=1)
        data = {"fecha_hora_cita": fecha_pasada.isoformat()}

        response = self.api_patch(self.url_name, data, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fecha_hora_cita", response.data)

    def test_actualizar_estado_invalido(self):
        """Test que verifica validación de estado inválido."""
        data = {"estado_cita": "ESTADO_INEXISTENTE"}

        response = self.api_patch(self.url_name, data, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("estado_cita", response.data)

    def test_actualizar_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.unauthenticate()

        data = {"estado_cita": "CONFIRMADA"}

        response = self.api_patch(self.url_name, data, pk=self.cita.cita_id)

        self.assert_unauthorized(response)

    def test_actualizar_usuario_normal(self):
        """Test que verifica que usuarios normales pueden actualizar."""
        self.authenticate_as_normal_user()

        data = {"observaciones": "Actualizado por usuario normal"}

        response = self.api_patch(self.url_name, data, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(
            response.data["observaciones"], "Actualizado por usuario normal"
        )

    def test_cambiar_estado_a_confirmada(self):
        """Test que verifica cambio de estado a CONFIRMADA."""
        data = {"estado_cita": "CONFIRMADA"}

        response = self.api_patch(self.url_name, data, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["estado_cita"], "CONFIRMADA")

        # Verificar en base de datos
        cita_actualizada = Cita.objects.get(cita_id=self.cita.cita_id)
        self.assertEqual(cita_actualizada.estado_cita, "CONFIRMADA")

    def test_cambiar_estado_a_cancelada(self):
        """Test que verifica cambio de estado a CANCELADA."""
        data = {
            "estado_cita": "CANCELADA",
            "observaciones": "Cita cancelada por el cliente",
        }

        response = self.api_patch(self.url_name, data, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["estado_cita"], "CANCELADA")

    def test_cambiar_estado_a_completada(self):
        """Test que verifica cambio de estado a COMPLETADA."""
        data = {
            "estado_cita": "COMPLETADA",
            "observaciones": "Servicio realizado exitosamente",
        }

        response = self.api_patch(self.url_name, data, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["estado_cita"], "COMPLETADA")

    def test_actualizar_observaciones_vacias(self):
        """Test que verifica manejo de observaciones vacías."""
        data = {"observaciones": ""}

        response = self.api_patch(self.url_name, data, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["observaciones"], "")

    def test_actualizar_observaciones_null(self):
        """Test que verifica manejo de observaciones nulas."""
        data = {"observaciones": None}

        response = self.api_patch(self.url_name, data, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertIsNone(response.data["observaciones"])

    def test_actualizar_cita_completada_no_permitido(self):
        """Test que verifica que no se puede modificar cita completada."""
        # Cambiar cita a completada primero
        self.cita.estado_cita = "COMPLETADA"
        self.cita.save()

        data = {"observaciones": "Intentando modificar cita completada"}

        response = self.api_patch(self.url_name, data, pk=self.cita.cita_id)

        # Dependiendo de la lógica de negocio, podría ser 400 o 403
        self.assertIn(
            response.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN],
        )

    def test_actualizar_cita_cancelada_no_permitido(self):
        """Test que verifica que no se puede modificar cita cancelada."""
        # Cambiar cita a cancelada primero
        self.cita.estado_cita = "CANCELADA"
        self.cita.save()

        data = {"observaciones": "Intentando modificar cita cancelada"}

        response = self.api_patch(self.url_name, data, pk=self.cita.cita_id)

        # Dependiendo de la lógica de negocio, podría ser 400 o 403
        self.assertIn(
            response.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN],
        )

    def test_actualizar_campos_requeridos_vacios_put(self):
        """Test que verifica validación de campos requeridos en PUT."""
        data = {
            "observaciones": "Solo observaciones"
            # Faltan cliente y fecha_hora_cita requeridos para PUT
        }

        response = self.api_put(self.url_name, data, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cliente", response.data)
        self.assertIn("fecha_hora_cita", response.data)

    def test_actualizar_timestamp_fecha_actualizacion(self):
        """Test que verifica que se actualiza el timestamp de fecha_actualizacion."""
        fecha_actualizacion_original = self.cita.fecha_actualizacion

        # Esperar un momento para asegurar diferencia en timestamp
        import time

        time.sleep(0.1)

        data = {"observaciones": "Actualización para verificar timestamp"}

        response = self.api_patch(self.url_name, data, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que fecha_actualizacion cambió
        cita_actualizada = Cita.objects.get(cita_id=self.cita.cita_id)
        self.assertGreater(
            cita_actualizada.fecha_actualizacion, fecha_actualizacion_original
        )
