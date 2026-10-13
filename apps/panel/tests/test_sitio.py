from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django_tenants.routers import TenantSyncRouter
from django_tenants.utils import get_public_schema_name

from apps.panel.sitio import PanelAdminSite
from apps.tenancy.models import Dominio, Negocio

User = get_user_model()

PANEL = "admin.localhost"


class RegistroDelSitioTests(SimpleTestCase):
    def test_el_admin_usa_el_sitio_del_panel(self):
        self.assertIsInstance(admin.site, PanelAdminSite)

    def test_los_modelos_siguen_registrados(self):
        registrados = {modelo._meta.label for modelo in admin.site._registry}
        self.assertEqual(registrados, {"auth.Group", "auth.User", "tenancy.Negocio", "tenancy.Persona", "tenancy.Rubro"})

    def test_el_admin_migra_en_los_mismos_esquemas(self):
        router = TenantSyncRouter()
        self.assertTrue(router.app_in_list("admin", settings.SHARED_APPS))
        self.assertTrue(router.app_in_list("admin", settings.TENANT_APPS))


@override_settings(DOMINIO_BASE="localhost")
class SitioDelPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        publico = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=publico, is_primary=True)
        cls.admin = User.objects.create_superuser(username="admin", password="x")

    def pagina_de_django(self, host=PANEL):
        connection.set_schema_to_public()
        panel = Client(HTTP_HOST=host)
        panel.force_login(self.admin)
        return panel.get("/admin/auth/group/add/")

    def test_los_titulos_vienen_del_sitio(self):
        respuesta = self.pagina_de_django()
        self.assertContains(respuesta, "| Hi Agenda · Panel</title>")
        self.assertContains(respuesta, ">Hi Agenda · Panel</a>")

    def test_ver_el_sitio_lleva_a_la_pagina_publica(self):
        self.assertContains(self.pagina_de_django(), '<a href="http://localhost/">Ver el sitio</a>')

    def test_ver_el_sitio_respeta_el_puerto_del_navegador(self):
        self.assertContains(self.pagina_de_django(f"{PANEL}:8000"), '<a href="http://localhost:8000/">Ver el sitio</a>')
