"""
Utilidades base para tests de API del proyecto nail-salon-backend.

Este módulo contiene:
- Clase ba    def api_get(self, url_name, query_params=None, url_kwargs=None, pk=None, **request_kwargs):
        """
        Realizar request GET a la API.

        Args:
            url_name (str): Nombre de la URL
            query_params (dict): Parámetros de consulta (query string)
            url_kwargs (dict): Parámetros para la URL
            pk: Primary key para la URL
            **request_kwargs: Parámetros adicionales para el request

        Returns:
            Response: Respuesta de la API
        """
        kwargs = url_kwargs or {}
        if pk is not None:
            kwargs['pk'] = pk
        url = self.get_url(url_name, **kwargs)
        
        # Si hay query_params, añadirlos como data para GET
        if query_params:
            return self.client.get(url, data=query_params, **request_kwargs)
        else:
            return self.client.get(url, **request_kwargs)tests de API
- Utilidades para autenticación y manejo de requests
- Helpers comunes para validaciones
"""

from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

# Importar modelos
from apps.clients.models import Cliente
from apps.services.models import Servicio
from apps.appointments.models import Cita

# Importar factories organizadas
from tests.factories import (
    UserFactory,
    AdminUserFactory,
    ClienteFactory,
    ServicioFactory,
    CitaFactory,
    DetalleCitaFactory,
    PagoFactory,
)


