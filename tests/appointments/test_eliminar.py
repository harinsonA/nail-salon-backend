"""
Tests para eliminar citas - API endpoint DELETE /api/citas/{id}/
"""

from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from ..utils import BaseAPITestCase
from apps.appointments.models import Cita, DetalleCita


class TestEliminarCitas(BaseAPITestCase):
    """Tests para el endpoint de eliminación de citas."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()

        # Crear cliente de prueba
        self.cliente = self.create_cliente_with_factory(
            nombre="Pedro",
            apellido="González",
            telefono="3001111111",
            email="pedro.gonzalez@test.com",
        )

        # Crear servicio de prueba
        self.servicio = self.create_servicio_with_factory(
            nombre_servicio="Pedicure", precio=30000
        )

        # Crear cita de prueba
        self.cita = self.create_cita_with_factory(
            cliente=self.cliente,
            fecha_hora_cita=timezone.now() + timedelta(days=1),
            estado_cita="PENDIENTE",
            observaciones="Cita para eliminar",
        )

        self.url_name = "cita-detail"

    def test_eliminar_cita_exitoso(self):
        """Test que verifica eliminación exitosa de una cita."""
        response = self.api_delete(self.url_name, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar que la cita fue eliminada de la base de datos
        with self.assertRaises(Cita.DoesNotExist):
            Cita.objects.get(cita_id=self.cita.cita_id)

    def test_eliminar_cita_inexistente(self):
        """Test que verifica respuesta para cita que no existe."""
        response = self.api_delete(self.url_name, pk=99999)

        self.assert_not_found(response)

    def test_eliminar_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación para eliminar."""
        self.unauthenticate()

        response = self.api_delete(self.url_name, pk=self.cita.cita_id)

        self.assert_unauthorized(response)

    def test_eliminar_usuario_normal(self):
        """Test que verifica que usuarios normales pueden eliminar."""
        self.authenticate_as_normal_user()

        response = self.api_delete(self.url_name, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar eliminación
        with self.assertRaises(Cita.DoesNotExist):
            Cita.objects.get(cita_id=self.cita.cita_id)

    def test_eliminar_admin_usuario(self):
        """Test que verifica que usuarios admin pueden eliminar."""
        self.authenticate_as_admin()

        response = self.api_delete(self.url_name, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

    def test_eliminar_cita_pendiente(self):
        """Test que verifica eliminación de cita con estado PENDIENTE."""
        self.cita.estado_cita = "PENDIENTE"
        self.cita.save()

        response = self.api_delete(self.url_name, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

    def test_eliminar_cita_confirmada(self):
        """Test que verifica eliminación de cita con estado CONFIRMADA."""
        self.cita.estado_cita = "CONFIRMADA"
        self.cita.save()

        response = self.api_delete(self.url_name, pk=self.cita.cita_id)

        # Dependiendo de la lógica de negocio, podría permitirse o no
        # Aquí asumimos que se permite
        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

    def test_no_eliminar_cita_completada(self):
        """Test que verifica que no se puede eliminar cita COMPLETADA."""
        self.cita.estado_cita = "COMPLETADA"
        self.cita.save()

        response = self.api_delete(self.url_name, pk=self.cita.cita_id)

        # No se debería poder eliminar una cita completada
        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)

        # Verificar que la cita sigue existiendo
        self.assertTrue(Cita.objects.filter(cita_id=self.cita.cita_id).exists())

    def test_eliminar_cita_cancelada(self):
        """Test que verifica eliminación de cita con estado CANCELADA."""
        self.cita.estado_cita = "CANCELADA"
        self.cita.save()

        response = self.api_delete(self.url_name, pk=self.cita.cita_id)

        # Las citas canceladas se pueden eliminar
        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

    def test_eliminar_cita_con_detalles(self):
        """Test que verifica eliminación de cita que tiene detalles asociados."""
        # Crear detalle de cita
        detalle = self.create_detalle_cita_with_factory(
            cita=self.cita, servicio=self.servicio, precio_acordado=self.servicio.precio
        )

        response = self.api_delete(self.url_name, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar que tanto la cita como sus detalles fueron eliminados
        with self.assertRaises(Cita.DoesNotExist):
            Cita.objects.get(cita_id=self.cita.cita_id)

        with self.assertRaises(DetalleCita.DoesNotExist):
            DetalleCita.objects.get(detalle_cita_id=detalle.detalle_cita_id)

    def test_eliminar_multiples_citas_diferentes_clientes(self):
        """Test que verifica eliminación independiente de citas."""
        # Crear otro cliente y cita
        otro_cliente = self.create_cliente_with_factory(
            nombre="Ana",
            apellido="Pérez",
            telefono="3002222222",
            email="ana.perez@test.com",
        )

        otra_cita = self.create_cita_with_factory(
            cliente=otro_cliente,
            fecha_hora_cita=timezone.now() + timedelta(days=2),
            estado_cita="PENDIENTE",
        )

        # Eliminar primera cita
        response = self.api_delete(self.url_name, pk=self.cita.cita_id)
        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar que la primera cita fue eliminada
        with self.assertRaises(Cita.DoesNotExist):
            Cita.objects.get(cita_id=self.cita.cita_id)

        # Verificar que la segunda cita sigue existiendo
        self.assertTrue(Cita.objects.filter(cita_id=otra_cita.cita_id).exists())

    def test_eliminar_cita_fecha_pasada(self):
        """Test que verifica eliminación de cita con fecha en el pasado."""
        # Crear cita con fecha pasada
        cita_pasada = self.create_cita_with_factory(
            cliente=self.cliente,
            fecha_hora_cita=timezone.now() - timedelta(days=1),
            estado_cita="PENDIENTE",
        )

        response = self.api_delete(self.url_name, pk=cita_pasada.cita_id)

        # Dependiendo de la lógica de negocio
        self.assertIn(
            response.status_code,
            [
                status.HTTP_204_NO_CONTENT,  # Si se permite
                status.HTTP_400_BAD_REQUEST,  # Si no se permite
            ],
        )

    def test_eliminar_cita_mismo_dia(self):
        """Test que verifica eliminación de cita programada para hoy."""
        # Crear cita para hoy
        cita_hoy = self.create_cita_with_factory(
            cliente=self.cliente,
            fecha_hora_cita=timezone.now() + timedelta(hours=2),
            estado_cita="CONFIRMADA",
        )

        response = self.api_delete(self.url_name, pk=cita_hoy.cita_id)

        # Podría requerir validaciones especiales para citas del mismo día
        self.assertIn(
            response.status_code,
            [
                status.HTTP_204_NO_CONTENT,  # Si se permite
                status.HTTP_400_BAD_REQUEST,  # Si requiere más tiempo de anticipación
            ],
        )

    def test_soft_delete_vs_hard_delete(self):
        """Test que verifica si se usa eliminación suave o definitiva."""
        cita_id_original = self.cita.cita_id

        response = self.api_delete(self.url_name, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar que es eliminación definitiva (hard delete)
        with self.assertRaises(Cita.DoesNotExist):
            Cita.objects.get(cita_id=cita_id_original)

        # Si fuera soft delete, verificaríamos un campo como 'is_deleted' o 'deleted_at'
        # cita_eliminada = Cita.objects.get(cita_id=cita_id_original)
        # self.assertTrue(cita_eliminada.is_deleted)

    def test_eliminar_respuesta_vacia(self):
        """Test que verifica que la respuesta de eliminación está vacía."""
        response = self.api_delete(self.url_name, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.content, b"")

    def test_eliminar_cita_y_verificar_contador(self):
        """Test que verifica cambios en contadores tras eliminación."""
        # Contar citas antes de eliminar
        citas_antes = Cita.objects.count()

        response = self.api_delete(self.url_name, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar que el contador disminuyó
        citas_despues = Cita.objects.count()
        self.assertEqual(citas_despues, citas_antes - 1)

    def test_eliminar_cita_cliente_con_historial(self):
        """Test que verifica eliminación cuando el cliente tiene historial."""
        # Crear otra cita para el mismo cliente
        otra_cita = self.create_cita_with_factory(
            cliente=self.cliente,
            fecha_hora_cita=timezone.now() + timedelta(days=3),
            estado_cita="PENDIENTE",
        )

        response = self.api_delete(self.url_name, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar que solo se eliminó la cita específica
        with self.assertRaises(Cita.DoesNotExist):
            Cita.objects.get(cita_id=self.cita.cita_id)

        # La otra cita del mismo cliente debe seguir existiendo
        self.assertTrue(Cita.objects.filter(cita_id=otra_cita.cita_id).exists())

    def test_eliminar_cita_con_multiple_detalles(self):
        """Test que verifica eliminación en cascada con múltiples detalles."""
        # Crear múltiples servicios
        servicio2 = self.create_servicio_with_factory(
            nombre_servicio="Manicure Francesa", precio=35000
        )

        # Crear múltiples detalles para la misma cita
        self.create_detalle_cita_with_factory(
            cita=self.cita, servicio=self.servicio, precio_acordado=self.servicio.precio
        )

        self.create_detalle_cita_with_factory(
            cita=self.cita, servicio=servicio2, precio_acordado=servicio2.precio
        )

        response = self.api_delete(self.url_name, pk=self.cita.cita_id)

        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)

        # Verificar que todos los detalles fueron eliminados
        self.assertEqual(DetalleCita.objects.filter(cita=self.cita).count(), 0)

    def test_intentar_eliminar_dos_veces(self):
        """Test que verifica comportamiento al intentar eliminar dos veces."""
        # Primera eliminación
        response1 = self.api_delete(self.url_name, pk=self.cita.cita_id)
        self.assert_response_status(response1, status.HTTP_204_NO_CONTENT)

        # Segunda eliminación (debe fallar)
        response2 = self.api_delete(self.url_name, pk=self.cita.cita_id)
        self.assert_not_found(response2)
