"""
Tests para crear clientes - API endpoint POST /api/clientes/
"""

from django.urls import reverse
from rest_framework import status
from ..utils import BaseAPITestCase
from apps.clients.models import Cliente


class TestCrearClientes(BaseAPITestCase):
    """Tests para el endpoint de creación de clientes."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.url_name = "cliente-list"  # POST al mismo endpoint de list

    def test_crear_cliente_exitoso(self):
        """Test que verifica que se puede crear un cliente correctamente."""
        data = {
            "nombre": "Juan",
            "apellido": "Pérez",
            "telefono": "3001234567",
            "email": "juan.perez@test.com",
            "activo": True,
            "notas": "Cliente nuevo de test",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_201_CREATED)

        # Verificar que se creó en la base de datos
        self.assertTrue(Cliente.objects.filter(email="juan.perez@test.com").exists())

        # Verificar estructura de la respuesta
        expected_fields = [
            "cliente_id",  # El serializer devuelve cliente_id, no id
            "nombre",
            "apellido",
            "telefono",
            "email",
            "activo",
            "fecha_registro",
            "notas",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        self.assert_response_contains_fields(response.data, expected_fields)

        # Verificar valores
        self.assertEqual(response.data["nombre"], "Juan")
        self.assertEqual(response.data["apellido"], "Pérez")
        self.assertEqual(response.data["email"], "juan.perez@test.com")

    def test_crear_cliente_datos_minimos(self):
        """Test que verifica crear cliente con datos mínimos requeridos."""
        data = {
            "nombre": "Ana",
            "apellido": "García",
            "telefono": "3009876543",
            "email": "ana.garcia@test.com",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["activo"], True)  # Por defecto debe ser True

    def test_crear_cliente_email_duplicado(self):
        """Test que verifica que no se puede crear cliente con email duplicado."""
        # Crear cliente inicial
        self.create_cliente_with_factory(email="test@example.com")

        data = {
            "nombre": "Pedro",
            "apellido": "Martínez",
            "telefono": "3005555555",
            "email": "test@example.com",  # Email duplicado
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_crear_cliente_telefono_duplicado(self):
        """Test que verifica que no se puede crear cliente con teléfono duplicado."""
        # Crear cliente inicial
        self.create_cliente_with_factory(telefono="3001111111")

        data = {
            "nombre": "Luis",
            "apellido": "González",
            "telefono": "3001111111",  # Teléfono duplicado
            "email": "luis.gonzalez@test.com",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("telefono", response.data)

    def test_crear_cliente_datos_faltantes(self):
        """Test que verifica validación de campos requeridos."""
        data = {
            "nombre": "Carlos"
            # Faltan apellido, telefono, email
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("apellido", response.data)
        self.assertIn("telefono", response.data)
        self.assertIn("email", response.data)

    def test_crear_cliente_email_invalido(self):
        """Test que verifica validación de formato de email."""
        data = {
            "nombre": "María",
            "apellido": "López",
            "telefono": "3002222222",
            "email": "email-invalido",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_crear_cliente_telefono_invalido(self):
        """Test que verifica validación de formato de teléfono."""
        data = {
            "nombre": "Roberto",
            "apellido": "Ruiz",
            "telefono": "123",  # Muy corto
            "email": "roberto.ruiz@test.com",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("telefono", response.data)

    def test_crear_cliente_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.unauthenticate()

        data = {
            "nombre": "Test",
            "apellido": "User",
            "telefono": "3000000000",
            "email": "test@example.com",
        }

        response = self.api_post(self.url_name, data)
        self.assert_unauthorized(response)

    def test_crear_cliente_usuario_normal(self):
        """Test que verifica que usuarios normales pueden crear clientes."""
        self.authenticate_as_normal_user()

        data = {
            "nombre": "Usuario",
            "apellido": "Normal",
            "telefono": "3007777777",
            "email": "usuario.normal@test.com",
        }

        response = self.api_post(self.url_name, data)
        self.assert_response_status(response, status.HTTP_201_CREATED)

    def test_crear_cliente_nombre_largo(self):
        """Test que verifica límites de longitud en campos."""
        data = {
            "nombre": "A" * 151,  # Muy largo
            "apellido": "Pérez",
            "telefono": "3008888888",
            "email": "test.largo@test.com",
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nombre", response.data)

    def test_crear_cliente_notas_opcionales(self):
        """Test que verifica que las notas son opcionales."""
        data = {
            "nombre": "Sin",
            "apellido": "Notas",
            "telefono": "3009999999",
            "email": "sin.notas@test.com",
            "notas": "",  # Notas vacías
        }

        response = self.api_post(self.url_name, data)

        self.assert_response_status(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["notas"], "")
