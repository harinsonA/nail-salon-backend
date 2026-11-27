from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, SimpleTestCase

from apps.profiles.middleware import CambioDeClaveObligatorioMiddleware, PermisosPorRolMiddleware
from apps.profiles.models import Perfil
from apps.tenancy.business_status import BusinessStatus
from apps.tenancy.middleware import EstadoDelNegocioMiddleware
from apps.tenancy.models import Negocio
from tests.base import NegocioTestCase

User = get_user_model()
Estado = Negocio.Estado


class BusinessStatusTests(SimpleTestCase):
    def test_preparing_paused_and_cancelled_are_unavailable(self):
        expected = {Estado.PREPARANDO: 503, Estado.PAUSADO: 410, Estado.CANCELADO: 410}
        for estado, status_code in expected.items():
            with self.subTest(estado=estado):
                self.assertEqual(BusinessStatus(Negocio(estado=estado)).unavailable.status_code, status_code)

    def test_active_and_overdue_are_available(self):
        for estado in (Estado.ACTIVO, Estado.MOROSO):
            with self.subTest(estado=estado):
                self.assertIsNone(BusinessStatus(Negocio(estado=estado)).unavailable)

    def test_does_not_apply_without_business_or_in_public_schema(self):
        request = RequestFactory().get("/")
        self.assertIsNone(BusinessStatus.for_request(request))
        request.tenant = Negocio(schema_name="public")
        self.assertIsNone(BusinessStatus.for_request(request))


class PausedSectionTests(NegocioTestCase):
    esquema = "status_paused"

    def make_user(self, rol):
        user = User.objects.create_user(username=rol, email=f"{rol}@correo.cl")
        Perfil.objects.filter(user=user).update(rol=rol)
        return User.objects.get(pk=user.pk)

    def test_overdue_pauses_administration_only_for_managers(self):
        overdue = BusinessStatus(Negocio(estado=Estado.MOROSO))
        self.assertTrue(overdue.pauses_section("incomes", self.make_user(Perfil.Rol.ENCARGADO)))
        self.assertFalse(overdue.pauses_section("incomes", self.make_user(Perfil.Rol.COLABORADOR)))
        self.assertFalse(overdue.pauses_section("calendar", self.make_user(Perfil.Rol.PROPIETARIO)))

    def test_overdue_pauses_clients_for_managers_but_not_whatsapp(self):
        overdue = BusinessStatus(Negocio(estado=Estado.MOROSO))
        owner = self.make_user(Perfil.Rol.PROPIETARIO)
        for url_name in ("clients", "client_create_modal", "api_clients", "api_client"):
            with self.subTest(url_name=url_name):
                self.assertTrue(overdue.pauses_section(url_name, owner))
        self.assertFalse(overdue.pauses_section("client_whatsapp_modal", owner))
        self.assertFalse(overdue.pauses_section("clients", self.make_user(Perfil.Rol.COLABORADOR)))

    def test_overdue_stops_new_appointments_for_everyone(self):
        overdue = BusinessStatus(Negocio(estado=Estado.MOROSO))
        self.assertFalse(overdue.allows_new_appointments)
        collaborator = self.make_user(Perfil.Rol.COLABORADOR)
        for url_name in ("create_appointment_from_calendar", "api_appointments"):
            with self.subTest(url_name=url_name):
                self.assertTrue(overdue.pauses_section(url_name, collaborator))
        self.assertFalse(overdue.pauses_section("api_appointment", collaborator))

    def test_active_pauses_nothing(self):
        active = BusinessStatus(Negocio(estado=Estado.ACTIVO))
        self.assertFalse(active.pauses_section("incomes", self.make_user(Perfil.Rol.PROPIETARIO)))


class WebMiddlewaresSkipApiTests(NegocioTestCase):
    esquema = "status_api"

    def request_for(self, path):
        request = RequestFactory().get(path)
        request.tenant = self.negocio
        request.user = AnonymousUser()
        return request

    def test_business_status_does_not_answer_api_requests(self):
        self.negocio.estado = Estado.PAUSADO
        middleware = EstadoDelNegocioMiddleware(lambda request: None)
        self.assertIsNone(middleware.process_view(self.request_for("/api/v1/startup/"), None, (), {}))
        self.assertEqual(middleware.process_view(self.request_for("/"), None, (), {}).status_code, 410)

    def test_permissions_and_temporary_password_do_not_answer_api_requests(self):
        user = User.objects.create_user(username="colaboradora", email="colaboradora@correo.cl")
        Perfil.objects.filter(user=user).update(rol=Perfil.Rol.COLABORADOR, debe_cambiar_clave=True)
        request = self.request_for("/api/v1/services/")
        request.user = User.objects.get(pk=user.pk)
        for middleware in (CambioDeClaveObligatorioMiddleware, PermisosPorRolMiddleware):
            with self.subTest(middleware=middleware.__name__):
                self.assertIsNone(middleware(lambda request: None).process_view(request, None, (), {}))
