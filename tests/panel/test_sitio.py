from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django_tenants.routers import TenantSyncRouter
from django_tenants.utils import get_public_schema_name

from apps.panel.sitio import PanelAdminSite
from apps.tenancy.models import Dominio, Negocio, Persona, Rubro

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
class CierreDeLasPaginasDeDjangoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        publico = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=publico, is_primary=True)
        cls.admin = User.objects.create_superuser(username="admin", password="x")
        cls.grupo = Group.objects.create(name="Soporte")
        cls.persona = Persona.objects.create(nombres="Carla")
        cls.rubro = Rubro.objects.get(codigo="barberia")

    def setUp(self):
        connection.set_schema_to_public()
        self.panel = Client(HTTP_HOST=PANEL)
        self.panel.force_login(self.admin)

    def test_la_raiz_lleva_al_inicio_del_panel(self):
        self.assertRedirects(Client(HTTP_HOST=PANEL).get("/"), "/admin/", fetch_redirect_response=False)
        self.assertRedirects(self.panel.get("/"), "/admin/")

    def test_los_historiales_de_django_llevan_a_su_listado(self):
        casos = {
            f"/admin/auth/user/{self.admin.pk}/history/": "/admin/auth/user/",
            f"/admin/auth/group/{self.grupo.pk}/history/": "/admin/auth/group/",
            f"/admin/tenancy/persona/{self.persona.pk}/history/": "/admin/tenancy/persona/",
            f"/admin/tenancy/rubro/{self.rubro.pk}/history/": "/admin/tenancy/rubro/",
        }
        for ruta, listado in casos.items():
            with self.subTest(ruta=ruta):
                self.assertRedirects(self.panel.get(ruta), listado, fetch_redirect_response=False)
        version = self.persona.history.first()
        self.assertRedirects(
            self.panel.get(f"/admin/tenancy/persona/{self.persona.pk}/history/{version.history_id}/"),
            "/admin/tenancy/persona/",
            fetch_redirect_response=False,
        )

    def test_las_pantallas_viejas_siguen_llevando_a_su_listado(self):
        for ruta, listado in {
            "/admin/auth/group/add/": "/admin/auth/group/",
            f"/admin/tenancy/persona/{self.persona.pk}/change/": "/admin/tenancy/persona/",
            f"/admin/tenancy/rubro/{self.rubro.pk}/delete/": "/admin/tenancy/rubro/",
            f"/admin/auth/user/{self.admin.pk}/password/": "/admin/auth/user/",
        }.items():
            with self.subTest(ruta=ruta):
                self.assertRedirects(self.panel.get(ruta), listado, fetch_redirect_response=False)
