from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django_tenants.utils import get_public_schema_name

from apps.common.views.error_views import bad_request, server_error
from apps.profiles.models import Perfil
from apps.tenancy.models import Dominio, Negocio
from tests.base import NegocioTestCase

User = get_user_model()


class PaginasDeErrorDelNegocioTests(NegocioTestCase):
    esquema = "errores"
    dominio = "errores.localhost"

    def navegador_de(self, rol):
        usuario = User.objects.create_user(username=rol, email=f"{rol}@correo.cl")
        Perfil.objects.filter(user=usuario).update(rol=rol, debe_cambiar_clave=False)
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(usuario)
        return navegador

    def peticion(self):
        request = RequestFactory().get("/", HTTP_HOST=self.dominio)
        request.user = AnonymousUser()
        return request

    def test_el_404_lleva_al_dashboard_a_quien_administra(self):
        respuesta = self.navegador_de(Perfil.Rol.PROPIETARIO).get("/no-existe/")
        self.assertContains(respuesta, "Esta página no existe", status_code=404)
        self.assertContains(respuesta, f'href="{reverse("dashboard")}"', status_code=404)
        self.assertContains(respuesta, f'data-redirect-url="{reverse("dashboard")}"', status_code=404)
        self.assertContains(respuesta, "Hi Agenda · Negocio errores", status_code=404)

    def test_el_404_lleva_al_calendario_al_colaborador(self):
        respuesta = self.navegador_de(Perfil.Rol.COLABORADOR).get("/no-existe/")
        self.assertContains(respuesta, "Ir al calendario", status_code=404)
        self.assertNotContains(respuesta, reverse("dashboard"), status_code=404)

    def test_el_403_del_colaborador_no_lo_manda_a_otra_seccion_reservada(self):
        respuesta = self.navegador_de(Perfil.Rol.COLABORADOR).get(reverse("dashboard"))
        self.assertContains(respuesta, "No tienes acceso a esta sección", status_code=403)
        self.assertContains(respuesta, f'data-redirect-url="{reverse("calendar")}"', status_code=403)

    def test_el_500_ofrece_reintentar_sin_redireccion(self):
        respuesta = server_error(self.peticion())
        self.assertContains(respuesta, "Algo falló de nuestro lado", status_code=500)
        self.assertContains(respuesta, "Reintentar", status_code=500)
        self.assertNotContains(respuesta, "data-redirect-url", status_code=500)

    def test_el_400_redirige_al_inicio(self):
        respuesta = bad_request(self.peticion())
        self.assertContains(respuesta, "No pudimos procesar la solicitud", status_code=400)
        self.assertContains(respuesta, "data-redirect-url", status_code=400)


class PaginasDeErrorDelPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        publico = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain="admin.localhost", tenant=publico, is_primary=True)
        cls.staff = User.objects.create_user(username="staff", password="x", is_staff=True)

    def setUp(self):
        connection.set_schema_to_public()
        self.panel = Client(HTTP_HOST="admin.localhost")
        self.panel.force_login(self.staff)

    def test_una_accion_reservada_muestra_el_403_del_panel(self):
        alta = reverse("admin:tenancy_negocio_add", urlconf=settings.PUBLIC_SCHEMA_URLCONF)
        respuesta = self.panel.get(alta)
        self.assertContains(respuesta, "Tu usuario del panel no tiene permiso para esta acción.", status_code=403)
        self.assertContains(respuesta, 'href="/admin/"', status_code=403)

    def test_una_direccion_inexistente_muestra_el_404_del_panel(self):
        respuesta = self.panel.get("/admin/daw/")
        self.assertContains(respuesta, "Esta página no existe", status_code=404)
        self.assertContains(respuesta, "Ir al inicio del panel", status_code=404)
        self.assertContains(respuesta, "Hi Agenda · Panel de administración", status_code=404)


class PaginasDeErrorDeLaRaizTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        publico = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain="localhost", tenant=publico, is_primary=True)

    def test_una_direccion_inexistente_vuelve_a_la_pagina_publica(self):
        respuesta = Client(HTTP_HOST="localhost").get("/da")
        self.assertContains(respuesta, "Esta página no existe", status_code=404)
        self.assertContains(respuesta, 'data-redirect-url="/"', status_code=404)