class BaseAPITestCase(TestCase):
    """
    Clase base para todos los tests de API.

    Proporciona:
    - Configuración de base de datos para tests
    - Cliente API autenticado
    - Métodos helper para requests comunes
    - Factories para crear datos de test
    """

    # Permitir acceso a todas las bases de datos
    databases = "__all__"

    def setUp(self):
        """Configuración inicial para cada test."""
        # Cliente API para hacer requests
        self.client = APIClient()

        # Crear usuario administrador para tests
        self.admin_user = User.objects.create_user(
            username="admin_test",
            email="admin@test.com",
            password="testpassword123",
            is_staff=True,
            is_superuser=True,
        )

        # Crear usuario normal para tests
        self.normal_user = User.objects.create_user(
            username="user_test", email="user@test.com", password="testpassword123"
        )

        # Crear tokens de autenticación
        self.admin_token, _ = Token.objects.get_or_create(user=self.admin_user)
        self.normal_token, _ = Token.objects.get_or_create(user=self.normal_user)

        # Configurar autenticación por defecto (admin)
        self.authenticate_as_admin()

    def authenticate_as_admin(self):
        """Autenticar como usuario administrador."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.admin_token.key}")
        self.current_user = self.admin_user

    def authenticate_as_normal_user(self):
        """Autenticar como usuario normal."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.normal_token.key}")
        self.current_user = self.normal_user

    def unauthenticate(self):
        """Remover autenticación."""
        self.client.credentials()
        self.current_user = None

    # ===========================================
    # MÉTODOS HELPER PARA REQUESTS HTTP
    # ===========================================

    def get_url(self, url_name, **kwargs):
        """
        Obtener URL usando reverse.

        Args:
            url_name (str): Nombre de la URL (ej: 'clients:list')
            **kwargs: Parámetros para la URL

        Returns:
            str: URL completa
        """
        return reverse(url_name, kwargs=kwargs)

    def api_get(self, url_name, url_kwargs=None, pk=None, **request_kwargs):
        """
        Realizar request GET a la API.

        Args:
            url_name (str): Nombre de la URL
            url_kwargs (dict): Parámetros para la URL
            pk: Primary key para la URL
            **request_kwargs: Parámetros adicionales para el request

        Returns:
            Response: Respuesta de la API
        """
        kwargs = url_kwargs or {}
        if pk is not None:
            kwargs["pk"] = pk
        url = self.get_url(url_name, **kwargs)
        return self.client.get(url, **request_kwargs)

    def api_post(self, url_name, data=None, url_kwargs=None, pk=None, **request_kwargs):
        """
        Realizar request POST a la API.

        Args:
            url_name (str): Nombre de la URL
            data (dict): Datos a enviar
            url_kwargs (dict): Parámetros para la URL
            pk: Primary key para la URL
            **request_kwargs: Parámetros adicionales para el request

        Returns:
            Response: Respuesta de la API
        """
        kwargs = url_kwargs or {}
        if pk is not None:
            kwargs["pk"] = pk
        url = self.get_url(url_name, **kwargs)
        return self.client.post(url, data, format="json", **request_kwargs)

    def api_put(self, url_name, data=None, url_kwargs=None, pk=None, **request_kwargs):
        """
        Realizar request PUT a la API.

        Args:
            url_name (str): Nombre de la URL
            data (dict): Datos a enviar
            url_kwargs (dict): Parámetros para la URL
            pk: Primary key para la URL
            **request_kwargs: Parámetros adicionales para el request

        Returns:
            Response: Respuesta de la API
        """
        kwargs = url_kwargs or {}
        if pk is not None:
            kwargs["pk"] = pk
        url = self.get_url(url_name, **kwargs)
        return self.client.put(url, data, format="json", **request_kwargs)

    def api_patch(
        self, url_name, data=None, url_kwargs=None, pk=None, **request_kwargs
    ):
        """
        Realizar request PATCH a la API.

        Args:
            url_name (str): Nombre de la URL
            data (dict): Datos a enviar
            url_kwargs (dict): Parámetros para la URL
            pk: Primary key para la URL
            **request_kwargs: Parámetros adicionales para el request

        Returns:
            Response: Respuesta de la API
        """
        kwargs = url_kwargs or {}
        if pk is not None:
            kwargs["pk"] = pk
        url = self.get_url(url_name, **kwargs)
        return self.client.patch(url, data, format="json", **request_kwargs)

    def api_delete(self, url_name, url_kwargs=None, pk=None, **request_kwargs):
        """
        Realizar request DELETE a la API.

        Args:
            url_name (str): Nombre de la URL
            url_kwargs (dict): Parámetros para la URL
            pk: Primary key para la URL
            **request_kwargs: Parámetros adicionales para el request

        Returns:
            Response: Respuesta de la API
        """
        kwargs = url_kwargs or {}
        if pk is not None:
            kwargs["pk"] = pk
        url = self.get_url(url_name, **kwargs)
        return self.client.delete(url, **request_kwargs)

    # ===========================================
    # MÉTODOS DE VALIDACIÓN COMUNES
    # ===========================================

    def assert_response_status(self, response, expected_status):
        """
        Validar el status code de una respuesta.

        Args:
            response: Respuesta de la API
            expected_status: Status code esperado
        """
        self.assertEqual(
            response.status_code,
            expected_status,
            f"Expected status {expected_status}, got {response.status_code}. "
            f"Response data: {getattr(response, 'data', 'No data')}",
        )

    def assert_response_contains_fields(self, response_data, required_fields):
        """
        Validar que la respuesta contenga los campos requeridos.

        Args:
            response_data (dict): Datos de la respuesta
            required_fields (list): Lista de campos requeridos
        """
        for field in required_fields:
            self.assertIn(
                field, response_data, f"Field '{field}' not found in response data"
            )

    def assert_pagination_response(self, response_data):
        """
        Validar que la respuesta tenga el formato de paginación esperado.

        Args:
            response_data (dict): Datos de la respuesta
        """
        # Verificar campos básicos de paginación
        basic_fields = ["count", "results"]
        self.assert_response_contains_fields(response_data, basic_fields)
        self.assertIsInstance(response_data["results"], list)
        
        # Verificar si tiene formato estándar Django o formato personalizado
        if "links" in response_data:
            # Formato personalizado con links
            self.assertIn("links", response_data)
            self.assertIn("total_pages", response_data)
            self.assertIn("current_page", response_data)
        else:
            # Formato estándar Django
            pagination_fields = ["count", "next", "previous", "results"]
            self.assert_response_contains_fields(response_data, pagination_fields)

    def assert_unauthorized(self, response):
        """
        Validar que la respuesta sea 401 Unauthorized.

        Args:
            response: Respuesta de la API
        """
        self.assert_response_status(response, status.HTTP_401_UNAUTHORIZED)

    def assert_forbidden(self, response):
        """
        Validar que la respuesta sea 403 Forbidden.

        Args:
            response: Respuesta de la API
        """
        self.assert_response_status(response, status.HTTP_403_FORBIDDEN)

    def assert_not_found(self, response):
        """
        Validar que la respuesta sea 404 Not Found.

        Args:
            response: Respuesta de la API
        """
        self.assert_response_status(response, status.HTTP_404_NOT_FOUND)

    def assert_bad_request(self, response):
        """
        Validar que la respuesta sea 400 Bad Request.

        Args:
            response: Respuesta de la API
        """
        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)

    # ===========================================
    # FACTORIES PARA CREAR DATOS DE TEST
    # ===========================================

    def create_cliente_data(self, **kwargs):
        """
        Crear datos válidos para un cliente.

        Args:
            **kwargs: Campos a sobrescribir

        Returns:
            dict: Datos del cliente
        """
        base_data = {
            "nombre": "Juan",
            "apellido": "Pérez",
            "telefono": "3001234567",
            "email": f"juan.perez.{timezone.now().timestamp()}@test.com",
            "activo": True,
            "notas": "Cliente de test",
        }
        base_data.update(kwargs)
        return base_data

    def create_cliente(self, **kwargs):
        """
        Crear un cliente en la base de datos.

        Args:
            **kwargs: Campos a sobrescribir

        Returns:
            Cliente: Instancia del cliente creado
        """
        data = self.create_cliente_data(**kwargs)
        return Cliente.objects.create(**data)

    def create_servicio_data(self, **kwargs):
        """
        Crear datos válidos para un servicio.

        Args:
            **kwargs: Campos a sobrescribir

        Returns:
            dict: Datos del servicio
        """
        base_data = {
            "nombre_servicio": "Manicure Test",
            "precio": Decimal("25000.00"),
            "descripcion": "Servicio de test",
            "duracion_estimada": timedelta(hours=1),
            "activo": True,
            "categoria": "Test",
        }
        base_data.update(kwargs)
        return base_data

    def create_servicio(self, **kwargs):
        """
        Crear un servicio en la base de datos.

        Args:
            **kwargs: Campos a sobrescribir

        Returns:
            Servicio: Instancia del servicio creado
        """
        data = self.create_servicio_data(**kwargs)
        return Servicio.objects.create(**data)

    def create_cita_data(self, cliente=None, **kwargs):
        """
        Crear datos válidos para una cita.

        Args:
            cliente: Instancia del cliente (se crea uno si no se proporciona)
            **kwargs: Campos a sobrescribir

        Returns:
            dict: Datos de la cita
        """
        if cliente is None:
            cliente = self.create_cliente()

        base_data = {
            "cliente": cliente,
            "fecha_hora_cita": timezone.now() + timedelta(days=1),
            "estado": "programada",
            "notas": "Cita de test",
        }
        base_data.update(kwargs)
        return base_data

    def create_cita(self, cliente=None, **kwargs):
        """
        Crear una cita en la base de datos.

        Args:
            cliente: Instancia del cliente (se crea uno si no se proporciona)
            **kwargs: Campos a sobrescribir

        Returns:
            Cita: Instancia de la cita creada
        """
        data = self.create_cita_data(cliente=cliente, **kwargs)
        return Cita.objects.create(**data)

    # ===========================================
    # FACTORY BOY METHODS (Recomendados)
    # ===========================================

    def create_user_with_factory(self, **kwargs):
        """Crear usuario usando UserFactory."""
        return UserFactory(**kwargs)

    def create_admin_user_with_factory(self, **kwargs):
        """Crear usuario admin usando AdminUserFactory."""
        return AdminUserFactory(**kwargs)

    def create_cliente_with_factory(self, **kwargs):
        """Crear cliente usando ClienteFactory."""
        return ClienteFactory(**kwargs)

    def create_servicio_with_factory(self, **kwargs):
        """Crear servicio usando ServicioFactory."""
        return ServicioFactory(**kwargs)

    def create_cita_with_factory(self, **kwargs):
        """Crear cita usando CitaFactory."""
        # Si no se proporciona cliente, crear uno
        if "cliente" not in kwargs:
            kwargs["cliente"] = ClienteFactory()
        return CitaFactory(**kwargs)

    def create_detalle_cita_with_factory(self, **kwargs):
        """Crear detalle de cita usando DetalleCitaFactory."""
        return DetalleCitaFactory(**kwargs)

    def create_pago_with_factory(self, **kwargs):
        """Crear pago usando PagoFactory."""
        return PagoFactory(**kwargs)

    # ===========================================
    # HELPERS PARA DATOS EN FORMATO API
    # ===========================================

    def serialize_datetime(self, dt):
        """
        Serializar datetime para envío por API.

        Args:
            dt (datetime): Datetime a serializar

        Returns:
            str: Datetime en formato ISO
        """
        if dt:
            return dt.isoformat()
        return None

    def serialize_timedelta(self, td):
        """
        Serializar timedelta para envío por API.

        Args:
            td (timedelta): Timedelta a serializar

        Returns:
            str: Timedelta en formato de duración
        """
        if td:
            total_seconds = int(td.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return None

    # ===========================================
    # HELPERS PARA TESTS COMUNES
    # ===========================================

    def generic_test_list_endpoint(self, url_name, expected_fields=None):
        """
        Test genérico para endpoints de listado.

        Args:
            url_name (str): Nombre de la URL del endpoint
            expected_fields (list): Campos esperados en cada item
        """
        response = self.api_get(url_name)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assert_pagination_response(response.data)

        if expected_fields and response.data["results"]:
            first_item = response.data["results"][0]
            self.assert_response_contains_fields(first_item, expected_fields)

    def generic_test_create_endpoint(self, url_name, valid_data, expected_fields=None):
        """
        Test genérico para endpoints de creación.

        Args:
            url_name (str): Nombre de la URL del endpoint
            valid_data (dict): Datos válidos para crear
            expected_fields (list): Campos esperados en la respuesta
        """
        response = self.api_post(url_name, valid_data)
        self.assert_response_status(response, status.HTTP_201_CREATED)

        if expected_fields:
            self.assert_response_contains_fields(response.data, expected_fields)

        return response.data

    def generic_test_detail_endpoint(self, url_name, obj_id, expected_fields=None):
        """
        Test genérico para endpoints de detalle.

        Args:
            url_name (str): Nombre de la URL del endpoint
            obj_id: ID del objeto a consultar
            expected_fields (list): Campos esperados en la respuesta
        """
        response = self.api_get(url_name, {"pk": obj_id})
        self.assert_response_status(response, status.HTTP_200_OK)

        if expected_fields:
            self.assert_response_contains_fields(response.data, expected_fields)

        return response.data

    def generic_test_update_endpoint(
        self, url_name, obj_id, update_data, expected_fields=None
    ):
        """
        Test genérico para endpoints de actualización.

        Args:
            url_name (str): Nombre de la URL del endpoint
            obj_id: ID del objeto a actualizar
            update_data (dict): Datos para actualizar
            expected_fields (list): Campos esperados en la respuesta
        """
        response = self.api_put(url_name, update_data, {"pk": obj_id})
        self.assert_response_status(response, status.HTTP_200_OK)

        if expected_fields:
            self.assert_response_contains_fields(response.data, expected_fields)

        return response.data

    def generic_test_delete_endpoint(self, url_name, obj_id):
        """
        Test genérico para endpoints de eliminación.

        Args:
            url_name (str): Nombre de la URL del endpoint
            obj_id: ID del objeto a eliminar
        """
        response = self.api_delete(url_name, {"pk": obj_id})
        self.assert_response_status(response, status.HTTP_204_NO_CONTENT)


class APITestMixin:
    """
    Mixin que proporciona métodos adicionales para tests específicos.
    Se puede usar junto con BaseAPITestCase para funcionalidades específicas.
    """

    def assert_validation_error(self, response, field_name=None):
        """
        Validar que la respuesta sea un error de validación.

        Args:
            response: Respuesta de la API
            field_name (str): Campo específico que debe tener error
        """
        self.assert_response_status(response, status.HTTP_400_BAD_REQUEST)

        if field_name:
            self.assertIn(field_name, response.data)

    def assert_permission_denied(self, response):
        """Validar que la respuesta sea permission denied."""
        self.assert_response_status(response, status.HTTP_403_FORBIDDEN)

    def assert_not_found(self, response):
        """Validar que la respuesta sea not found."""
        self.assert_response_status(response, status.HTTP_404_NOT_FOUND)

    def assert_unauthorized(self, response):
        """Validar que la respuesta sea unauthorized."""
        self.assert_response_status(response, status.HTTP_401_UNAUTHORIZED)
