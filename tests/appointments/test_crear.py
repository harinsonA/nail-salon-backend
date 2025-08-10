"""
Tests para crear citas - API endpoint POST /api/citas/
"""

from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from ..utils import BaseAPITestCase
from apps.appointments.models import Cita


class TestCrearCitas(BaseAPITestCase):
    """Tests para el endpoint de creación de citas."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.url_name = "cita-list"  # POST al mismo endpoint de list

        # Crear cliente de prueba
        self.cliente = self.create_cliente_with_factory(
            nombre="Ana",
            apellido="García",
            telefono="3001234567",
            email="ana.garcia@test.com",
        )

        # Crear servicio de prueba
        self.servicio = self.create_servicio_with_factory(
            nombre_servicio="Manicure Básico",
            precio=25000,
            duracion_estimada=timedelta(minutes=60),
        )

        # Fecha futura para las citas
        self.fecha_futura = timezone.now() + timedelta(days=1)

    def test_crear_cita_exitosa(self):
        """Test que verifica que se puede crear una cita correctamente."""
        data = {
            "cliente": self.cliente.cliente_id,
            "fecha_hora_cita": self.fecha_futura.isoformat(),
            "estado_cita": "CONFIRMADA",
            "observaciones": "Cita de prueba",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_201_CREATED)

        # Verificar que se creó en la base de datos
        self.assertTrue(Cita.objects.filter(cliente=self.cliente).exists())

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
        self.assertEqual(response.data["cliente"], self.cliente.cliente_id)
        self.assertEqual(response.data["estado_cita"], "CONFIRMADA")

    def test_crear_cita_datos_minimos(self):
        """Test que verifica crear cita con datos mínimos requeridos."""
        data = {
            "cliente": self.cliente.cliente_id,
            "fecha_hora_cita": self.fecha_futura.isoformat(),
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["estado_cita"], "PENDIENTE")  # Por defecto

    def test_crear_cita_cliente_inexistente(self):
        """Test que verifica que no se puede crear cita con cliente inexistente."""
        data = {
            "cliente": 99999,  # Cliente que no existe
            "fecha_hora_cita": self.fecha_futura.isoformat(),
            "estado_cita": "CONFIRMADA",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cliente", response.data)

    def test_crear_cita_datos_faltantes(self):
        """Test que verifica validación de campos requeridos."""
        data = {
            "observaciones": "Solo observaciones"
            # Faltan cliente y fecha_hora_cita
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cliente", response.data)
        self.assertIn("fecha_hora_cita", response.data)

    def test_crear_cita_fecha_pasada(self):
        """Test que verifica validación de fecha en el pasado."""
        fecha_pasada = timezone.now() - timedelta(days=1)

        data = {
            "cliente": self.cliente.cliente_id,
            "fecha_hora_cita": fecha_pasada.isoformat(),
            "estado_cita": "CONFIRMADA",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fecha_hora_cita", response.data)

    def test_crear_cita_estado_invalido(self):
        """Test que verifica validación de estado de cita."""
        data = {
            "cliente": self.cliente.cliente_id,
            "fecha_hora_cita": self.fecha_futura.isoformat(),
            "estado_cita": "ESTADO_INEXISTENTE",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("estado_cita", response.data)

    def test_crear_cita_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.unauthenticate()

        data = {
            "cliente": self.cliente.cliente_id,
            "fecha_hora_cita": self.fecha_futura.isoformat(),
        }

        response = self.api_post(self.url_name, data)
        self.assert_unauthorized(response)

    def test_crear_cita_usuario_normal(self):
        """Test que verifica que usuarios normales pueden crear citas."""
        self.authenticate_as_normal_user()

        data = {
            "cliente": self.cliente.cliente_id,
            "fecha_hora_cita": self.fecha_futura.isoformat(),
            "estado_cita": "CONFIRMADA",
            "observaciones": "Cita creada por usuario normal",
        }

        response = self.api_post(self.url_name, data)
        self.assert_response_status(response, status.HTTP_201_CREATED)

    def test_crear_cita_con_observaciones_largas(self):
        """Test que verifica manejo de observaciones extensas."""
        observaciones_largas = "A" * 1000  # Texto muy largo

        data = {
            "cliente": self.cliente.cliente_id,
            "fecha_hora_cita": self.fecha_futura.isoformat(),
            "observaciones": observaciones_largas,
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["observaciones"], observaciones_largas)

    def test_crear_cita_observaciones_opcionales(self):
        """Test que verifica que las observaciones son opcionales."""
        data = {
            "cliente": self.cliente.cliente_id,
            "fecha_hora_cita": self.fecha_futura.isoformat(),
            "observaciones": "",  # Observaciones vacías
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["observaciones"], "")

    def test_crear_cita_con_detalle_servicios(self):
        """Test que verifica creación de cita y posteriormente agregar servicios."""
        # Primero crear la cita
        data = {
            "cliente": self.cliente.cliente_id,
            "fecha_hora_cita": self.fecha_futura.isoformat(),
            "estado_cita": "CONFIRMADA",
            "observaciones": "Cita con servicios",
        }

        response = self.api_post(self.url_name, data)
        self.assert_response_status(response, status.HTTP_201_CREATED)

        cita_creada = Cita.objects.get(cita_id=response.data["cita_id"])

        # Luego crear el detalle de la cita por separado
        detalle = self.create_detalle_cita_with_factory(
            cita=cita_creada,
            servicio=self.servicio,
            precio_acordado=self.servicio.precio,
            cantidad_servicios=1,
            notas_detalle="Servicio principal",
        )

        # Verificar que se creó el detalle
        self.assertEqual(cita_creada.detalles.count(), 1)
        self.assertEqual(detalle.cita, cita_creada)
        self.assertEqual(detalle.servicio, self.servicio)

    def test_crear_cita_formato_fecha_correcto(self):
        """Test que verifica diferentes formatos de fecha aceptados."""
        # Formato ISO con timezone
        fecha_iso = self.fecha_futura.isoformat()

        data = {
            "cliente": self.cliente.cliente_id,
            "fecha_hora_cita": fecha_iso,
        }

        response = self.api_post(self.url_name, data)
        self.assert_response_status(response, status.HTTP_201_CREATED)

    def test_crear_multiple_citas_mismo_cliente(self):
        """Test que verifica que un cliente puede tener múltiples citas."""
        # Primera cita
        data1 = {
            "cliente": self.cliente.cliente_id,
            "fecha_hora_cita": self.fecha_futura.isoformat(),
            "observaciones": "Primera cita",
        }

        # Segunda cita (día siguiente)
        fecha_futura_2 = self.fecha_futura + timedelta(days=1)
        data2 = {
            "cliente": self.cliente.cliente_id,
            "fecha_hora_cita": fecha_futura_2.isoformat(),
            "observaciones": "Segunda cita",
        }

        response1 = self.api_post(self.url_name, data1)
        response2 = self.api_post(self.url_name, data2)

        self.assert_response_status(response1, status.HTTP_201_CREATED)
        self.assert_response_status(response2, status.HTTP_201_CREATED)

        # Verificar que el cliente tiene 2 citas
        citas_cliente = Cita.objects.filter(cliente=self.cliente)
        self.assertEqual(citas_cliente.count(), 2)
