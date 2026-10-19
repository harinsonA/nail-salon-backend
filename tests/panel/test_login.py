import re

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase
from django_tenants.utils import get_public_schema_name

from apps.tenancy.models import Dominio, Negocio

User = get_user_model()

PANEL = "admin.localhost"
RUTA = "/admin/login/"


class LoginDelPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        publico = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=publico, is_primary=True)
        cls.admin = User.objects.create_superuser(username="admin", email="admin@correo.cl", password="clave-larga")

    def setUp(self):
        connection.set_schema_to_public()
        self.panel = Client(HTTP_HOST=PANEL)

    def destino(self, respuesta):
        return re.search(r'name="next" value="([^"]*)"', respuesta.content.decode()).group(1)

    def test_usa_el_diseno_de_acceso_de_hi_agenda(self):
        respuesta = self.panel.get(RUTA)
        self.assertContains(respuesta, "soft-card")
        self.assertContains(respuesta, "comfort-button")
        self.assertNotContains(respuesta, "admin/css/login.css")

    def test_el_encabezado_habla_del_panel_y_no_del_negocio(self):
        respuesta = self.panel.get(RUTA)
        self.assertContains(respuesta, "Panel de administración")
        self.assertContains(respuesta, "Negocios, titulares y dominios de Hi Agenda")
        self.assertNotContains(respuesta, "Bienvenida")

    def test_pide_usuario_y_contrasena(self):
        respuesta = self.panel.get(RUTA)
        self.assertContains(respuesta, 'name="username"')
        self.assertContains(respuesta, ">Usuario<")
        self.assertContains(respuesta, 'name="password"')
        self.assertContains(respuesta, 'class="gentle-toggle"')

    def test_entrar_lleva_al_inicio_del_panel(self):
        respuesta = self.panel.get(RUTA)
        entrada = self.panel.post(
            RUTA,
            {"username": "admin", "password": "clave-larga", "next": self.destino(respuesta)},
        )
        self.assertRedirects(entrada, "/admin/")

    def test_entrar_respeta_el_destino_que_se_pidio(self):
        respuesta = self.panel.get(RUTA, {"next": "/admin/tenancy/negocio/"})
        self.assertEqual(self.destino(respuesta), "/admin/tenancy/negocio/")
        entrada = self.panel.post(
            f"{RUTA}?next=/admin/tenancy/negocio/",
            {"username": "admin", "password": "clave-larga", "next": "/admin/tenancy/negocio/"},
        )
        self.assertRedirects(entrada, "/admin/tenancy/negocio/", fetch_redirect_response=False)

    def test_cerrar_sesion_vuelve_al_login_del_panel(self):
        self.panel.force_login(self.admin)
        salida = self.panel.post("/admin/logout/")
        self.assertRedirects(salida, RUTA, fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.panel.session)

    def test_credenciales_incorrectas_muestran_la_alerta_del_diseno(self):
        respuesta = self.panel.post(RUTA, {"username": "admin", "password": "otra", "next": "/admin/"})
        self.assertContains(respuesta, "gentle-alert")
        self.assertContains(respuesta, "Usuario o contraseña incorrectos.")
        self.assertNotContains(respuesta, "staff")
        self.assertContains(respuesta, 'value="admin"')

    def test_una_cuenta_sin_acceso_al_panel_ve_el_aviso(self):
        User.objects.create_user(username="ayudante", password="clave-larga")
        self.panel.force_login(User.objects.get(username="ayudante"))
        respuesta = self.panel.get(RUTA)
        self.assertContains(respuesta, "no tiene acceso al panel")
        self.assertContains(respuesta, "ayudante")

    def test_un_administrador_con_sesion_abierta_entra_directo(self):
        self.panel.force_login(self.admin)
        self.assertRedirects(self.panel.get(RUTA), "/admin/")
