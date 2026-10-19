from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django_tenants.utils import get_public_schema_name

from apps.profiles.models import Perfil
from apps.seguridad.models import AccesoUsuario
from apps.seguridad.sessions import CLOSED_ELSEWHERE_MESSAGE, SESSION_TOKEN_KEY
from apps.tenancy.models import Dominio, Negocio
from tests.base import NegocioTestCase

User = get_user_model()

PANEL = "admin.localhost"
LOGIN = "/admin/login/"
INICIO = "/admin/"
LISTA_AJAX = "/admin/auth/user/list/"
CLAVE = "Clave-Larga-1"


class SesionUnicaEnElPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        publico = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=publico, is_primary=True)
        cls.admin = User.objects.create_superuser(
            username="admin", email="admin@hiagenda.cl", password=CLAVE, first_name="Ana", last_name="Rojas"
        )

    def setUp(self):
        connection.set_schema_to_public()

    def entrar(self):
        navegador = Client(HTTP_HOST=PANEL)
        respuesta = navegador.post(LOGIN, {"username": "admin", "password": CLAVE, "next": INICIO})
        self.assertRedirects(respuesta, INICIO, fetch_redirect_response=False)
        return navegador

    def token_guardado(self):
        token = AccesoUsuario.objects.get(user=self.admin).token_sesion
        return str(token) if token else None

    def test_entrar_guarda_el_mismo_token_en_la_sesion_y_en_la_base(self):
        navegador = self.entrar()
        self.assertEqual(navegador.session[SESSION_TOKEN_KEY], self.token_guardado())

    def test_entrar_en_otro_dispositivo_cierra_la_sesion_anterior(self):
        computador = self.entrar()
        telefono = self.entrar()
        respuesta = computador.get(INICIO)
        self.assertRedirects(respuesta, f"{LOGIN}?next={INICIO}", fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", computador.session)
        self.assertEqual(telefono.get(INICIO).status_code, 200)

    def test_el_login_dice_por_que_se_cerro_y_solo_una_vez(self):
        computador = self.entrar()
        self.entrar()
        computador.get(INICIO)
        self.assertContains(computador.get(LOGIN), CLOSED_ELSEWHERE_MESSAGE)
        self.assertNotContains(computador.get(LOGIN), CLOSED_ELSEWHERE_MESSAGE)

    def test_una_peticion_ajax_recibe_el_motivo(self):
        computador = self.entrar()
        self.entrar()
        respuesta = computador.get(LISTA_AJAX, {"draw": 1, "start": 0, "length": 10}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()["message"], CLOSED_ELSEWHERE_MESSAGE)

    def test_cambiar_la_propia_clave_no_cierra_la_sesion(self):
        navegador = self.entrar()
        respuesta = navegador.post(
            "/admin/account/modal/",
            {
                "username": "admin",
                "first_name": "Ana",
                "first_surname": "Rojas",
                "email": "admin@hiagenda.cl",
                "password": "Otra-Clave-2026",
                "password_confirmation": "Otra-Clave-2026",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(navegador.get(INICIO).status_code, 200)

    def test_salir_borra_el_token(self):
        navegador = self.entrar()
        navegador.post("/admin/logout/")
        self.assertIsNone(self.token_guardado())

    def test_salir_desde_una_sesion_vieja_no_borra_el_token_vigente(self):
        computador = self.entrar()
        telefono = self.entrar()
        vigente = self.token_guardado()
        computador.post("/admin/logout/")
        self.assertEqual(self.token_guardado(), vigente)
        self.assertEqual(telefono.get(INICIO).status_code, 200)

    def test_una_sesion_de_antes_del_cambio_adopta_el_token_si_no_hay_otro(self):
        navegador = self.entrar()
        sesion = navegador.session
        del sesion[SESSION_TOKEN_KEY]
        sesion.save()
        AccesoUsuario.objects.filter(user=self.admin).update(token_sesion=None)
        self.assertEqual(navegador.get(INICIO).status_code, 200)
        self.assertEqual(navegador.session[SESSION_TOKEN_KEY], self.token_guardado())

    def test_una_sesion_sin_token_se_cierra_si_ya_hay_una_vigente(self):
        vieja = self.entrar()
        sesion = vieja.session
        del sesion[SESSION_TOKEN_KEY]
        sesion.save()
        self.assertRedirects(vieja.get(INICIO), f"{LOGIN}?next={INICIO}", fetch_redirect_response=False)

    @override_settings(SECURITY_SINGLE_SESSION=False)
    def test_el_interruptor_apagado_permite_varias_sesiones(self):
        computador = self.entrar()
        self.entrar()
        self.assertEqual(computador.get(INICIO).status_code, 200)


class SesionUnicaTodaviaNoEnLosNegociosTests(NegocioTestCase):
    esquema = "sesion_negocio"
    dominio = "sesion-negocio.localhost"

    def test_dos_sesiones_del_mismo_usuario_del_negocio_siguen_abiertas(self):
        laura = User.objects.create_user(username="laura", email="laura@correo.cl", password=CLAVE)
        Perfil.objects.filter(user=laura).update(debe_cambiar_clave=False)
        computador = Client(HTTP_HOST=self.dominio)
        telefono = Client(HTTP_HOST=self.dominio)
        for navegador in (computador, telefono):
            navegador.post(reverse("login"), {"username": "laura@correo.cl", "password": CLAVE})
        self.assertEqual(computador.get(reverse("calendar")).status_code, 200)
        self.assertEqual(telefono.get(reverse("calendar")).status_code, 200)
