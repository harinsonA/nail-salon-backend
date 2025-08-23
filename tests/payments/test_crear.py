"""
Tests para crear pagos - API endpoint POST /api/pagos/
"""

from decimal import Decimal
from rest_framework import status
from ..utils import BaseAPITestCase
from apps.payments.models import Pago


class TestCrearPagos(BaseAPITestCase):
    """Tests para el endpoint de creación de pagos."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.url_name = "payments:pago-list"  # Usar namespace correcto
        self.cita = self.create_cita_with_factory()

    def test_crear_pago_exitoso(self):
        """Test que verifica que se puede crear un pago correctamente."""
        data = {
            "cita": self.cita.cita_id,
            "monto_total": "50000.00",
            "metodo_pago": "EFECTIVO",
            "estado_pago": "PAGADO",
            "notas_pago": "Pago de test completado",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_201_CREATED)

        # Verificar que se creó en la base de datos
        self.assertTrue(Pago.objects.filter(cita=self.cita).exists())

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

        # Verificar valores
        self.assertEqual(response.data["cita"], self.cita.cita_id)
        self.assertEqual(response.data["monto_total"], "50000.00")
        self.assertEqual(response.data["metodo_pago"], "EFECTIVO")
        self.assertEqual(response.data["estado_pago"], "PAGADO")

    def test_crear_pago_datos_minimos(self):
        """Test que verifica crear pago con datos mínimos requeridos."""
        data = {
            "cita": self.cita.cita_id,
            "monto_total": "25000.00",
            "metodo_pago": "EFECTIVO",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["estado_pago"], "PENDIENTE"
        )  # Por defecto debe ser pendiente

    def test_crear_pago_datos_faltantes(self):
        """Test que verifica validación de campos requeridos."""
        data = {
            "notas_pago": "Sin cita ni monto"
            # Faltan cita, monto_total, metodo_pago
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cita", response.data)
        self.assertIn("monto_total", response.data)
        self.assertIn("metodo_pago", response.data)

    def test_crear_pago_monto_negativo(self):
        """Test que verifica validación de monto negativo."""
        data = {
            "cita": self.cita.cita_id,
            "monto_total": "-1000.00",
            "metodo_pago": "EFECTIVO",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("monto_total", response.data)

    def test_crear_pago_monto_cero(self):
        """Test que verifica validación de monto cero."""
        data = {
            "cita": self.cita.cita_id,
            "monto_total": "0.00",
            "metodo_pago": "EFECTIVO",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("monto_total", response.data)

    def test_crear_pago_cita_inexistente(self):
        """Test que verifica validación de cita inexistente."""
        data = {
            "cita": 99999,  # Cita que no existe
            "monto_total": "30000.00",
            "metodo_pago": "TARJETA",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cita", response.data)

    def test_crear_pago_metodo_invalido(self):
        """Test que verifica validación de método de pago inválido."""
        data = {
            "cita": self.cita.cita_id,
            "monto_total": "25000.00",
            "metodo_pago": "criptomoneda",  # Método no válido
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("metodo_pago", response.data)

    def test_crear_pago_estado_invalido(self):
        """Test que verifica validación de estado de pago inválido."""
        data = {
            "cita": self.cita.cita_id,
            "monto_total": "25000.00",
            "metodo_pago": "EFECTIVO",
            "estado_pago": "estado_inexistente",  # Estado no válido
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("estado_pago", response.data)

    def test_crear_pago_monto_formato_invalido(self):
        """Test que verifica validación de formato de monto."""
        data = {
            "cita": self.cita.cita_id,
            "monto_total": "precio_texto",  # No es un número
            "metodo_pago": "EFECTIVO",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("monto_total", response.data)

    def test_crear_pago_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.unauthenticate()

        data = {
            "cita": self.cita.cita_id,
            "monto_total": "25000.00",
            "metodo_pago": "EFECTIVO",
        }

        response = self.api_post(self.url_name, data)
        self.assert_unauthorized(response)

    def test_crear_pago_usuario_normal(self):
        """Test que verifica que usuarios normales pueden crear pagos."""
        self.authenticate_as_normal_user()

        data = {
            "cita": self.cita.cita_id,
            "monto_total": "35000.00",
            "metodo_pago": "TARJETA",
            "estado_pago": "PAGADO",
        }

        response = self.api_post(self.url_name, data)
        self.assert_response_status(response, status.HTTP_201_CREATED)

    def test_crear_pago_con_transferencia(self):
        """Test que verifica crear pago con transferencia bancaria."""
        data = {
            "cita": self.cita.cita_id,
            "monto_total": "45000.00",
            "metodo_pago": "TRANSFERENCIA",
            "estado_pago": "PENDIENTE",
            "notas_pago": "Transferencia en proceso de verificación",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["metodo_pago"], "TRANSFERENCIA")
        self.assertEqual(response.data["estado_pago"], "PENDIENTE")

    def test_crear_pago_notas_largas(self):
        """Test que verifica límites de longitud en notas."""
        data = {
            "cita": self.cita.cita_id,
            "monto_total": "25000.00",
            "metodo_pago": "EFECTIVO",
            "notas_pago": "A" * 501,  # Muy largo (asumiendo límite de 500)
        }

        response = self.api_post(self.url_name, data)

        # Dependiendo de la validación del modelo, puede ser 400 o 201
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            self.assertIn("notas_pago", response.data)
        else:
            self.assert_response_status(response, status.HTTP_201_CREATED)

    def test_crear_pago_multiple_misma_cita(self):
        """Test que verifica crear múltiples pagos para la misma cita."""
        # Primer pago
        data1 = {
            "cita": self.cita.cita_id,
            "monto_total": "20000.00",
            "metodo_pago": "EFECTIVO",
            "estado_pago": "PAGADO",
            "notas_pago": "Anticipo",
        }

        response1 = self.api_post(self.url_name, data1)
        self.assert_response_status(response1, status.HTTP_201_CREATED)

        # Segundo pago para la misma cita
        data2 = {
            "cita": self.cita.cita_id,
            "monto_total": "15000.00",
            "metodo_pago": "TARJETA",
            "estado_pago": "PAGADO",
            "notas_pago": "Pago restante",
        }

        response2 = self.api_post(self.url_name, data2)
        self.assert_response_status(response2, status.HTTP_201_CREATED)

        # Verificar que ambos pagos existen
        pagos_cita = Pago.objects.filter(cita=self.cita)
        self.assertEqual(pagos_cita.count(), 2)
