from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase, override_settings
from django_tenants.utils import get_public_schema_name

from apps.tenancy.models import Dominio, Negocio

User = get_user_model()

PANEL = "admin.localhost"


@override_settings(DOMINIO_BASE="localhost")
class MenuDelPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        publico = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=publico, is_primary=True)
        cls.admin = User.objects.create_superuser(username="admin", password="clave-larga")

    def setUp(self):
        connection.set_schema_to_public()
        self.panel = Client(HTTP_HOST=PANEL)

    def inicio(self, usuario=None):
        self.panel.force_login(usuario or self.admin)
        return self.panel.get("/admin/")

    def test_el_inicio_es_la_vista_del_panel(self):
        respuesta = self.inicio()
        self.assertTemplateUsed(respuesta, "panel/inicio.html")
        self.assertTemplateUsed(respuesta, "panel/base.html")
        self.assertContains(respuesta, "<title>Panel · Hi Agenda</title>")
        self.assertContains(respuesta, "container-main")
        self.assertContains(respuesta, "Inicio")
        self.assertNotContains(respuesta, "admin/css/base.css")
        self.assertNotContains(respuesta, "Acciones recientes")

    def test_el_inicio_pide_sesion_de_staff(self):
        respuesta = self.panel.get("/admin/")
        self.assertRedirects(respuesta, "/admin/login/?next=/admin/", fetch_redirect_response=False)

    def test_la_pagina_de_cada_app_sigue_siendo_la_de_django(self):
        self.panel.force_login(self.admin)
        respuesta = self.panel.get("/admin/tenancy/")
        self.assertTemplateUsed(respuesta, "admin/app_index.html")
        self.assertNotContains(respuesta, "menu__brand")

    def test_el_menu_agrupa_los_modelos_por_aplicacion(self):
        respuesta = self.inicio()
        self.assertContains(respuesta, "menu__brand")
        self.assertContains(respuesta, 'href="/admin/" aria-label="Ir al inicio del panel"')
        self.assertContains(respuesta, "Autenticación y autorización")
        for ruta in ("/admin/auth/group/", "/admin/auth/user/", "/admin/tenancy/negocio/",
                     "/admin/tenancy/persona/", "/admin/tenancy/rubro/"):
            with self.subTest(ruta=ruta):
                self.assertContains(respuesta, f'href="{ruta}"')

    def test_la_tuerca_lleva_al_sitio_a_la_clave_y_al_cierre_de_sesion(self):
        respuesta = self.inicio()
        self.assertContains(respuesta, 'href="http://localhost/"')
        self.assertContains(respuesta, "Ver sitio")
        self.assertContains(respuesta, 'href="/admin/password_change/"')
        self.assertContains(respuesta, 'action="/admin/logout/"')
        self.assertContains(respuesta, 'form="logout_form"')

    def test_ver_sitio_se_abre_en_una_pestana_nueva(self):
        html = self.inicio().content.decode()
        self.assertRegex(html, r'href="http://localhost/" target="_blank"\s+rel="noopener noreferrer"')

    def test_ver_sitio_respeta_el_puerto_del_navegador(self):
        self.panel = Client(HTTP_HOST=f"{PANEL}:8000")
        self.assertContains(self.inicio(), 'href="http://localhost:8000/"')

    def test_el_menu_solo_muestra_lo_que_el_usuario_puede_ver(self):
        staff = User.objects.create_user(username="staff", password="clave-larga", is_staff=True)
        respuesta = self.inicio(staff)
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, "/admin/tenancy/negocio/")
        self.assertNotContains(respuesta, "/admin/auth/user/")
        self.assertContains(respuesta, "Cerrar sesión")

    def test_una_cuenta_sin_clave_utilizable_no_ve_cambiar_contrasena(self):
        sin_clave = User.objects.create_superuser(username="sin-clave", password=None)
        self.assertNotContains(self.inicio(sin_clave), "Cambiar contraseña")
